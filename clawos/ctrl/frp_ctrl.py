import os
import re
import subprocess
import tarfile
import tempfile
import platform

from flask import Blueprint, current_app, request

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task, update_task
from lib import systemd_utils
import requests


frp_bp = Blueprint('frp', __name__)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FRP_PACKS_DIR = os.path.join(BASE_DIR, 'bin')
FRPC_CONFIG_PATH = os.path.join(FRP_PACKS_DIR, 'frpc.toml')


def _current_system_key():
    name = (platform.system() or '').lower()
    if name.startswith('win'):
        return 'win'
    if name.startswith('darwin'):
        return 'mac'
    return 'linux'


def _current_frpc_binary_path():
    key = _current_system_key()
    if key == 'win':
        return os.path.join(FRP_PACKS_DIR, 'frpc-win.exe')
    if key == 'mac':
        return os.path.join(FRP_PACKS_DIR, 'frpc-mac')
    return os.path.join(FRP_PACKS_DIR, 'frpc-linux')


def _arch_linux_name():
    m = (platform.machine() or '').lower()
    if m in ('x86_64', 'amd64'):
        return 'amd64'
    if m in ('aarch64', 'arm64'):
        return 'arm64'
    if m.startswith('armv7'):
        return 'arm'
    if m in ('i386', 'i686', 'x86'):
        return '386'
    return 'amd64'


def _run_shell(task_id, cmd: str, timeout=None):
    update_task(task_id, status='running', message=cmd)
    r = subprocess.run(['bash', '-lc', cmd], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or '').strip()
        raise RuntimeError(err or ('command failed: ' + cmd))
    return r.stdout


def _frp_install_state():
    bin_path = _current_frpc_binary_path()
    installed = os.path.exists(bin_path) or _systemctl_user_show('frpc.service').get('available')
    return {'installed': bool(installed), 'bin_path': bin_path}


def _get_embedded_runtime_api():
    try:
        ext = current_app.extensions.get('frpc_runtime') or {}
        if isinstance(ext, dict):
            return ext
    except Exception:
        pass
    return {}


@frp_bp.route('/api/frp/install_state')
def api_frp_install_state():
    return api_ok(_frp_install_state())


def _ensure_frpc_service(task_id):
    bin_path = _current_frpc_binary_path()
    unit_dir = os.path.expanduser('~/.config/systemd/user')
    os.makedirs(unit_dir, exist_ok=True)
    unit_path = os.path.join(unit_dir, 'frpc.service')
    content = '\n'.join([
        '[Unit]',
        'Description=FRP Client (frpc)',
        'After=network.target',
        '',
        '[Service]',
        'Type=simple',
        f'ExecStart={bin_path} -c {FRPC_CONFIG_PATH}',
        'Restart=on-failure',
        'RestartSec=2',
        '',
        '[Install]',
        'WantedBy=default.target',
        '',
    ])
    with open(unit_path, 'w', encoding='utf-8') as f:
        f.write(content)
    _run_shell(task_id, 'systemctl --user daemon-reload', timeout=20)
    _run_shell(task_id, 'systemctl --user enable frpc.service', timeout=20)
    _run_shell(task_id, 'systemctl --user restart frpc.service', timeout=30)


def _ensure_frpc_config():
    cfg_path = FRPC_CONFIG_PATH
    os.makedirs(FRP_PACKS_DIR, exist_ok=True)
    if os.path.exists(cfg_path):
        return
    content = '\n'.join([
        'serverAddr = "your-frp-server"',
        'serverPort = 7000',
        '',
        'auth.method = "token"',
        'auth.token = "change-me"',
        '',
        '[[proxies]]',
        'name = "ssh"',
        'type = "tcp"',
        'localIP = "127.0.0.1"',
        'localPort = 22',
        'remotePort = 6002',
        '',
    ])
    with open(cfg_path, 'w', encoding='utf-8') as f:
        f.write(content)

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
    frp_config_path = FRPC_CONFIG_PATH
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
    frp_config_path = FRPC_CONFIG_PATH
    try:
        data = request.get_json()
        content = data.get('content', '')
        os.makedirs(FRP_PACKS_DIR, exist_ok=True)

        with open(frp_config_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return api_ok({'success': True})
    except Exception as e:
        return api_error(str(e))


@frp_bp.route('/api/frp/state')
def api_frp_state():
    frp_config_path = FRPC_CONFIG_PATH
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

    runtime_api = _get_embedded_runtime_api()
    get_state = runtime_api.get('get_state') if isinstance(runtime_api, dict) else None
    get_mapping_summary = runtime_api.get('get_mapping_summary') if isinstance(runtime_api, dict) else None
    if callable(get_state):
        service = get_state()
    else:
        service = _systemctl_user_show('frpc.service')
    if callable(get_mapping_summary):
        summary = get_mapping_summary() or {}
        items = summary.get('items') or []
        proxy_map = {str(item.get('name') or '').strip(): item for item in items if str(item.get('name') or '').strip()}
        merged_proxies = []
        for proxy in config_info.get('proxies') or []:
            name = str((proxy or {}).get('name') or '').strip()
            runtime_item = proxy_map.get(name) or {}
            merged = dict(proxy or {})
            if runtime_item.get('remote'):
                merged['runtimeRemote'] = runtime_item.get('remote')
            if runtime_item.get('url'):
                merged['accessUrl'] = runtime_item.get('url')
            if runtime_item.get('local'):
                merged['runtimeLocal'] = runtime_item.get('local')
            if runtime_item.get('status'):
                merged['runtimeStatus'] = runtime_item.get('status')
            merged_proxies.append(merged)
        if merged_proxies:
            config_info['proxies'] = merged_proxies
        config_info['runtime'] = summary.get('runtime') or {}
    return api_ok({'config': config_info, 'service': service})


@frp_bp.route('/api/frp/control', methods=['POST'])
def api_frp_control():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    action = (data.get('action') or '').strip().lower()
    if action not in {'start', 'stop', 'restart'}:
        return api_error('Invalid action', status=400)

    runtime_api = _get_embedded_runtime_api()
    get_state = runtime_api.get('get_state') if isinstance(runtime_api, dict) else None
    start_fn = runtime_api.get('start') if isinstance(runtime_api, dict) else None
    stop_fn = runtime_api.get('stop') if isinstance(runtime_api, dict) else None

    if action == 'start' and callable(start_fn):
        ok, message = start_fn()
        if ok:
            return api_ok({'ok': True, 'service': get_state() if callable(get_state) else None})
        return api_error(message or '启动失败', status=500)
    if action == 'stop' and callable(stop_fn):
        ok, message = stop_fn()
        if ok:
            return api_ok({'ok': True, 'service': get_state() if callable(get_state) else None})
        return api_error(message or '停止失败', status=500)
    if action == 'restart' and callable(stop_fn) and callable(start_fn):
        ok, message = stop_fn()
        if not ok:
            return api_error(message or '停止失败', status=500)
        ok, message = start_fn()
        if ok:
            return api_ok({'ok': True, 'service': get_state() if callable(get_state) else None})
        return api_error(message or '启动失败', status=500)

    result = systemd_utils.control_systemd_service('frpc.service', action)
    if isinstance(result, dict) and result.get('success'):
        return api_ok({'ok': True, 'service': _systemctl_user_show('frpc.service')})
    message = None
    if isinstance(result, dict):
        message = result.get('message')
    return api_error(message or 'Error', status=500)


@frp_bp.route('/api/frp/autostart', methods=['POST'])
def api_frp_autostart():
    data = request.get_json(silent=True) or {}
    enabled = bool(data.get('autostart', False))
    runtime_api = _get_embedded_runtime_api()
    setter = runtime_api.get('set_autostart') if isinstance(runtime_api, dict) else None
    getter = runtime_api.get('get_state') if isinstance(runtime_api, dict) else None
    if not callable(setter):
        return api_error('FRP runtime unavailable', status=500)
    try:
        saved = setter(enabled)
        return api_ok({
            'autostart': bool(saved.get('autostart', False)),
            'service': getter() if callable(getter) else None,
        })
    except Exception as e:
        return api_error(str(e), status=500)


@frp_bp.route('/api/frp/install', methods=['POST'])
def api_frp_install():
    def _install(task_id, skip_if_installed: bool):
        state = _frp_install_state()
        if skip_if_installed and state.get('installed'):
            return

        update_task(task_id, status='running', message='fetching latest frp release')
        resp = requests.get('https://api.github.com/repos/fatedier/frp/releases/latest', timeout=15)
        resp.raise_for_status()
        data = resp.json() or {}
        tag = (data.get('tag_name') or '').strip()
        ver = tag[1:] if tag.startswith('v') else tag
        if not ver:
            raise RuntimeError('failed to detect frp version')
        arch = _arch_linux_name()
        filename = f'frp_{ver}_linux_{arch}.tar.gz'
        url = f'https://github.com/fatedier/frp/releases/download/{tag}/{filename}'

        update_task(task_id, status='running', message='downloading ' + filename)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tf:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        tf.write(chunk)
                tar_path = tf.name

        update_task(task_id, status='running', message='extracting ' + filename)
        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                members = tar.getmembers()
                frpc_member = None
                for m in members:
                    base = os.path.basename(m.name)
                    if base == 'frpc' and m.isfile():
                        frpc_member = m
                        break
                if not frpc_member:
                    raise RuntimeError('frpc not found in archive')
                os.makedirs(FRP_PACKS_DIR, exist_ok=True)
                extracted = tar.extractfile(frpc_member)
                if not extracted:
                    raise RuntimeError('extract frpc failed')
                out_path = _current_frpc_binary_path()
                with open(out_path, 'wb') as f:
                    f.write(extracted.read())
                os.chmod(out_path, 0o755)
        finally:
            try:
                os.remove(tar_path)
            except Exception:
                pass

        _ensure_frpc_config()
        _ensure_frpc_service(task_id)

    task_id = create_task(lambda tid: _install(tid, True), name='frp install')
    return api_ok({'taskId': task_id})

@frp_bp.route('/api/frp/reinstall', methods=['POST'])
def api_frp_reinstall():
    def _do(task_id):
        _do_uninstall(task_id)
        api_frp_install_inner(task_id)

    def api_frp_install_inner(task_id):
        state = _frp_install_state()
        if state.get('installed'):
            _do_uninstall(task_id)
        update_task(task_id, status='running', message='reinstalling frpc')
        resp = requests.get('https://api.github.com/repos/fatedier/frp/releases/latest', timeout=15)
        resp.raise_for_status()
        data = resp.json() or {}
        tag = (data.get('tag_name') or '').strip()
        ver = tag[1:] if tag.startswith('v') else tag
        if not ver:
            raise RuntimeError('failed to detect frp version')
        arch = _arch_linux_name()
        filename = f'frp_{ver}_linux_{arch}.tar.gz'
        url = f'https://github.com/fatedier/frp/releases/download/{tag}/{filename}'
        update_task(task_id, status='running', message='downloading ' + filename)
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tf:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        tf.write(chunk)
                tar_path = tf.name
        update_task(task_id, status='running', message='extracting ' + filename)
        try:
            with tarfile.open(tar_path, 'r:gz') as tar:
                frpc_member = None
                for m in tar.getmembers():
                    if os.path.basename(m.name) == 'frpc' and m.isfile():
                        frpc_member = m
                        break
                if not frpc_member:
                    raise RuntimeError('frpc not found in archive')
                os.makedirs(FRP_PACKS_DIR, exist_ok=True)
                extracted = tar.extractfile(frpc_member)
                if not extracted:
                    raise RuntimeError('extract frpc failed')
                out_path = _current_frpc_binary_path()
                with open(out_path, 'wb') as f:
                    f.write(extracted.read())
                os.chmod(out_path, 0o755)
        finally:
            try:
                os.remove(tar_path)
            except Exception:
                pass
        _ensure_frpc_config()
        _ensure_frpc_service(task_id)

    task_id = create_task(_do, name='frp reinstall')
    return api_ok({'taskId': task_id})


def _do_uninstall(task_id):
    try:
        _run_shell(task_id, 'systemctl --user stop frpc.service', timeout=20)
    except Exception:
        pass
    try:
        _run_shell(task_id, 'systemctl --user disable frpc.service', timeout=20)
    except Exception:
        pass
    unit_path = os.path.expanduser('~/.config/systemd/user/frpc.service')
    try:
        if os.path.exists(unit_path):
            os.remove(unit_path)
    except Exception:
        pass
    try:
        _run_shell(task_id, 'systemctl --user daemon-reload', timeout=20)
    except Exception:
        pass
    # Keep packaged binaries/config under bin; uninstall here only removes service wiring.


@frp_bp.route('/api/frp/uninstall', methods=['POST'])
def api_frp_uninstall():
    def _do(task_id):
        _do_uninstall(task_id)

    task_id = create_task(_do, name='frp uninstall')
    return api_ok({'taskId': task_id})
