import os
import secrets
import threading
import time

from flask import Blueprint, jsonify, redirect, request, url_for
from flask import render_template

import config
from lib import json_utils


auth_bp = Blueprint('auth', __name__)

AUTH_COOKIE_NAME = 'clawos_auth'
AUTH_FILE_PATH = config.AUTH_FILE
AUTH_SESSION_TTL_SECONDS = 30 * 24 * 60 * 60

_auth_lock = threading.Lock()


def _now_ts():
    return int(time.time())


def _load_auth_store():
    data = json_utils.load_json(AUTH_FILE_PATH, default=None)
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get('sessions'), dict):
        data['sessions'] = {}
    if not isinstance(data.get('version'), int):
        data['version'] = 1
    return data


def _save_auth_store(data):
    json_utils.save_json(AUTH_FILE_PATH, data if isinstance(data, dict) else {})


def _purge_expired_sessions(data, now_ts):
    sessions = data.get('sessions')
    if not isinstance(sessions, dict):
        data['sessions'] = {}
        return
    expired = []
    for token, meta in sessions.items():
        if not isinstance(meta, dict):
            expired.append(token)
            continue
        last_seen = meta.get('last_seen')
        try:
            last_seen = int(last_seen)
        except Exception:
            expired.append(token)
            continue
        if now_ts - last_seen > AUTH_SESSION_TTL_SECONDS:
            expired.append(token)
    for token in expired:
        sessions.pop(token, None)


def _get_authed_token():
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return ''
    return str(token)


def _is_request_authed():
    token = _get_authed_token()
    if not token:
        return False
    now_ts = _now_ts()
    with _auth_lock:
        data = _load_auth_store()
        _purge_expired_sessions(data, now_ts)
        sessions = data.get('sessions', {})
        if token not in sessions:
            _save_auth_store(data)
            return False
        meta = sessions.get(token) or {}
        if not isinstance(meta, dict):
            sessions.pop(token, None)
            _save_auth_store(data)
            return False
        meta['last_seen'] = now_ts
        meta['ip'] = request.remote_addr or meta.get('ip') or ''
        meta['ua'] = request.headers.get('User-Agent', '')[:300]
        sessions[token] = meta
        data['sessions'] = sessions
        _save_auth_store(data)
    return True


def _render_login_page(error_message=None, success_redirect=None):
    err = (error_message or '').strip()
    return render_template('login.html', error_message=err, success_redirect=success_redirect)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if _is_request_authed():
            return redirect(url_for('browser.browse'))
        success_redirect = request.args.get('success_redirect', '')
        return _render_login_page(success_redirect=success_redirect), 200, {'Content-Type': 'text/html; charset=utf-8'}

    password = (request.form.get('password') or '').strip()
    success_redirect = request.form.get('success_redirect', '').strip()
    if password and password == config.AUTH_PASSWORD:
        now_ts = _now_ts()
        token = 'sess_' + secrets.token_urlsafe(32)
        with _auth_lock:
            data = _load_auth_store()
            _purge_expired_sessions(data, now_ts)
            sessions = data.get('sessions', {})
            sessions[token] = {
                'created_at': now_ts,
                'last_seen': now_ts,
                'ip': request.remote_addr or '',
                'ua': request.headers.get('User-Agent', '')[:300],
            }
            data['sessions'] = sessions
            _save_auth_store(data)

        success_redirect = success_redirect or ''
        if success_redirect and success_redirect.startswith('/'):
            resp = redirect(success_redirect)
        else:
            resp = redirect(url_for('browser.browse'))
        resp.set_cookie(
            AUTH_COOKIE_NAME,
            token,
            max_age=AUTH_SESSION_TTL_SECONDS,
            httponly=True,
            samesite='Lax',
        )
        return resp
    return _render_login_page('密码错误'), 401, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}


@auth_bp.before_app_request
def require_auth():
    if request.endpoint == 'static':
        return None
    if request.path == '/favicon.ico':
        return None
    if request.path == '/':
        return None
    if request.path.startswith('/screenshots/'):
        return None
    if request.path.startswith('/login'):
        return None
    if request.path.startswith('/@vite'):
        return None
    host = (request.host or '').split(':')[0].lower()
    if host in ('localhost', '127.0.0.1'):
        return None
    if (request.remote_addr or '') in ('127.0.0.1', '::1'):
        return None
    if _is_request_authed():
        return None

    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': {'message': 'Unauthorized'}}), 401
    if request.path.startswith('/socket.io'):
        return ('Unauthorized', 401, {'Cache-Control': 'no-store'})
    return redirect('/login?success_redirect=' + request.full_path)


@auth_bp.route('/logout')
def logout():
    token = _get_authed_token()
    if token:
        with _auth_lock:
            data = _load_auth_store()
            sessions = data.get('sessions', {})
            if isinstance(sessions, dict):
                sessions.pop(token, None)
                data['sessions'] = sessions
            _save_auth_store(data)
    resp = redirect('/login')
    resp.set_cookie(AUTH_COOKIE_NAME, '', expires=0)
    return resp
