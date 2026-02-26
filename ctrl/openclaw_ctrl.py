import datetime
import json
import os
import socket
import subprocess
import shutil

from flask import Blueprint, request

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task
from lib import packages_utils


openclaw_bp = Blueprint('openclaw', __name__)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')


def _is_openclaw_installed():
    if shutil.which('openclaw'):
        return True
    info = packages_utils.list_npm_packages()
    if not info.get('success'):
        return False
    packages = info.get('packages') or []
    for p in packages:
        if (p.get('name') or '').strip().lower() == 'openclaw':
            return True
    return False


def _openclaw_install_check():
    if shutil.which('openclaw'):
        return True, 'path'
    info = packages_utils.list_npm_packages()
    if not info.get('success'):
        return False, 'npm_list_failed'
    packages = info.get('packages') or []
    for p in packages:
        if (p.get('name') or '').strip().lower() == 'openclaw':
            return True, 'npm_list'
    return False, 'not_found'


@openclaw_bp.route('/api/openclaw/install_state')
def api_openclaw_install_state():
    installed, reason = _openclaw_install_check()
    return api_ok({'installed': installed, 'reason': reason})


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


@openclaw_bp.route('/api/openclaw/cron/list')
def api_openclaw_cron_list():
    installed, reason = _openclaw_install_check()
    if not installed:
        return api_ok({'jobs': [], 'installed': False, 'reason': reason})

    try:
        result = subprocess.run(
            ['openclaw', 'cron', 'list', '--json'],
            capture_output=True,
            text=True,
            timeout=30
        )
        stdout = result.stdout or ''
        if result.returncode != 0 and not stdout.strip():
            return api_ok({'jobs': []})
        if not stdout.strip():
            return api_ok({'jobs': []})
        try:
            output = json.loads(stdout)
        except Exception:
            return api_error('输出解析失败', status=500)
        if isinstance(output, list):
            return api_ok({'jobs': output})
        if isinstance(output, dict):
            return api_ok(output)
        return api_ok({'jobs': []})
    except FileNotFoundError:
        return api_ok({'jobs': []})
    except subprocess.TimeoutExpired:
        return api_error('Command timeout', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@openclaw_bp.route('/api/openclaw/cron/add', methods=['POST'])
def api_openclaw_cron_add():
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    time_type = (data.get('timeType') or '').strip()
    schedule = (data.get('schedule') or '').strip()

    if not message:
        return api_error('Missing message', status=400)
    if time_type not in ('at', 'cron'):
        return api_error('Invalid timeType', status=400)
    if not schedule:
        return api_error('Missing schedule', status=400)
    installed, reason = _openclaw_install_check()
    if not installed:
        return api_error('OpenClaw not installed: ' + reason, status=404)

    name = message
    try:
        result = subprocess.run(
            ['openclaw', 'cron', 'add', '--name', name, '--' + time_type, schedule, '--message', '🔔 ' + message, '--delete-after-run'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return api_error(result.stderr or 'Command failed', status=500)
        stdout = result.stdout or ''
        if not stdout.strip():
            return api_ok({'success': True})
        try:
            output = json.loads(stdout)
        except Exception:
            output = stdout
        return api_ok({'result': output})
    except FileNotFoundError:
        return api_error('OpenClaw not installed: path', status=404)
    except subprocess.TimeoutExpired:
        return api_error('Command timeout', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@openclaw_bp.route('/api/openclaw/cron/remove', methods=['POST'])
def api_openclaw_cron_remove():
    data = request.get_json(silent=True) or {}
    job_id = (data.get('jobId') or '').strip()
    if not job_id:
        return api_error('Missing jobId', status=400)
    installed, reason = _openclaw_install_check()
    if not installed:
        return api_error('OpenClaw not installed: ' + reason, status=404)
    try:
        result = subprocess.run(
            ['openclaw', 'cron', 'remove', job_id],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return api_error(result.stderr or 'Command failed', status=500)
        stdout = result.stdout or ''
        if not stdout.strip():
            return api_ok({'success': True})
        try:
            output = json.loads(stdout)
        except Exception:
            output = stdout
        return api_ok({'result': output})
    except FileNotFoundError:
        return api_error('OpenClaw not installed: path', status=404)
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
    
    parts = cmd.split()
    is_list = 'cron' in parts and 'list' in parts and '--json' in parts
    if not _is_openclaw_installed():
        if is_list:
            return api_ok({'jobs': []})
        return api_error('OpenClaw not installed', status=404)

    cli_args = parts[1:] if parts and parts[0] == 'openclaw' else parts

    try:
        result = subprocess.run(
            ['openclaw'] + cli_args,
            capture_output=True,
            text=True,
            timeout=30
        )
        stdout = result.stdout or ''
        if result.returncode != 0 and is_list and not stdout.strip():
            return api_ok({'jobs': []})
        try:
            import json
            output = json.loads(stdout) if stdout.strip() else ({'jobs': []} if is_list else '')
        except:
            output = stdout
        if is_list and output == '':
            output = {'jobs': []}
        return api_ok(output)
    except FileNotFoundError:
        if is_list:
            return api_ok({'jobs': []})
        return api_error('OpenClaw not installed', status=404)
    except subprocess.TimeoutExpired:
        return api_error('Command timeout', status=500)
    except Exception as e:
        return api_error(str(e), status=500)
