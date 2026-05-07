import os
import platform
import requests
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

import yaml
from flask import Blueprint, redirect, render_template, request

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task, update_task


hermes_bp = Blueprint('hermes', __name__)

HERMES_CONFIG_PATH = os.path.expanduser('~/.hermes/config.yaml')
HERMES_HOME = os.path.dirname(HERMES_CONFIG_PATH)
HERMES_REPO_DIR = os.path.join(HERMES_HOME, 'hermes-agent')
HERMES_VENV_DIR = os.path.join(HERMES_REPO_DIR, 'venv')
HERMES_REPO_ARCHIVE_URL = 'https://github.com/NousResearch/hermes-agent/archive/refs/heads/main.zip'
HERMES_CROSS_PLATFORM_EXTRAS = ['cron', 'cli', 'pty', 'mcp', 'honcho', 'acp', 'web']


@hermes_bp.route('/hermes-config')
def hermes_config_page_legacy():
    return redirect('/hermes_config')


@hermes_bp.route('/hermes_config')
def hermes_config_page():
    return render_template('hermes_config.html')


def _read_hermes_config_text():
    if not os.path.exists(HERMES_CONFIG_PATH):
        return ''
    with open(HERMES_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def _load_hermes_config_data():
    text = _read_hermes_config_text()
    if not text.strip():
        return {}
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _save_hermes_config_text(text):
    parsed = yaml.safe_load(text) if str(text).strip() else {}
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError('配置文件顶层必须是对象')
    os.makedirs(HERMES_HOME, exist_ok=True)
    with open(HERMES_CONFIG_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text if isinstance(text, str) else '')
    return parsed


def _save_hermes_config_data(data):
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError('配置文件顶层必须是对象')
    os.makedirs(HERMES_HOME, exist_ok=True)
    with open(HERMES_CONFIG_PATH, 'w', encoding='utf-8', newline='\n') as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return data


def _ensure_dict(value):
    return value if isinstance(value, dict) else {}


def _ensure_list(value):
    return value if isinstance(value, list) else []


def _normalize_hermes_provider_item(item):
    data = item if isinstance(item, dict) else {}
    return {
        'name': str(data.get('name') or '').strip(),
        'model': str(data.get('model') or '').strip(),
        'base_url': str(data.get('base_url') or '').strip(),
        'api_key': str(data.get('api_key') or '').strip(),
    }


def _get_hermes_models_payload(config):
    cfg = config if isinstance(config, dict) else {}
    model_cfg = _ensure_dict(cfg.get('model'))
    providers = []
    for item in _ensure_list(cfg.get('custom_providers')):
        normalized = _normalize_hermes_provider_item(item)
        if not normalized['name'] and not normalized['model'] and not normalized['base_url'] and not normalized['api_key']:
            continue
        providers.append({
            'name': normalized['name'],
            'model': normalized['model'],
            'base_url': normalized['base_url'],
            'api_key_masked': '******' if normalized['api_key'] else '',
        })
    return {
        'defaultModel': {
            'default': str(model_cfg.get('default') or '').strip(),
            'provider': str(model_cfg.get('provider') or '').strip(),
            'base_url': str(model_cfg.get('base_url') or '').strip(),
            'api_key_masked': '******' if str(model_cfg.get('api_key') or '').strip() else '',
        },
        'providers': providers,
    }


def _platform_label():
    name = (platform.system() or '').lower()
    if name.startswith('win'):
        return 'windows'
    if name.startswith('darwin'):
        return 'macos'
    return 'linux'


def _subprocess_kwargs():
    kwargs = {
        'capture_output': True,
        'text': True,
        'encoding': 'utf-8',
        'errors': 'replace',
    }
    if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _run_command(cmd, cwd=None, task_id=None, step_message=None, timeout=None):
    if task_id and step_message:
        update_task(task_id, status='running', message=step_message)
    result = subprocess.run(
        [str(part) for part in cmd],
        cwd=cwd,
        timeout=timeout,
        **_subprocess_kwargs(),
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or '').strip() or '命令执行失败'
        raise RuntimeError(msg[:1000])
    return result


def _select_python_command():
    candidates = []
    seen = set()

    def add(cmd, label):
        key = tuple(cmd)
        if key in seen:
            return
        seen.add(key)
        candidates.append({'cmd': cmd, 'label': label})

    if sys.executable:
        add([sys.executable], 'current-python')
    if os.name == 'nt':
        add(['py', '-3.11'], 'py-3.11')
        add(['py', '-3'], 'py-3')
    add(['python3.11'], 'python3.11')
    add(['python3'], 'python3')
    add(['python'], 'python')

    check_code = 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
    for item in candidates:
        try:
            result = subprocess.run(
                item['cmd'] + ['-c', check_code],
                timeout=15,
                **_subprocess_kwargs(),
            )
            if result.returncode == 0:
                return item
        except Exception:
            continue
    raise RuntimeError('未找到可用的 Python 3.11+ 解释器')


def _venv_python_path():
    if os.name == 'nt':
        return os.path.join(HERMES_VENV_DIR, 'Scripts', 'python.exe')
    return os.path.join(HERMES_VENV_DIR, 'bin', 'python')


def _venv_hermes_path():
    if os.name == 'nt':
        return os.path.join(HERMES_VENV_DIR, 'Scripts', 'hermes.exe')
    return os.path.join(HERMES_VENV_DIR, 'bin', 'hermes')


def _hermes_launcher_dir():
    return os.path.join(os.path.expanduser('~'), '.local', 'bin')


def _hermes_launcher_paths():
    base_dir = _hermes_launcher_dir()
    if os.name == 'nt':
        return [
            os.path.join(base_dir, 'hermes.cmd'),
            os.path.join(base_dir, 'hermes.ps1'),
        ]
    return [os.path.join(base_dir, 'hermes')]


def _extract_repo_archive(task_id=None):
    if task_id:
        update_task(task_id, status='running', message='正在下载 Hermes 源码', progress=10)
    response = requests.get(HERMES_REPO_ARCHIVE_URL, stream=True, timeout=60)
    response.raise_for_status()
    tmp_dir = tempfile.mkdtemp(prefix='hermes-install-')
    zip_path = os.path.join(tmp_dir, 'hermes-agent.zip')
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(tmp_dir)

    extracted_root = None
    for name in os.listdir(tmp_dir):
        candidate = os.path.join(tmp_dir, name)
        if os.path.isdir(candidate) and name.startswith('hermes-agent-'):
            extracted_root = candidate
            break
    if not extracted_root:
        raise RuntimeError('Hermes 源码解压失败')
    return tmp_dir, extracted_root


def _ensure_hermes_repository(task_id=None):
    os.makedirs(HERMES_HOME, exist_ok=True)
    marker = os.path.join(HERMES_REPO_DIR, 'pyproject.toml')
    if os.path.exists(marker):
        return HERMES_REPO_DIR

    if os.path.exists(HERMES_REPO_DIR):
        backup_path = HERMES_REPO_DIR + '.backup-' + str(int(time.time()))
        os.replace(HERMES_REPO_DIR, backup_path)

    tmp_dir, extracted_root = _extract_repo_archive(task_id=task_id)
    try:
        shutil.move(extracted_root, HERMES_REPO_DIR)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return HERMES_REPO_DIR


def _ensure_hermes_launcher():
    hermes_cmd = _venv_hermes_path()
    if not os.path.exists(hermes_cmd):
        raise RuntimeError('Hermes 命令未生成: ' + hermes_cmd)
    launcher_dir = _hermes_launcher_dir()
    os.makedirs(launcher_dir, exist_ok=True)

    if os.name == 'nt':
        cmd_path = os.path.join(launcher_dir, 'hermes.cmd')
        with open(cmd_path, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(f'@"{hermes_cmd}" %*\r\n')
        ps1_path = os.path.join(launcher_dir, 'hermes.ps1')
        with open(ps1_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(f'& "{hermes_cmd}" $args\n')
        return

    launcher_path = os.path.join(launcher_dir, 'hermes')
    try:
        if os.path.lexists(launcher_path):
            os.remove(launcher_path)
        os.symlink(hermes_cmd, launcher_path)
    except Exception:
        with open(launcher_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('#!/usr/bin/env sh\n')
            f.write('exec "' + hermes_cmd.replace('"', '\\"') + '" "$@"\n')
        os.chmod(launcher_path, 0o755)


def _find_hermes_command_path():
    candidates = [
        _venv_hermes_path(),
        *(_hermes_launcher_paths()),
    ]
    found = shutil.which('hermes')
    if found:
        candidates.append(found)
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return ''


def _install_hermes_package(task_id, python_cmd):
    if task_id:
        update_task(task_id, status='running', message='正在创建 Hermes 虚拟环境', progress=25)
    if not os.path.exists(_venv_python_path()):
        _run_command(python_cmd + ['-m', 'venv', HERMES_VENV_DIR], cwd=HERMES_HOME, timeout=180, task_id=task_id)

    venv_python = _venv_python_path()
    _run_command([venv_python, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'], cwd=HERMES_REPO_DIR, timeout=600, task_id=task_id, step_message='正在升级 pip/setuptools')

    extras = ','.join(HERMES_CROSS_PLATFORM_EXTRAS)
    target = f'.[{extras}]' if extras else '.'
    try:
        _run_command([venv_python, '-m', 'pip', 'install', '-e', target], cwd=HERMES_REPO_DIR, timeout=1800, task_id=task_id, step_message='正在安装 Hermes 依赖')
    except Exception:
        _run_command([venv_python, '-m', 'pip', 'install', '-e', '.'], cwd=HERMES_REPO_DIR, timeout=1800, task_id=task_id, step_message='扩展依赖安装失败，回退到核心安装')


def _try_stop_hermes_gateway():
    hermes_cmd = _venv_hermes_path()
    if not os.path.exists(hermes_cmd):
        return
    try:
        _run_command([hermes_cmd, 'gateway', 'stop'], timeout=30)
    except Exception:
        pass


def _remove_path(path):
    if not path:
        return
    try:
        if os.path.islink(path) or os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def _check_hermes_installed():
    command_path = _find_hermes_command_path()
    local_installed = bool(command_path)
    repo_exists = os.path.isdir(HERMES_REPO_DIR)
    venv_exists = os.path.exists(_venv_python_path())
    installed = bool(local_installed or (repo_exists and venv_exists))
    return {
        'installed': installed,
        'local_installed': bool(local_installed),
        'shell': 'python-native',
        'platform': _platform_label(),
        'config_exists': os.path.exists(HERMES_CONFIG_PATH),
        'repo_exists': repo_exists,
        'venv_exists': venv_exists,
        'command_path': command_path,
    }


def _build_hermes_summary(config):
    model = config.get('model') or {}
    agent = config.get('agent') or {}
    terminal = config.get('terminal') or {}
    browser = config.get('browser') or {}
    display = config.get('display') or {}
    approvals = config.get('approvals') or {}
    toolsets = config.get('toolsets') or []
    custom_providers = config.get('custom_providers') or []

    return {
        'model': {
            'default': model.get('default', ''),
            'provider': model.get('provider', ''),
            'base_url': model.get('base_url', ''),
        },
        'agent': {
            'max_turns': agent.get('max_turns', ''),
            'reasoning_effort': agent.get('reasoning_effort', ''),
            'tool_use_enforcement': agent.get('tool_use_enforcement', ''),
            'verbose': agent.get('verbose', False),
        },
        'terminal': {
            'backend': terminal.get('backend', ''),
            'cwd': terminal.get('cwd', ''),
            'timeout': terminal.get('timeout', ''),
            'persistent_shell': terminal.get('persistent_shell', False),
        },
        'browser': {
            'allow_private_urls': browser.get('allow_private_urls', False),
            'record_sessions': browser.get('record_sessions', False),
        },
        'display': {
            'personality': display.get('personality', ''),
            'streaming': display.get('streaming', False),
            'show_reasoning': display.get('show_reasoning', False),
        },
        'approvals': {
            'mode': approvals.get('mode', ''),
            'timeout': approvals.get('timeout', ''),
        },
        'counts': {
            'toolsets': len(toolsets) if isinstance(toolsets, list) else 0,
            'custom_providers': len(custom_providers) if isinstance(custom_providers, list) else 0,
        },
    }


@hermes_bp.route('/api/hermes/install_state')
def api_hermes_install_state():
    return api_ok(_check_hermes_installed())


@hermes_bp.route('/api/hermes/config', methods=['GET', 'POST'])
def api_hermes_config():
    if request.method == 'GET':
        try:
            config = _load_hermes_config_data()
            text = _read_hermes_config_text()
            return api_ok({
                'configPath': '~/.hermes/config.yaml',
                'absoluteConfigPath': HERMES_CONFIG_PATH,
                'exists': os.path.exists(HERMES_CONFIG_PATH),
                'rawText': text,
                'config': config,
                'summary': _build_hermes_summary(config),
                'installState': _check_hermes_installed(),
            })
        except yaml.YAMLError as e:
            return api_error(f'YAML 解析失败: {e}', status=500)
        except Exception as e:
            return api_error(str(e), status=500)

    payload = request.get_json(silent=True) or {}
    raw_text = payload.get('rawText')
    if raw_text is None:
        return api_error('缺少 rawText', status=400)

    try:
        parsed = _save_hermes_config_text(str(raw_text))
    except yaml.YAMLError as e:
        return api_error(f'YAML 解析失败: {e}', status=400)
    except Exception as e:
        return api_error(str(e), status=500)

    return api_ok({
        'saved': True,
        'configPath': '~/.hermes/config.yaml',
        'absoluteConfigPath': HERMES_CONFIG_PATH,
        'config': parsed,
        'summary': _build_hermes_summary(parsed),
    })


@hermes_bp.route('/api/hermes/models', methods=['GET'])
def api_hermes_models():
    try:
        config = _load_hermes_config_data()
        return api_ok(_get_hermes_models_payload(config))
    except Exception as e:
        return api_error(str(e), status=500)


@hermes_bp.route('/api/hermes/models/save_default', methods=['POST'])
def api_hermes_models_save_default():
    payload = request.get_json(silent=True) or {}
    default_name = str(payload.get('default') or '').strip()
    provider_name = str(payload.get('provider') or '').strip()
    base_url = str(payload.get('base_url') or '').strip()
    api_key = str(payload.get('api_key') or '').strip()
    if not default_name:
        return api_error('缺少默认模型', status=400)
    try:
        config = _load_hermes_config_data()
        model_cfg = _ensure_dict(config.get('model'))
        model_cfg['default'] = default_name
        model_cfg['provider'] = provider_name or 'custom'
        model_cfg['base_url'] = base_url
        if api_key:
            model_cfg['api_key'] = api_key
        elif 'api_key' not in model_cfg:
            model_cfg['api_key'] = ''
        config['model'] = model_cfg
        _save_hermes_config_data(config)
        return api_ok(_get_hermes_models_payload(config))
    except Exception as e:
        return api_error(str(e), status=500)


@hermes_bp.route('/api/hermes/models/set_default', methods=['POST'])
def api_hermes_models_set_default():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get('name') or '').strip()
    if not name:
        return api_error('缺少 provider 名称', status=400)
    try:
        config = _load_hermes_config_data()
        providers = [_normalize_hermes_provider_item(it) for it in _ensure_list(config.get('custom_providers'))]
        target = next((it for it in providers if it['name'] == name), None)
        if not target:
            return api_error('provider 不存在', status=404)
        model_cfg = _ensure_dict(config.get('model'))
        model_cfg['default'] = target['model']
        model_cfg['provider'] = 'custom'
        model_cfg['base_url'] = target['base_url']
        model_cfg['api_key'] = target['api_key']
        config['model'] = model_cfg
        _save_hermes_config_data(config)
        return api_ok(_get_hermes_models_payload(config))
    except Exception as e:
        return api_error(str(e), status=500)


@hermes_bp.route('/api/hermes/models/add', methods=['POST'])
def api_hermes_models_add():
    payload = request.get_json(silent=True) or {}
    item = _normalize_hermes_provider_item(payload)
    if not item['name']:
        return api_error('缺少 provider 名称', status=400)
    if not item['model']:
        return api_error('缺少模型名称', status=400)
    try:
        config = _load_hermes_config_data()
        providers = [_normalize_hermes_provider_item(it) for it in _ensure_list(config.get('custom_providers'))]
        if any(it['name'] == item['name'] for it in providers):
            return api_error('provider 已存在', status=400)
        providers.append(item)
        config['custom_providers'] = providers
        _save_hermes_config_data(config)
        return api_ok(_get_hermes_models_payload(config))
    except Exception as e:
        return api_error(str(e), status=500)


@hermes_bp.route('/api/hermes/models/update', methods=['POST'])
def api_hermes_models_update():
    payload = request.get_json(silent=True) or {}
    original_name = str(payload.get('originalName') or '').strip()
    item = _normalize_hermes_provider_item(payload)
    if not original_name:
        return api_error('缺少原 provider 名称', status=400)
    if not item['name']:
        return api_error('缺少 provider 名称', status=400)
    if not item['model']:
        return api_error('缺少模型名称', status=400)
    try:
        config = _load_hermes_config_data()
        providers = [_normalize_hermes_provider_item(it) for it in _ensure_list(config.get('custom_providers'))]
        original_item = None
        found = False
        for idx, existing in enumerate(providers):
            if existing['name'] != original_name:
                continue
            found = True
            original_item = dict(existing)
            if item['name'] != original_name and any(it['name'] == item['name'] for it in providers):
                return api_error('provider 已存在', status=400)
            providers[idx] = item
            break
        if not found:
            return api_error('provider 不存在', status=404)
        config['custom_providers'] = providers

        model_cfg = _ensure_dict(config.get('model'))
        if original_item and str(model_cfg.get('default') or '').strip() == str(original_item.get('model') or '').strip():
            model_cfg['default'] = item['model']
        if original_item and str(model_cfg.get('base_url') or '').strip() == str(original_item.get('base_url') or '').strip():
            model_cfg['base_url'] = item['base_url']
        if original_item and str(model_cfg.get('api_key') or '').strip() == str(original_item.get('api_key') or '').strip():
            model_cfg['api_key'] = item['api_key']
        config['model'] = model_cfg

        _save_hermes_config_data(config)
        return api_ok(_get_hermes_models_payload(config))
    except Exception as e:
        return api_error(str(e), status=500)


@hermes_bp.route('/api/hermes/models/remove', methods=['POST'])
def api_hermes_models_remove():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get('name') or '').strip()
    if not name:
        return api_error('缺少 provider 名称', status=400)
    try:
        config = _load_hermes_config_data()
        providers = [_normalize_hermes_provider_item(it) for it in _ensure_list(config.get('custom_providers'))]
        target = next((it for it in providers if it['name'] == name), None)
        new_providers = [it for it in providers if it['name'] != name]
        if len(new_providers) == len(providers):
            return api_error('provider 不存在', status=404)
        config['custom_providers'] = new_providers
        model_cfg = _ensure_dict(config.get('model'))
        if target and str(model_cfg.get('default') or '').strip() == str(target.get('model') or '').strip():
            model_cfg['provider'] = ''
        config['model'] = model_cfg
        _save_hermes_config_data(config)
        return api_ok(_get_hermes_models_payload(config))
    except Exception as e:
        return api_error(str(e), status=500)


@hermes_bp.route('/api/hermes/install', methods=['POST'])
def api_hermes_install():
    def _do(task_id):
        update_task(task_id, status='running', message='正在准备 Hermes 安装环境', progress=5)
        _ensure_hermes_repository(task_id=task_id)
        python_item = _select_python_command()
        update_task(task_id, status='running', message='检测到 Python: ' + python_item['label'], progress=15)
        _install_hermes_package(task_id, python_item['cmd'])
        update_task(task_id, status='running', message='正在写入 Hermes 启动入口', progress=92)
        _ensure_hermes_launcher()
        update_task(task_id, status='running', message='正在校验安装结果', progress=90)
        state = _check_hermes_installed()
        if not state.get('installed'):
            raise RuntimeError('安装脚本执行完成，但未检测到 Hermes 可执行命令')
        update_task(task_id, status='running', message='Hermes 安装完成', progress=100)

    task_id = create_task(_do, name='hermes install')
    return api_ok({'taskId': task_id})


@hermes_bp.route('/api/hermes/uninstall', methods=['POST'])
def api_hermes_uninstall():
    def _do(task_id):
        update_task(task_id, status='running', message='正在停止 Hermes 相关进程', progress=10)
        _try_stop_hermes_gateway()
        update_task(task_id, status='running', message='正在移除 Hermes 可执行文件', progress=40)
        for path in _hermes_launcher_paths():
            _remove_path(path)
        update_task(task_id, status='running', message='正在移除 Hermes 仓库目录', progress=70)
        _remove_path(HERMES_REPO_DIR)
        update_task(task_id, status='running', message='Hermes 已卸载，配置目录已保留', progress=100)

    task_id = create_task(_do, name='hermes uninstall')
    return api_ok({'taskId': task_id})
