from flask import Blueprint, jsonify, redirect, request, session, url_for

import config


auth_bp = Blueprint('auth', __name__)

def _render_login_page(error_message=None):
    err = (error_message or '').strip()
    err_html = (
        ('<div style="margin:12px 0;padding:10px 12px;border:1px solid #ffebe9;'
         'background:#fff1f0;color:#cf222e;border-radius:8px;">'
         + err +
         '</div>')
        if err
        else ''
    )
    return (
        '<!doctype html>'
        '<html lang="zh-CN"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>登录</title>'
        '</head>'
        '<body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,'
        'Helvetica,Arial,sans-serif;padding:24px;max-width:420px;margin:0 auto;">'
        '<h2 style="margin:0 0 12px 0;">登录</h2>'
        '<div style="color:#57606a;line-height:1.6;margin-bottom:12px;">'
        '请输入密码登录。'
        '</div>'
        + err_html +
        '<form method="post" action="/login">'
        '<label style="display:block;margin:8px 0 6px 0;color:#24292f;">密码</label>'
        '<input name="password" type="password" autocomplete="current-password" '
        'style="width:100%;padding:10px 12px;border:1px solid #d0d7de;border-radius:8px;'
        'font-size:16px;outline:none;" autofocus />'
        '<button type="submit" '
        'style="margin-top:12px;width:100%;padding:10px 12px;border:0;border-radius:8px;'
        'background:#0969da;color:#fff;font-size:16px;cursor:pointer;">登录</button>'
        '</form>'
        '</body></html>'
    )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('authed'):
            return redirect(url_for('file.browse'))
        return _render_login_page(), 200, {'Content-Type': 'text/html; charset=utf-8'}

    password = (request.form.get('password') or '').strip()
    if password and password == config.AUTH_PASSWORD:
        session['authed'] = True
        return redirect(url_for('file.browse'))
    return _render_login_page('密码错误'), 401, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}


@auth_bp.before_app_request
def require_auth():
    if request.endpoint == 'static':
        return None
    if request.path.startswith('/login'):
        return None
    if request.path.startswith('/@vite'):
        return None
    if session.get('authed'):
        return None

    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': {'message': 'Unauthorized'}}), 401
    if request.path.startswith('/socket.io'):
        return ('Unauthorized', 401, {'Cache-Control': 'no-store'})
    return redirect('/login')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
