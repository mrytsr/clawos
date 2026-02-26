import datetime
import json
import os
import socket
import subprocess

from flask import Blueprint, request

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task
from lib import packages_utils


openclaw_bp = Blueprint('openclaw', __name__)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')


def _is_openclaw_installed():
    info = packages_utils.list_npm_packages()
    if not info.get('success'):
        return False
    packages = info.get('packages') or []
    for p in packages:
        if (p.get('name') or '').strip().lower() == 'openclaw':
            return True
    return False


@openclaw_bp.route('/api/openclaw/install_state')
def api_openclaw_install_state():
    installed = _is_openclaw_installed()
    return api_ok({'installed': installed})


@openclaw_bp.route('/api/openclaw/install', methods=['POST'])
def api_openclaw_install():
    def _do():
        r = packages_utils.install_npm_package('openclaw')
        if not r.get('success'):
            raise RuntimeError(r.get('message') or 'install failed')

    task_id = create_task(_do, name='openclaw install')
    return api_ok({'taskId': task_id})


@openclaw_bp.route('/api/openclaw/reinstall', methods=['POST'])
def api_openclaw_reinstall():
    def _do():
        packages_utils.uninstall_npm_package('openclaw')
        r = packages_utils.install_npm_package('openclaw')
        if not r.get('success'):
            raise RuntimeError(r.get('message') or 'install failed')

    task_id = create_task(_do, name='openclaw reinstall')
    return api_ok({'taskId': task_id})


@openclaw_bp.route('/api/openclaw/uninstall', methods=['POST'])
def api_openclaw_uninstall():
    def _do():
        r = packages_utils.uninstall_npm_package('openclaw')
        if not r.get('success'):
            raise RuntimeError(r.get('message') or 'uninstall failed')

    task_id = create_task(_do, name='openclaw uninstall')
    return api_ok({'taskId': task_id})


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

    import platform
    os_text = ''
    try:
        if hasattr(os, 'uname'):
            u = os.uname()
            os_text = f'{u.sysname} {u.release} {u.machine}'
        else:
            os_text = platform.platform()
    except Exception:
        os_text = platform.platform()

    node_ver = ''
    try:
        node_ver = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=3).stdout.strip()
        if node_ver.startswith('v'):
            node_ver = node_ver[1:]
    except Exception:
        node_ver = ''

    result['overview'] = {
        'version': '2026.2.2',
        'os': os_text,
        'node': node_ver,
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


@openclaw_bp.route('/api/openclaw/exec', methods=['POST'])
def api_openclaw_exec():
    """执行 OpenClaw CLI 命令"""
    from flask import request
    data = request.get_json(silent=True) or {}
    command = data.get('command', '').strip()
    
    if not command:
        return api_error('Missing command', status=400)
    
    # 安全检查：只允许特定的 cron 命令
    allowed_prefixes = ['cron ']
    if not any(command.startswith(p) for p in allowed_prefixes):
        return api_error('Command not allowed', status=403)
    
    try:
        result = subprocess.run(
            ['openclaw'] + command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        return api_ok({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return api_error('Command timeout', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@openclaw_bp.route('/exec')
def api_exec_simple():
    """简单的命令执行接口（用于前端）"""
    import urllib.parse
    cmd = request.args.get('cmd', '').strip()
    
    if not cmd:
        return api_error('Missing cmd', status=400)
    
    # 安全检查：只允许 openclaw cron 命令
    if 'cron' not in cmd:
        return api_error('Command not allowed', status=403)
    
    try:
        # 解析命令
        parts = cmd.split()
        # 去除 "openclaw" 前缀
        cli_args = parts[1:] if len(parts) > 1 else []
        
        result = subprocess.run(
            ['openclaw'] + cli_args,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # 尝试解析 JSON 输出
        try:
            import json
            output = json.loads(result.stdout)
        except:
            output = result.stdout
        
        return api_ok(output)
    except subprocess.TimeoutExpired:
        return api_error('Command timeout', status=500)
    except Exception as e:
        return api_error(str(e), status=500)
