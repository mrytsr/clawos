import os
import shutil
import subprocess

import yaml
from flask import Blueprint, redirect, render_template, request

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task, update_task


hermes_bp = Blueprint('hermes', __name__)

HERMES_CONFIG_PATH = os.path.expanduser('~/.hermes/config.yaml')
HERMES_HOME = os.path.dirname(HERMES_CONFIG_PATH)
HERMES_REPO_DIR = os.path.join(HERMES_HOME, 'hermes-agent')
HERMES_INSTALL_SCRIPT = 'https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh'


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


def _get_shell_runner():
    if os.name != 'nt':
        bash = shutil.which('bash') or '/bin/bash'
        return {'label': 'bash', 'prefix': [bash, '-lc']}

    bash = shutil.which('bash') or shutil.which('bash.exe')
    if bash:
        return {'label': 'git-bash', 'prefix': [bash, '-lc']}

    wsl = shutil.which('wsl') or shutil.which('wsl.exe')
    if wsl:
        return {'label': 'wsl', 'prefix': [wsl, 'bash', '-lc']}

    return None


def _run_shell_script(script, task_id=None, step_message=None):
    runner = _get_shell_runner()
    if not runner:
        raise RuntimeError('未找到可用的 bash/WSL 环境，无法执行 Hermes 安装脚本')
    if task_id and step_message:
        update_task(task_id, status='running', message=step_message)
    result = subprocess.run(
        runner['prefix'] + [script],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or '').strip() or '命令执行失败'
        raise RuntimeError(msg[:1000])
    return result


def _check_hermes_installed():
    runner = _get_shell_runner()
    local_cmd = shutil.which('hermes')
    local_installed = bool(local_cmd) or os.path.exists(os.path.join(os.path.expanduser('~'), '.local', 'bin', 'hermes')) or os.path.isdir(HERMES_REPO_DIR)
    wsl_installed = False

    if runner:
        try:
            result = subprocess.run(
                runner['prefix'] + ['command -v hermes >/dev/null 2>&1 && echo installed || true'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10,
            )
            wsl_installed = 'installed' in (result.stdout or '')
        except Exception:
            wsl_installed = False

    installed = bool(local_installed or wsl_installed)
    return {
        'installed': installed,
        'local_installed': bool(local_installed),
        'shell': runner['label'] if runner else '',
        'config_exists': os.path.exists(HERMES_CONFIG_PATH),
        'repo_exists': os.path.isdir(HERMES_REPO_DIR),
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
        'summary': _build_hermes_summary(parsed),
    })


@hermes_bp.route('/api/hermes/install', methods=['POST'])
def api_hermes_install():
    def _do(task_id):
        update_task(task_id, status='running', message='正在准备 Hermes 安装环境', progress=5)
        _run_shell_script(
            f'curl -fsSL {HERMES_INSTALL_SCRIPT} | bash',
            task_id=task_id,
            step_message='正在执行官方安装脚本',
        )
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
        _run_shell_script('hermes gateway stop >/dev/null 2>&1 || true', task_id=task_id)
        update_task(task_id, status='running', message='正在移除 Hermes 可执行文件', progress=40)
        _run_shell_script('rm -f ~/.local/bin/hermes', task_id=task_id)
        update_task(task_id, status='running', message='正在移除 Hermes 仓库目录', progress=70)
        _run_shell_script('rm -rf ~/.hermes/hermes-agent', task_id=task_id)
        update_task(task_id, status='running', message='Hermes 已卸载，配置目录已保留', progress=100)

    task_id = create_task(_do, name='hermes uninstall')
    return api_ok({'taskId': task_id})
