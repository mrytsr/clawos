import datetime
import json
import os
import socket
import subprocess
import shutil

from flask import Blueprint, request, jsonify

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task
from lib import packages_utils


openclaw_bp = Blueprint('openclaw', __name__)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')

def _load_openclaw_config_raw():
    if not os.path.exists(OPENCLAW_CONFIG_PATH):
        raise FileNotFoundError('配置文件不存在')
    with open(OPENCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_openclaw_config_raw(config):
    with open(OPENCLAW_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _get_default_model_id(models_section):
    if not isinstance(models_section, dict):
        return None, None
    for k in ('defaultModelId', 'defaultModel', 'default'):
        v = models_section.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip(), k
        if isinstance(v, dict):
            vid = v.get('id')
            if isinstance(vid, str) and vid.strip():
                return vid.strip(), k
    return None, None


def _iter_models(config):
    providers = (config.get('models') or {}).get('providers') or {}
    for provider_name, provider_data in providers.items():
        models = provider_data.get('models') or []
        if not isinstance(models, list):
            continue
        for m in models:
            if not isinstance(m, dict):
                continue
            yield provider_name, m


def _openclaw_install_check():
    env = {}
    try:
        env = packages_utils.get_npm_env()
    except Exception:
        env = os.environ.copy()

    env_path = env.get('PATH') or ''
    env_path_parts = [p for p in env_path.split(os.pathsep) if p]
    extra_bins = [os.path.expanduser('~/.local/bin'), '/usr/local/bin', '/usr/bin']
    for p in reversed(extra_bins):
        if p and p not in env_path_parts:
            env_path_parts.insert(0, p)
    env['PATH'] = os.pathsep.join(env_path_parts)

    path = env.get('PATH') or ''
    cmd = shutil.which('openclaw', path=path) or shutil.which('openclaw')
    if cmd:
        return {'installed': True, 'reason': 'path', 'cmd': cmd, 'env': env}

    npm_cmd = None
    try:
        npm_cmd = packages_utils.find_npm()
    except Exception:
        npm_cmd = None

    if npm_cmd:
        npm_bin = ''
        try:
            npm_bin = subprocess.run(
                [npm_cmd, 'bin', '-g'],
                capture_output=True,
                text=True,
                timeout=5,
                env=env,
            ).stdout.strip()
        except Exception:
            npm_bin = ''
        if npm_bin:
            env2 = dict(env)
            env2['PATH'] = npm_bin + os.pathsep + (env.get('PATH') or '')
            cmd2 = shutil.which('openclaw', path=env2.get('PATH') or '')
            if cmd2:
                return {'installed': True, 'reason': 'npm_bin', 'cmd': cmd2, 'env': env2}
            env = env2

    info = packages_utils.list_npm_packages()
    if not info.get('success'):
        return {'installed': False, 'reason': 'npm_list_failed'}
    packages = info.get('packages') or []
    for p in packages:
        if (p.get('name') or '').strip().lower() == 'openclaw':
            return {'installed': False, 'reason': 'npm_list_no_bin'}
    return {'installed': False, 'reason': 'not_found'}


@openclaw_bp.route('/api/openclaw/install_state')
def api_openclaw_install_state():
    check = _openclaw_install_check()
    return api_ok({'installed': check.get('installed'), 'reason': check.get('reason')})


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


@openclaw_bp.route('/api/openclaw/models/list')
def api_openclaw_models_list():
    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    models_section = config.get('models') or {}
    default_id, _ = _get_default_model_id(models_section)

    providers = []
    models = []
    providers_map = models_section.get('providers') or {}
    if isinstance(providers_map, dict):
        providers = list(providers_map.keys())

    for provider_name, m in _iter_models(config):
        models.append({
            'provider': provider_name,
            'id': m.get('id', ''),
            'name': m.get('name', m.get('id', '')),
            'reasoning': bool(m.get('reasoning', False)),
            'default': bool(default_id and m.get('id') == default_id),
        })

    return api_ok({'providers': providers, 'defaultModelId': default_id, 'models': models})


@openclaw_bp.route('/api/openclaw/models/add', methods=['POST'])
def api_openclaw_models_add():
    data = request.get_json(silent=True) or {}
    provider = (data.get('provider') or '').strip() or 'default'
    model_id = (data.get('id') or '').strip()
    name = (data.get('name') or '').strip()
    reasoning = bool(data.get('reasoning', False))

    if not model_id:
        return api_error('Missing model id', status=400)

    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    models_section = config.setdefault('models', {})
    providers_map = models_section.setdefault('providers', {})
    if not isinstance(providers_map, dict):
        return api_error('配置文件格式错误', status=500)

    provider_section = providers_map.setdefault(provider, {})
    models_list = provider_section.setdefault('models', [])
    if not isinstance(models_list, list):
        return api_error('配置文件格式错误', status=500)

    for m in models_list:
        if isinstance(m, dict) and (m.get('id') or '').strip() == model_id:
            return api_error('Model already exists', status=409)

    models_list.append({
        'id': model_id,
        'name': name or model_id,
        'reasoning': reasoning,
    })

    _save_openclaw_config_raw(config)
    return api_ok({'provider': provider, 'id': model_id})


@openclaw_bp.route('/api/openclaw/models/remove', methods=['POST'])
def api_openclaw_models_remove():
    data = request.get_json(silent=True) or {}
    provider = (data.get('provider') or '').strip()
    model_id = (data.get('modelId') or data.get('id') or '').strip()

    if not model_id:
        return api_error('Missing model id', status=400)

    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    models_section = config.get('models') or {}
    providers_map = models_section.get('providers') or {}
    if not isinstance(providers_map, dict):
        return api_error('配置文件格式错误', status=500)

    removed = 0
    target_providers = [provider] if provider else list(providers_map.keys())
    for p in target_providers:
        provider_section = providers_map.get(p) or {}
        models_list = provider_section.get('models') or []
        if not isinstance(models_list, list):
            continue
        before = len(models_list)
        provider_section['models'] = [m for m in models_list if not (isinstance(m, dict) and (m.get('id') or '').strip() == model_id)]
        providers_map[p] = provider_section
        removed += max(0, before - len(provider_section['models']))

    if removed > 0:
        default_id, default_key = _get_default_model_id(models_section)
        if default_id == model_id and default_key:
            try:
                del models_section[default_key]
            except Exception:
                models_section[default_key] = ''
        config['models'] = models_section
        _save_openclaw_config_raw(config)

    return api_ok({'removed': removed})


@openclaw_bp.route('/api/openclaw/models/set_default', methods=['POST'])
def api_openclaw_models_set_default():
    data = request.get_json(silent=True) or {}
    model_id = (data.get('modelId') or data.get('id') or '').strip()
    if not model_id:
        return api_error('Missing model id', status=400)

    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    exists = False
    for _, m in _iter_models(config):
        if (m.get('id') or '').strip() == model_id:
            exists = True
            break
    if not exists:
        return api_error('Model not found', status=404)

    models_section = config.setdefault('models', {})
    _, default_key = _get_default_model_id(models_section)
    if default_key:
        models_section[default_key] = model_id
    else:
        models_section['defaultModelId'] = model_id
    config['models'] = models_section
    _save_openclaw_config_raw(config)
    return api_ok({'defaultModelId': model_id})


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

    check = _openclaw_install_check()
    if not check.get('installed'):
        return api_error('OpenClaw not installed', status=404)
    
    try:
        result = subprocess.run(
            [check.get('cmd') or 'openclaw'] + command.split(),
            capture_output=True,
            text=True,
            timeout=30,
            env=check.get('env'),
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
    check = _openclaw_install_check()
    installed = bool(check.get('installed'))
    reason = check.get('reason')
    if not installed:
        return api_ok({'jobs': [], 'installed': False, 'reason': reason})

    try:
        result = subprocess.run(
            [check.get('cmd') or 'openclaw', 'cron', 'list', '--json'],
            capture_output=True,
            text=True,
            timeout=30,
            env=check.get('env'),
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
    check = _openclaw_install_check()
    installed = bool(check.get('installed'))
    reason = check.get('reason')
    if not installed:
        return jsonify({
            'success': False,
            'error': {'message': 'OpenClaw not installed'},
            'installed': installed,
            'reason': reason,
        }), 404

    name = message
    result = subprocess.run(
        [check.get('cmd') or 'openclaw', 'cron', 'add', '--name', name, '--' + time_type, schedule, '--message', '🔔 ' + message, '--delete-after-run'],
        capture_output=True,
        text=True,
        timeout=30,
        env=check.get('env'),
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


@openclaw_bp.route('/api/openclaw/cron/remove', methods=['POST'])
def api_openclaw_cron_remove():
    data = request.get_json(silent=True) or {}
    job_id = (data.get('jobId') or '').strip()
    if not job_id:
        return api_error('Missing jobId', status=400)
    check = _openclaw_install_check()
    installed = bool(check.get('installed'))
    reason = check.get('reason')
    if not installed:
        return jsonify({
            'success': False,
            'error': {'message': 'OpenClaw not installed'},
            'installed': installed,
            'reason': reason,
        }), 404
    try:
        result = subprocess.run(
            [check.get('cmd') or 'openclaw', 'cron', 'remove', job_id],
            capture_output=True,
            text=True,
            timeout=30,
            env=check.get('env'),
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
    check = _openclaw_install_check()
    if not check.get('installed'):
        if is_list:
            return api_ok({'jobs': []})
        return api_error('OpenClaw not installed', status=404)

    cli_args = parts[1:] if parts and parts[0] == 'openclaw' else parts

    try:
        result = subprocess.run(
            [check.get('cmd') or 'openclaw'] + cli_args,
            capture_output=True,
            text=True,
            timeout=30,
            env=check.get('env'),
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
