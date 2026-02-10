import os
import re
import subprocess

from flask import Blueprint, request

from ctrl import api_error, api_ok
from lib import systemd_utils


frp_bp = Blueprint('frp', __name__)


def _systemctl_user_show(unit: str):
    try:
        result = subprocess.run(
            [
                'systemctl',
                '--user',
                'show',
                unit,
                '--no-pager',
                '--property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,FragmentPath',
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception as e:
        return {'available': False, 'error': str(e)}

    if result.returncode != 0:
        err = (result.stderr or result.stdout or '').strip()
        return {'available': False, 'error': err or 'systemctl failed'}

    props = {}
    for line in (result.stdout or '').splitlines():
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = (k or '').strip()
        v = (v or '').strip()
        if k:
            props[k] = v

    active = (props.get('ActiveState') or '').lower()
    sub = (props.get('SubState') or '').lower()
    running = active == 'active' and sub == 'running'

    return {
        'available': True,
        'id': props.get('Id') or unit,
        'description': props.get('Description') or '',
        'load_state': props.get('LoadState') or '',
        'active_state': props.get('ActiveState') or '',
        'sub_state': props.get('SubState') or '',
        'unit_file_state': props.get('UnitFileState') or '',
        'fragment_path': props.get('FragmentPath') or '',
        'running': running,
    }


def _parse_frpc_toml(content: str):
    text = content or ''
    proxies = []
    current = None

    proxy_header_re = re.compile(r'^\s*\[\[proxies\]\]\s*$')
    kv_re = {
        'name': re.compile(r'^\s*name\s*=\s*"([^"]*)"\s*$'),
        'type': re.compile(r'^\s*type\s*=\s*"([^"]*)"\s*$'),
        'localIP': re.compile(r'^\s*localIP\s*=\s*"([^"]*)"\s*$'),
        'localPort': re.compile(r'^\s*localPort\s*=\s*(\d+)\s*$'),
        'remotePort': re.compile(r'^\s*remotePort\s*=\s*(\d+)\s*$'),
    }

    for line in text.splitlines():
        if proxy_header_re.match(line):
            if current:
                proxies.append(current)
            current = {}
            continue
        if current is None:
            continue
        for k, rx in kv_re.items():
            m = rx.match(line)
            if m:
                current[k] = m.group(1)

    if current:
        proxies.append(current)

    server_addr = None
    server_port = None
    m = re.search(r'^\s*serverAddr\s*=\s*"([^"]*)"\s*$', text, flags=re.MULTILINE)
    if m:
        server_addr = m.group(1)
    m = re.search(r'^\s*serverPort\s*=\s*(\d+)\s*$', text, flags=re.MULTILINE)
    if m:
        try:
            server_port = int(m.group(1))
        except Exception:
            server_port = None

    return {
        'serverAddr': server_addr,
        'serverPort': server_port,
        'proxies': proxies,
    }


@frp_bp.route('/api/frp/config')
def api_frp_config():
    frp_config_path = '/usr/local/frp/frpc.toml'
    try:
        if not os.path.exists(frp_config_path):
            return api_error('FRP 配置文件不存在')

        with open(frp_config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return api_ok({'content': content, 'path': frp_config_path})
    except Exception as e:
        return api_error(str(e))


@frp_bp.route('/api/frp/config', methods=['POST'])
def api_frp_config_save():
    frp_config_path = '/usr/local/frp/frpc.toml'
    try:
        data = request.get_json()
        content = data.get('content', '')

        with open(frp_config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return api_ok({'success': True})
    except Exception as e:
        return api_error(str(e))


@frp_bp.route('/api/frp/state')
def api_frp_state():
    frp_config_path = '/usr/local/frp/frpc.toml'
    config_info = {'present': False, 'path': frp_config_path}
    try:
        if os.path.exists(frp_config_path):
            with open(frp_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            parsed = _parse_frpc_toml(content)
            config_info = {
                'present': True,
                'path': frp_config_path,
                'serverAddr': parsed.get('serverAddr'),
                'serverPort': parsed.get('serverPort'),
                'proxies': parsed.get('proxies') or [],
            }
    except Exception as e:
        config_info = {'present': False, 'path': frp_config_path, 'error': str(e)}

    service = _systemctl_user_show('frpc.service')
    return api_ok({'config': config_info, 'service': service})


@frp_bp.route('/api/frp/control', methods=['POST'])
def api_frp_control():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    action = (data.get('action') or '').strip().lower()
    if action not in {'start', 'stop', 'restart'}:
        return api_error('Invalid action', status=400)

    result = systemd_utils.control_systemd_service('frpc.service', action)
    if isinstance(result, dict) and result.get('success'):
        return api_ok({'ok': True, 'service': _systemctl_user_show('frpc.service')})
    message = None
    if isinstance(result, dict):
        message = result.get('message')
    return api_error(message or 'Error', status=500)
