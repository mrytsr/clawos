import json
import os
import subprocess

from flask import Blueprint, jsonify, request, render_template

from ctrl import api_error, api_ok


nanobot_bp = Blueprint('nanobot', __name__)

CONFIG_PATH = os.path.expanduser('~/.nanobot/config.json')


@nanobot_bp.route('/nanobot/config')
def nanobot_config_page():
    return render_template('nanobot_config.html')


def _read_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _write_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


@nanobot_bp.route('/api/nanobot/config')
def api_nanobot_config():
    cfg = _read_config()
    return api_ok(cfg)


@nanobot_bp.route('/api/nanobot/config', methods=['POST'])
def api_nanobot_config_post():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    
    _write_config(data)
    return api_ok({'message': '配置已保存'})


@nanobot_bp.route('/api/nanobot/restart', methods=['POST'])
def api_nanobot_restart():
    try:
        subprocess.run(['systemctl', '--user', 'restart', 'nanobot'], capture_output=True, timeout=10)
        return api_ok({'message': '服务重启中'})
    except Exception as e:
        return api_error(f'重启失败: {str(e)}', status=500)


@nanobot_bp.route('/api/nanobot/status')
def api_nanobot_status():
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'is-active', 'nanobot'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return api_ok({
            'running': result.returncode == 0,
            'status': result.stdout.strip()
        })
    except Exception as e:
        return api_ok({'running': False, 'error': str(e)})
