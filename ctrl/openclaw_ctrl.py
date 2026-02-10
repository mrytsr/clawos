import datetime
import json
import os
import socket
import subprocess

from flask import Blueprint

from ctrl import api_error, api_ok


openclaw_bp = Blueprint('openclaw', __name__)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')


@openclaw_bp.route('/api/openclaw/config')
def api_openclaw_config():
    try:
        if not os.path.exists(OPENCLAW_CONFIG_PATH):
            return api_error('配置文件不存在')

        with open(OPENCLAW_CONFIG_PATH, 'r') as f:
            config = json.load(f)

        simplified = {
            'version': config.get('meta', {}).get('lastTouchedVersion', 'Unknown'),
            'models': {
                'count': 0,
                'list': []
            },
            'channels': {},
            'gateway': {},
            'auth': {}
        }

        providers = config.get('models', {}).get('providers', {})
        for provider_name, provider_data in providers.items():
            models = provider_data.get('models', [])
            for m in models:
                simplified['models']['list'].append({
                    'id': m.get('id', ''),
                    'name': m.get('name', m.get('id', '')),
                    'reasoning': m.get('reasoning', False)
                })
        simplified['models']['count'] = len(simplified['models']['list'])

        channels = config.get('channels', {})
        for ch_name, ch_data in channels.items():
            simplified['channels'][ch_name] = {
                'enabled': ch_data.get('enabled', False)
            }

        gateway = config.get('gateway', {})
        simplified['gateway'] = {
            'port': gateway.get('port', 18789),
            'bind': gateway.get('bind', 'lan'),
            'tailscale': gateway.get('tailscale', {}).get('mode', 'off')
        }

        auth = config.get('auth', {}).get('profiles', {})
        simplified['auth'] = {
            'profiles': list(auth.keys())
        }

        return api_ok(simplified)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@openclaw_bp.route('/api/openclaw/status')
def api_openclaw_status():
    result = {
        'overview': {},
        'gateway': {},
        'agents': [],
        'channels': {},
        'diagnosis': {
            'warnings': [],
            'checks': {}
        }
    }

    result['overview'] = {
        'version': '2026.2.2',
        'os': f'{os.uname().sysname} {os.uname().release} {os.uname().machine}',
        'node': subprocess.run(['node', '--version'], capture_output=True, text=True).stdout.strip().replace('v', ''),
        'dashboard': 'http://127.0.0.1:18789/',
        'tailscale': 'off',
        'channel': 'stable'
    }

    gateway_port = 18789
    port_used = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        conn_result = sock.connect_ex(('127.0.0.1', gateway_port))
        port_used = (conn_result == 0)
        sock.close()
    except:
        pass

    gateway_process = None
    try:
        ps_result = subprocess.run(
            ['ps', 'aux'], capture_output=True, text=True
        )
        for line in ps_result.stdout.split('\n'):
            if 'openclaw-gateway' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 1:
                    gateway_process = {
                        'pid': int(parts[1]),
                        'running': True
                    }
                break
    except:
        pass

    result['gateway'] = {
        'port': gateway_port,
        'port_used': port_used,
        'auth': True,
        'latency_ms': None,
        'service_running': gateway_process is not None,
        'service_pid': gateway_process['pid'] if gateway_process else None
    }

    if port_used:
        import time
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('127.0.0.1', gateway_port))
            sock.close()
            result['gateway']['latency_ms'] = int((time.time() - start) * 1000)
        except:
            result['gateway']['latency_ms'] = None

    try:
        agents_dir = os.path.expanduser('~/.openclaw/agents')
        if os.path.exists(agents_dir):
            for name in os.listdir(agents_dir):
                agent_path = os.path.join(agents_dir, name)
                if not os.path.isdir(agent_path):
                    continue

                sessions_file = os.path.join(agent_path, 'sessions', 'sessions.json')
                active_ago = None
                sessions_count = 0
                try:
                    if os.path.exists(sessions_file):
                        with open(sessions_file, 'r') as f:
                            sessions = json.load(f)
                        sessions_count = len(sessions.get('sessions', []))
                        last_active = sessions.get('last_active')
                        if last_active:
                            dt = datetime.datetime.fromtimestamp(int(last_active) / 1000)
                            delta = datetime.datetime.now() - dt
                            if delta.days > 0:
                                active_ago = f'{delta.days}天前'
                            elif delta.seconds > 3600:
                                active_ago = f'{delta.seconds//3600}小时前'
                            elif delta.seconds > 60:
                                active_ago = f'{delta.seconds//60}分钟前'
                            else:
                                active_ago = '刚刚'
                except:
                    pass

                status = 'ok' if sessions_count > 0 else 'pending'
                result['agents'].append({
                    'id': name,
                    'name': name,
                    'status': status,
                    'sessions': sessions_count,
                    'active_ago': active_ago
                })
    except:
        pass

    try:
        if os.path.exists(OPENCLAW_CONFIG_PATH):
            with open(OPENCLAW_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            channels = config.get('channels', {})
            for ch_name, ch_data in channels.items():
                enabled = ch_data.get('enabled', False)
                accounts = ch_data.get('accounts', [])
                accounts_ok = sum(1 for a in accounts if a.get('status') == 'ok')
                result['channels'][ch_name] = {
                    'enabled': enabled,
                    'status': 'ok' if enabled else 'not_configured',
                    'accounts_total': len(accounts),
                    'accounts_ok': accounts_ok if enabled else 0
                }
    except:
        pass

    if port_used:
        result['diagnosis']['warnings'].append({
            'message': f'端口{gateway_port}被占用',
            'level': 'warning'
        })

    skills_dir = os.path.expanduser('~/.openclaw/skills')
    skills_eligible = 0
    if os.path.exists(skills_dir):
        for root, dirs, files in os.walk(skills_dir):
            if 'SKILL.md' in files:
                skills_eligible += 1

    result['diagnosis']['checks']['skills'] = {
        'eligible': skills_eligible,
        'missing': 0
    }

    return api_ok(result)
