import os
import platform
import re
import subprocess
import uuid


def frp_bin_dir(base_dir):
    return os.path.join(base_dir, 'bin')


def _ensure_executable(path):
    try:
        if os.name != 'nt' and path and os.path.exists(path):
            os.chmod(path, 0o755)
    except Exception:
        pass


def current_chmlfrpc_binary_path(base_dir):
    sys_name = (platform.system() or '').lower()
    arch = (platform.machine() or '').lower()
    if sys_name.startswith('win'):
        return os.path.join(frp_bin_dir(base_dir), 'chmlfrpc-win-amd64.exe')
    if sys_name.startswith('darwin'):
        name = 'chmlfrpc-mac-arm64' if arch in {'arm64', 'aarch64'} else 'chmlfrpc-mac-amd64'
        path = os.path.join(frp_bin_dir(base_dir), name)
        _ensure_executable(path)
        return path
    path = os.path.join(frp_bin_dir(base_dir), 'chmlfrpc-linux-amd64')
    _ensure_executable(path)
    return path


def chml_profiles():
    token = 'AWlTx7jczSvkYjePNeUSNmAb'
    return {
        'token': token,
        'items': [
            {'p': 291844, 'remote': 'tw.2.frp.one:32020'},
            {'p': 291845, 'remote': 'tw.frp.one:22294'},
            {'p': 291847, 'remote': 'xg-5.frp.one:23746'},
        ],
    }


def chml_profile_sequence(preferred_p=None):
    profiles = chml_profiles()
    items = list(profiles.get('items') or [])
    if preferred_p is None:
        return items
    try:
        p = int(preferred_p)
    except Exception:
        return items
    head = []
    tail = []
    for item in items:
        if int(item.get('p') or 0) == p:
            head.append(item)
        else:
            tail.append(item)
    return head + tail


def resolve_chml_profile(p=None):
    profiles = chml_profiles()
    items = profiles.get('items') or []
    if p is not None:
        try:
            target = int(p)
        except Exception:
            target = None
        if target is not None:
            for item in items:
                if int(item.get('p') or 0) == target:
                    return profiles.get('token') or '', item
    return profiles.get('token') or '', (items[0] if items else {})


def build_chml_mapping_summary(local_port, p, remote_addr, running, pid=None, reason=None):
    remote_text = str(remote_addr or '').strip()
    url = status_url_from_remote('tcp', remote_text)
    runtime = {'ok': bool(running), 'reason': str(reason or '').strip()}
    if runtime['ok']:
        runtime.pop('reason', None)
    return {
        'ok': True,
        'mode': 'chmlfrpc',
        'items': [
            {
                'name': str(p) if p is not None else '-',
                'type': 'tcp',
                'local': f'127.0.0.1:{local_port}',
                'remote': remote_text or '-',
                'url': url,
                'status': 'running' if running else 'stopped',
                'runtime_remote': remote_text,
            }
        ],
        'runtime': runtime,
        'pid': pid,
    }


def current_frpc_binary_path(base_dir):
    name = (platform.system() or '').lower()
    bin_dir = frp_bin_dir(base_dir)
    if name.startswith('win'):
        return os.path.join(bin_dir, 'frpc-win.exe')
    path = os.path.join(bin_dir, 'frpc-mac' if name.startswith('darwin') else 'frpc-linux')
    _ensure_executable(path)
    return path


def current_frpc_config_path(base_dir):
    return os.path.join(frp_bin_dir(base_dir), 'frpc.toml')


def status_url_from_remote(proxy_type, remote_addr):
    text = str(remote_addr or '').strip()
    if not text:
        return ''
    kind = str(proxy_type or 'tcp').strip().lower() or 'tcp'
    if '://' in text:
        return text
    if kind in {'http', 'https', 'tcp'}:
        return f'http://{text}'
    return text


def parse_frpc_toml(content):
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
        for key, rx in kv_re.items():
            matched = rx.match(line)
            if matched:
                current[key] = matched.group(1)

    if current:
        proxies.append(current)

    server_addr = None
    server_port = None
    matched = re.search(r'^\s*serverAddr\s*=\s*"([^"]*)"\s*$', text, flags=re.MULTILINE)
    if matched:
        server_addr = matched.group(1)
    matched = re.search(r'^\s*serverPort\s*=\s*(\d+)\s*$', text, flags=re.MULTILINE)
    if matched:
        try:
            server_port = int(matched.group(1))
        except Exception:
            server_port = None

    return {
        'serverAddr': server_addr,
        'serverPort': server_port,
        'proxies': proxies,
    }


def rewrite_frpc_proxy_names_with_uuid(base_dir):
    config_path = current_frpc_config_path(base_dir)
    if not os.path.exists(config_path):
        return {'ok': False, 'reason': 'frpc.toml not found', 'updated': 0}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        name_re = re.compile(r'^(\s*name\s*=\s*)"[^"]*"\s*$')
        in_proxy = False
        updated = 0
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == '[[proxies]]':
                in_proxy = True
                new_lines.append(line)
                continue
            if in_proxy:
                matched = name_re.match(line)
                if matched:
                    new_name = str(uuid.uuid4())
                    newline = '\r\n' if line.endswith('\r\n') else '\n'
                    new_lines.append(f'{matched.group(1)}"{new_name}"{newline}')
                    updated += 1
                    in_proxy = False
                    continue
                if stripped.startswith('[[') or stripped.startswith('['):
                    in_proxy = False
            new_lines.append(line)
        if updated:
            with open(config_path, 'w', encoding='utf-8', newline='') as f:
                f.writelines(new_lines)
        return {'ok': True, 'updated': updated}
    except Exception as e:
        return {'ok': False, 'reason': str(e), 'updated': 0}


def load_frpc_status_map(base_dir, timeout=10):
    frpc_path = current_frpc_binary_path(base_dir)
    config_path = current_frpc_config_path(base_dir)
    if not os.path.exists(frpc_path):
        return {'ok': False, 'reason': 'frpc 可执行文件不存在: ' + frpc_path, 'items': {}}
    if not os.path.exists(config_path):
        return {'ok': False, 'reason': 'frpc.toml 不存在: ' + config_path, 'items': {}}
    try:
        kwargs = {
            'cwd': frp_bin_dir(base_dir),
            'capture_output': True,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'timeout': timeout,
        }
        if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        result = subprocess.run([frpc_path, '-c', config_path, 'status'], **kwargs)
        if result.returncode != 0:
            reason = (result.stderr or result.stdout or '').strip() or f'退出码 {result.returncode}'
            return {'ok': False, 'reason': reason, 'items': {}}
        items = {}
        for raw_line in (result.stdout or '').splitlines():
            line = (raw_line or '').strip()
            if not line or line.startswith('Proxy Status') or line in {'TCP', 'UDP', 'HTTP', 'HTTPS', 'STCP', 'XTCP', 'SUDP'}:
                continue
            if line.startswith('Name ') or line.startswith('Name\t'):
                continue
            parts = re.split(r'\s{2,}', line)
            if len(parts) < 4:
                continue
            name = str(parts[0] or '').strip()
            status = str(parts[1] or '').strip()
            local_addr = str(parts[2] or '').strip()
            remote_addr = str(parts[-1] or '').strip()
            if not name:
                continue
            items[name] = {
                'name': name,
                'status': status,
                'local_addr': local_addr,
                'remote_addr': remote_addr,
            }
        return {'ok': True, 'items': items}
    except Exception as e:
        return {'ok': False, 'reason': str(e), 'items': {}}


def load_frpc_mapping_summary(base_dir):
    config_path = current_frpc_config_path(base_dir)
    if not os.path.exists(config_path):
        return {'ok': False, 'reason': 'frpc.toml 不存在', 'items': []}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        parsed = parse_frpc_toml(content)
        server_addr = (parsed.get('serverAddr') or '').strip()
        proxies = parsed.get('proxies') or []
        status_summary = load_frpc_status_map(base_dir)
        status_map = status_summary.get('items') or {}
        items = []
        for proxy in proxies:
            name = str((proxy or {}).get('name') or '-').strip() or '-'
            proxy_type = str((proxy or {}).get('type') or 'tcp').strip().lower() or 'tcp'
            local_ip = str((proxy or {}).get('localIP') or '127.0.0.1').strip() or '127.0.0.1'
            local_port = (proxy or {}).get('localPort')
            status_item = status_map.get(name) or {}
            actual_remote = str(status_item.get('remote_addr') or '').strip()
            actual_local = str(status_item.get('local_addr') or '').strip()
            items.append({
                'name': name,
                'type': proxy_type,
                'local': actual_local or (f'{local_ip}:{local_port}' if local_port else local_ip),
                'remote': actual_remote or '-',
                'url': status_url_from_remote(proxy_type, actual_remote),
                'status': status_item.get('status') or '',
                'runtime_remote': actual_remote,
            })
        return {
            'ok': True,
            'server_addr': server_addr or '-',
            'server_port': parsed.get('serverPort'),
            'items': items,
            'runtime': status_summary,
        }
    except Exception as e:
        return {'ok': False, 'reason': str(e), 'items': []}
