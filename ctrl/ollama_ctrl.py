import json
import os
import shutil
import subprocess

from flask import Blueprint

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task, update_task


ollama_bp = Blueprint('ollama', __name__)


def _has_ollama():
    return bool(shutil.which('ollama'))


def _run_shell(task_id, cmd: str, timeout=None):
    update_task(task_id, status='running', message=cmd)
    result = subprocess.run(
        ['bash', '-lc', cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or '').strip()
        raise RuntimeError(err or ('command failed: ' + cmd))
    return result.stdout


@ollama_bp.route('/api/ollama/install_state')
def api_ollama_install_state():
    return api_ok({'installed': _has_ollama()})


@ollama_bp.route('/api/ollama/install', methods=['POST'])
def api_ollama_install():
    if os.name == 'nt':
        return api_error('Windows 环境不支持该操作', status=400)

    def _do(task_id):
        if _has_ollama():
            return
        _run_shell(task_id, 'curl -fsSL https://ollama.com/install.sh | sh', timeout=60 * 10)

    task_id = create_task(_do, name='ollama install')
    return api_ok({'taskId': task_id})


@ollama_bp.route('/api/ollama/reinstall', methods=['POST'])
def api_ollama_reinstall():
    if os.name == 'nt':
        return api_error('Windows 环境不支持该操作', status=400)

    def _do(task_id):
        _do_uninstall(task_id)
        _do_install(task_id)

    def _do_install(task_id):
        _run_shell(task_id, 'curl -fsSL https://ollama.com/install.sh | sh', timeout=60 * 10)

    task_id = create_task(_do, name='ollama reinstall')
    return api_ok({'taskId': task_id})


@ollama_bp.route('/api/ollama/uninstall', methods=['POST'])
def api_ollama_uninstall():
    if os.name == 'nt':
        return api_error('Windows 环境不支持该操作', status=400)

    def _do(task_id):
        _do_uninstall(task_id)

    task_id = create_task(_do, name='ollama uninstall')
    return api_ok({'taskId': task_id})


def _do_uninstall(task_id):
    path = shutil.which('ollama')
    cmds = [
        'systemctl stop ollama 2>/dev/null || true',
        'systemctl disable ollama 2>/dev/null || true',
        'systemctl --user stop ollama 2>/dev/null || true',
        'systemctl --user disable ollama 2>/dev/null || true',
    ]
    for cmd in cmds:
        try:
            _run_shell(task_id, cmd, timeout=30)
        except Exception:
            pass

    if path and os.path.isabs(path):
        try:
            os.remove(path)
        except Exception:
            pass

    for p in [
        '/etc/systemd/system/ollama.service',
        '/usr/lib/systemd/system/ollama.service',
        '/usr/local/lib/systemd/system/ollama.service',
        '/usr/local/bin/ollama',
        '/usr/bin/ollama',
    ]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    for d in [
        os.path.expanduser('~/.ollama'),
        '/usr/share/ollama',
        '/var/lib/ollama',
    ]:
        try:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass

    try:
        _run_shell(task_id, 'systemctl daemon-reload 2>/dev/null || true', timeout=15)
    except Exception:
        pass


@ollama_bp.route('/api/ollama/models')
def api_ollama_models():
    try:
        models = []

        try:
            import requests

            r = requests.get('http://localhost:11434/api/tags', timeout=3)
            if r.status_code == 200:
                data = r.json() or {}
                for m in data.get('models', []) or []:
                    models.append({
                        'name': m.get('name', ''),
                        'size': m.get('size', 0),
                        'modified': m.get('modified', ''),
                    })
                return api_ok({'models': models})
        except Exception:
            pass

        if _has_ollama():
            try:
                result = subprocess.run(
                    ['ollama', 'list'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').strip().split('\n'):
                        if not line:
                            continue
                        parts = line.split()
                        if not parts:
                            continue
                        model_name = parts[0]
                        size = parts[1] if len(parts) > 1 else '?'
                        models.append({'name': model_name, 'size': size})
            except Exception:
                pass

        return api_ok({'models': models})
    except Exception as e:
        return api_error(str(e), status=500)
