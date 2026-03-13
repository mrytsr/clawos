import datetime
import json
import os
import socket
import subprocess
import shutil

from flask import Blueprint, request, jsonify, render_template, redirect

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task
from lib import packages_utils


openclaw_bp = Blueprint('openclaw', __name__)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')

@openclaw_bp.route('/openclaw-config')
def openclaw_config_page():
    return redirect('/openclaw_config')


@openclaw_bp.route('/openclaw_config')
def openclaw_config_page_v2():
    return render_template('openclaw_config.html')

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


def _to_float_or_none(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _to_int_or_none(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _normalize_input_list(v):
    if v is None:
        return None
    if isinstance(v, list):
        out = []
        for x in v:
            sx = str(x).strip()
            if sx:
                out.append(sx)
        return out
    s = str(v).strip()
    if not s:
        return None
    return [x.strip() for x in s.split(',') if x.strip()]


def _resolve_provider_field(data, primary_key, alias_key):
    if primary_key in data:
        return data.get(primary_key)
    return data.get(alias_key)


def _upsert_provider_meta(provider_section, data):
    if not isinstance(provider_section, dict):
        provider_section = {}
    provider_base_url = _resolve_provider_field(data, 'providerBaseUrl', 'baseUrl')
    provider_api = _resolve_provider_field(data, 'providerApi', 'api')
    provider_api_key = _resolve_provider_field(data, 'providerApiKey', 'apiKey')

    if provider_base_url is not None:
        provider_section['baseUrl'] = str(provider_base_url).strip()
    elif 'baseUrl' not in provider_section:
        provider_section['baseUrl'] = ''

    if provider_api is not None:
        provider_section['api'] = str(provider_api).strip() or 'openai-completions'
    elif not isinstance(provider_section.get('api'), str) or not provider_section.get('api'):
        provider_section['api'] = 'openai-completions'

    if provider_api_key is not None:
        key_text = str(provider_api_key).strip()
        if key_text:
            provider_section['apiKey'] = key_text
    elif 'apiKey' not in provider_section:
        provider_section['apiKey'] = ''

    models_list = provider_section.get('models')
    if not isinstance(models_list, list):
        provider_section['models'] = []
    return provider_section


def _build_model_entry(data, fallback_name=''):
    model_id = (data.get('id') or '').strip()
    name = (data.get('name') or '').strip() or fallback_name or model_id
    reasoning = bool(data.get('reasoning', False))
    input_types = _normalize_input_list(data.get('input'))
    context_window = _to_int_or_none(data.get('contextWindow'))
    max_tokens = _to_int_or_none(data.get('maxTokens'))
    cost_input = _to_float_or_none((data.get('cost') or {}).get('input') if isinstance(data.get('cost'), dict) else data.get('costInput'))
    cost_output = _to_float_or_none((data.get('cost') or {}).get('output') if isinstance(data.get('cost'), dict) else data.get('costOutput'))
    cost_cache_read = _to_float_or_none((data.get('cost') or {}).get('cacheRead') if isinstance(data.get('cost'), dict) else data.get('costCacheRead'))
    cost_cache_write = _to_float_or_none((data.get('cost') or {}).get('cacheWrite') if isinstance(data.get('cost'), dict) else data.get('costCacheWrite'))

    item = {
        'id': model_id,
        'name': name,
        'reasoning': reasoning,
    }
    if input_types is not None:
        item['input'] = input_types
    if context_window is not None:
        item['contextWindow'] = context_window
    if max_tokens is not None:
        item['maxTokens'] = max_tokens
    if any(x is not None for x in [cost_input, cost_output, cost_cache_read, cost_cache_write]):
        item['cost'] = {}
        if cost_input is not None:
            item['cost']['input'] = cost_input
        if cost_output is not None:
            item['cost']['output'] = cost_output
        if cost_cache_read is not None:
            item['cost']['cacheRead'] = cost_cache_read
        if cost_cache_write is not None:
            item['cost']['cacheWrite'] = cost_cache_write
    return item


def _openclaw_agents_dir():
    return os.path.expanduser('~/.openclaw/agents')


def _safe_agent_id(agent_id):
    s = (agent_id or '').strip()
    if not s:
        return None
    bad = ['..', '/', '\\', '\0']
    if any(x in s for x in bad):
        return None
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
    if any(ch not in allowed for ch in s):
        return None
    return s


def _collect_openclaw_agents():
    agents = []
    agents_dir = _openclaw_agents_dir()
    if not os.path.exists(agents_dir):
        return agents

    for name in os.listdir(agents_dir):
        agent_path = os.path.join(agents_dir, name)
        if not os.path.isdir(agent_path):
            continue

        sessions_file = os.path.join(agent_path, 'sessions', 'sessions.json')
        active_ago = None
        sessions_count = 0
        try:
            if os.path.exists(sessions_file):
                with open(sessions_file, 'r', encoding='utf-8') as f:
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
        except Exception:
            pass

        status = 'ok' if sessions_count > 0 else 'pending'
        agents.append({
            'id': name,
            'name': name,
            'status': status,
            'sessions': sessions_count,
            'active_ago': active_ago
        })
    return agents


def _safe_channel_name(name):
    s = (name or '').strip()
    if not s:
        return None
    bad = ['..', '/', '\\', '\0']
    if any(x in s for x in bad):
        return None
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
    if any(ch not in allowed for ch in s):
        return None
    return s


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
    provider_configs = {}
    models = []
    providers_map = models_section.get('providers') or {}
    if isinstance(providers_map, dict):
        providers = list(providers_map.keys())
        for provider_name, provider_data in providers_map.items():
            p = provider_data if isinstance(provider_data, dict) else {}
            api_key = str(p.get('apiKey') or '')
            provider_configs[provider_name] = {
                'baseUrl': p.get('baseUrl') or '',
                'api': p.get('api') or 'openai-completions',
                'hasApiKey': bool(api_key.strip()),
                'apiKeyMasked': ('*' * max(0, len(api_key.strip()) - 4) + api_key.strip()[-4:]) if api_key.strip() else '',
            }

    for provider_name, m in _iter_models(config):
        cost = m.get('cost') if isinstance(m.get('cost'), dict) else {}
        models.append({
            'provider': provider_name,
            'id': m.get('id', ''),
            'name': m.get('name', m.get('id', '')),
            'reasoning': bool(m.get('reasoning', False)),
            'input': m.get('input') if isinstance(m.get('input'), list) else [],
            'cost': {
                'input': cost.get('input'),
                'output': cost.get('output'),
                'cacheRead': cost.get('cacheRead'),
                'cacheWrite': cost.get('cacheWrite'),
            },
            'contextWindow': m.get('contextWindow'),
            'maxTokens': m.get('maxTokens'),
            'providerBaseUrl': (provider_configs.get(provider_name) or {}).get('baseUrl', ''),
            'providerApi': (provider_configs.get(provider_name) or {}).get('api', 'openai-completions'),
            'providerHasApiKey': (provider_configs.get(provider_name) or {}).get('hasApiKey', False),
            'providerApiKeyMasked': (provider_configs.get(provider_name) or {}).get('apiKeyMasked', ''),
            'default': bool(default_id and m.get('id') == default_id),
        })

    return api_ok({
        'providers': providers,
        'providerConfigs': provider_configs,
        'defaultModelId': default_id,
        'models': models
    })


@openclaw_bp.route('/api/openclaw/models/add', methods=['POST'])
def api_openclaw_models_add():
    data = request.get_json(silent=True) or {}
    provider = (data.get('provider') or '').strip() or 'default'
    model_id = (data.get('id') or '').strip()
    name = (data.get('name') or '').strip()

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
    provider_section = _upsert_provider_meta(provider_section, data)
    models_list = provider_section.setdefault('models', [])
    if not isinstance(models_list, list):
        return api_error('配置文件格式错误', status=500)

    for m in models_list:
        if isinstance(m, dict) and (m.get('id') or '').strip() == model_id:
            return api_error('Model already exists', status=409)

    entry = _build_model_entry(data, fallback_name=name or model_id)
    models_list.append(entry)
    provider_section['models'] = models_list
    providers_map[provider] = provider_section
    models_section['providers'] = providers_map
    config['models'] = models_section

    _save_openclaw_config_raw(config)
    return api_ok({'provider': provider, 'id': model_id})


@openclaw_bp.route('/api/openclaw/models/update', methods=['POST'])
def api_openclaw_models_update():
    data = request.get_json(silent=True) or {}
    provider = (data.get('provider') or '').strip() or 'default'
    model_id = (data.get('id') or '').strip()
    new_model_id = (data.get('newId') or '').strip() or model_id
    if not model_id:
        return api_error('Missing model id', status=400)
    if not new_model_id:
        return api_error('Missing new model id', status=400)

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

    provider_section = providers_map.get(provider) or {}
    if not isinstance(provider_section, dict):
        return api_error('Provider not found', status=404)
    provider_section = _upsert_provider_meta(provider_section, data)
    models_list = provider_section.get('models') or []
    if not isinstance(models_list, list):
        return api_error('配置文件格式错误', status=500)

    target_idx = -1
    for idx, m in enumerate(models_list):
        if isinstance(m, dict) and (m.get('id') or '').strip() == model_id:
            target_idx = idx
            break
    if target_idx < 0:
        return api_error('Model not found', status=404)

    for idx, m in enumerate(models_list):
        if idx == target_idx:
            continue
        if isinstance(m, dict) and (m.get('id') or '').strip() == new_model_id:
            return api_error('Model id already exists', status=409)

    current = models_list[target_idx] if isinstance(models_list[target_idx], dict) else {}
    merge_data = dict(current)
    merge_data.update(data)
    merge_data['id'] = new_model_id
    if 'name' not in data and isinstance(current.get('name'), str) and current.get('name').strip():
        merge_data['name'] = current.get('name').strip()
    updated_entry = _build_model_entry(merge_data, fallback_name=new_model_id)
    models_list[target_idx] = updated_entry

    default_id, default_key = _get_default_model_id(models_section)
    if default_id == model_id and new_model_id != model_id:
        if default_key:
            models_section[default_key] = new_model_id
        else:
            models_section['defaultModelId'] = new_model_id

    provider_section['models'] = models_list
    providers_map[provider] = provider_section
    models_section['providers'] = providers_map
    config['models'] = models_section
    _save_openclaw_config_raw(config)
    return api_ok({'provider': provider, 'id': new_model_id})


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


@openclaw_bp.route('/api/openclaw/agents/list')
def api_openclaw_agents_list():
    try:
        agents = _collect_openclaw_agents()
        agents.sort(key=lambda a: (a.get('id') or '').lower())
        return api_ok({'agents': agents})
    except Exception as e:
        return api_error(str(e), status=500)


@openclaw_bp.route('/api/openclaw/agents/add', methods=['POST'])
def api_openclaw_agents_add():
    data = request.get_json(silent=True) or {}
    agent_id = _safe_agent_id(data.get('id') or data.get('name'))
    if not agent_id:
        return api_error('Invalid agent id', status=400)

    agents_dir = _openclaw_agents_dir()
    agent_path = os.path.join(agents_dir, agent_id)
    if os.path.exists(agent_path):
        return api_error('Agent already exists', status=409)

    os.makedirs(os.path.join(agent_path, 'sessions'), exist_ok=True)
    sessions_file = os.path.join(agent_path, 'sessions', 'sessions.json')
    if not os.path.exists(sessions_file):
        with open(sessions_file, 'w', encoding='utf-8') as f:
            json.dump({'sessions': [], 'last_active': None}, f, ensure_ascii=False, indent=2)

    return api_ok({'id': agent_id})


@openclaw_bp.route('/api/openclaw/agents/rename', methods=['POST'])
def api_openclaw_agents_rename():
    data = request.get_json(silent=True) or {}
    old_id = _safe_agent_id(data.get('from') or data.get('oldId') or data.get('old') or data.get('id'))
    new_id = _safe_agent_id(data.get('to') or data.get('newId') or data.get('new'))
    if not old_id or not new_id:
        return api_error('Invalid agent id', status=400)
    if old_id == new_id:
        return api_ok({'id': new_id})

    agents_dir = _openclaw_agents_dir()
    old_path = os.path.join(agents_dir, old_id)
    new_path = os.path.join(agents_dir, new_id)
    if not os.path.exists(old_path):
        return api_error('Agent not found', status=404)
    if os.path.exists(new_path):
        return api_error('Target agent already exists', status=409)

    os.rename(old_path, new_path)
    return api_ok({'id': new_id})


@openclaw_bp.route('/api/openclaw/agents/remove', methods=['POST'])
def api_openclaw_agents_remove():
    data = request.get_json(silent=True) or {}
    agent_id = _safe_agent_id(data.get('id') or data.get('name'))
    if not agent_id:
        return api_error('Invalid agent id', status=400)

    agents_dir = _openclaw_agents_dir()
    agent_path = os.path.join(agents_dir, agent_id)
    if not os.path.exists(agent_path):
        return api_ok({'removed': False})

    shutil.rmtree(agent_path, ignore_errors=True)
    return api_ok({'removed': True})


@openclaw_bp.route('/api/openclaw/channels/list')
def api_openclaw_channels_list():
    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    channels_map = config.get('channels') or {}
    if not isinstance(channels_map, dict):
        return api_error('配置文件格式错误', status=500)

    channels = []
    for name, data in channels_map.items():
        if not isinstance(data, dict):
            data = {}
        channels.append({
            'name': name,
            'enabled': bool(data.get('enabled', False)),
            'raw': data,
        })
    channels.sort(key=lambda c: (c.get('name') or '').lower())
    return api_ok({'channels': channels})


@openclaw_bp.route('/api/openclaw/channels/add', methods=['POST'])
def api_openclaw_channels_add():
    data = request.get_json(silent=True) or {}
    name = _safe_channel_name(data.get('name') or data.get('id'))
    enabled = bool(data.get('enabled', False))
    if not name:
        return api_error('Invalid channel name', status=400)

    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    channels_map = config.setdefault('channels', {})
    if not isinstance(channels_map, dict):
        return api_error('配置文件格式错误', status=500)
    if name in channels_map:
        return api_error('Channel already exists', status=409)

    channels_map[name] = {'enabled': enabled}
    config['channels'] = channels_map
    _save_openclaw_config_raw(config)
    return api_ok({'name': name})


@openclaw_bp.route('/api/openclaw/channels/update', methods=['POST'])
def api_openclaw_channels_update():
    data = request.get_json(silent=True) or {}
    name = _safe_channel_name(data.get('name') or data.get('id'))
    new_name = _safe_channel_name(data.get('newName') or data.get('to') or data.get('renameTo')) if (data.get('newName') or data.get('to') or data.get('renameTo')) else None
    enabled = data.get('enabled', None)

    if not name:
        return api_error('Invalid channel name', status=400)

    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    channels_map = config.get('channels') or {}
    if not isinstance(channels_map, dict):
        return api_error('配置文件格式错误', status=500)
    if name not in channels_map:
        return api_error('Channel not found', status=404)

    ch = channels_map.get(name) or {}
    if not isinstance(ch, dict):
        ch = {}
    if enabled is not None:
        ch['enabled'] = bool(enabled)

    target_name = new_name or name
    if new_name and new_name != name:
        if new_name in channels_map:
            return api_error('Target channel already exists', status=409)
        del channels_map[name]
        channels_map[new_name] = ch
    else:
        channels_map[name] = ch

    config['channels'] = channels_map
    _save_openclaw_config_raw(config)
    return api_ok({'name': target_name})


@openclaw_bp.route('/api/openclaw/channels/remove', methods=['POST'])
def api_openclaw_channels_remove():
    data = request.get_json(silent=True) or {}
    name = _safe_channel_name(data.get('name') or data.get('id'))
    if not name:
        return api_error('Invalid channel name', status=400)

    try:
        config = _load_openclaw_config_raw()
    except FileNotFoundError as e:
        return api_error(str(e), status=404)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)

    channels_map = config.get('channels') or {}
    if not isinstance(channels_map, dict):
        return api_error('配置文件格式错误', status=500)
    if name not in channels_map:
        return api_ok({'removed': False})

    del channels_map[name]
    config['channels'] = channels_map
    _save_openclaw_config_raw(config)
    return api_ok({'removed': True})


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
