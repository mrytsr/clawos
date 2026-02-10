import os
import re
import subprocess

from flask import Blueprint, request

from ctrl import api_error, api_ok
from lib import systemd_utils


clash_bp = Blueprint('clash', __name__)


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


def _detect_clash():
    service_candidates = [
        'clash.service',
        'clash-meta.service',
        'mihomo.service',
    ]
    config_candidates = [
        os.path.expanduser('~/.config/clash/config.yaml'),
        os.path.expanduser('~/.config/mihomo/config.yaml'),
        '/etc/clash/config.yaml',
        '/etc/mihomo/config.yaml',
        '/usr/local/etc/clash/config.yaml',
    ]

    service = None
    for s in service_candidates:
        st = _systemctl_user_show(s)
        if st.get('available'):
            service = s
            break

    config_path = None
    for p in config_candidates:
        if p and os.path.exists(p):
            config_path = p
            break

    return service, config_path


def _parse_clash_yaml_minimal(content: str):
    text = content or ''
    out = {}
    keys = [
        'port',
        'socks-port',
        'mixed-port',
        'redir-port',
        'tproxy-port',
        'allow-lan',
        'mode',
        'log-level',
        'external-controller',
        'secret',
    ]
    for k in keys:
        m = re.search(r'^\s*' + re.escape(k) + r'\s*:\s*([^\n#]+)', text, flags=re.MULTILINE)
        if not m:
            continue
        v = (m.group(1) or '').strip().strip('"').strip("'")
        if k in {'port', 'socks-port', 'mixed-port', 'redir-port', 'tproxy-port'}:
            try:
                out[k] = int(v)
            except Exception:
                out[k] = v
        elif k in {'allow-lan'}:
            out[k] = v.lower() in {'true', 'yes', '1', 'on'}
        elif k in {'secret'}:
            out[k] = '***' if v else ''
        else:
            out[k] = v
    return out


@clash_bp.route('/api/clash/state')
def api_clash_state():
    service_name, config_path = _detect_clash()
    config = {'present': False, 'path': config_path or ''}
    try:
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            config = {
                'present': True,
                'path': config_path,
                'summary': _parse_clash_yaml_minimal(content),
            }
    except Exception as e:
        config = {'present': False, 'path': config_path or '', 'error': str(e)}

    service = _systemctl_user_show(service_name) if service_name else {'available': False, 'error': 'service not found'}
    return api_ok({'config': config, 'service': service})


@clash_bp.route('/api/clash/control', methods=['POST'])
def api_clash_control():
    service_name, _config_path = _detect_clash()
    if not service_name:
        return api_error('service not found', status=404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    action = (data.get('action') or '').strip().lower()
    if action not in {'start', 'stop', 'restart'}:
        return api_error('Invalid action', status=400)

    result = systemd_utils.control_systemd_service(service_name, action)
    if isinstance(result, dict) and result.get('success'):
        return api_ok({'ok': True, 'service': _systemctl_user_show(service_name)})
    message = None
    if isinstance(result, dict):
        message = result.get('message')
    return api_error(message or 'Error', status=500)
