"""Flask API routes for ClawOS."""

import os
import shutil
from datetime import datetime

from flask import Blueprint, current_app, request

import config
from ctrl import api_error, api_ok

from lib import file_utils, json_utils


class _ApiContext:
    """Resolved config values used by API handlers."""

    def __init__(
        self,
        root_dir,
        conversation_file,
        trash_dir,
        terminal_supported,
    ):
        self.root_dir = root_dir
        self.conversation_file = conversation_file
        self.trash_dir = trash_dir
        self.terminal_supported = terminal_supported


def _get_ctx():
    try:
        stored = current_app.extensions.get('api_ctx')
    except RuntimeError:
        stored = None
    if stored is not None:
        return stored
    return _ApiContext(
        root_dir=config.ROOT_DIR,
        conversation_file=config.CONVERSATION_FILE,
        trash_dir=config.TRASH_DIR,
        terminal_supported=True,
    )


def _api_menu(ctx):
    """Return top menu entries."""

    items = [
        {'action': 'bot', 'icon': '🤖', 'text': 'claw对话'},
        {'action': 'config', 'icon': '⚙️', 'text': '配置'},
        {'action': 'git', 'icon': '🔀', 'text': 'Git管理'},
        {'action': 'process', 'icon': '📊', 'text': '进程管理'},
        {'action': 'gpu', 'icon': '🖥️', 'text': '显卡'},
        {'action': 'ollama', 'icon': '🦙', 'text': 'Ollama'},
        {'action': 'openclaw', 'icon': '⚙️', 'text': 'OpenClaw'},
        {'action': 'system-package', 'icon': '📦', 'text': '系统包管理'},
        {'action': 'pip', 'icon': '🐍', 'text': 'pip包管理'},
        {'action': 'npm', 'icon': '📦', 'text': 'npm包管理'},
        {'action': 'docker', 'icon': '🐳', 'text': 'docker管理'},
        {'action': 'systemd', 'icon': '🔧', 'text': 'systemd管理'},
        {'action': 'disk', 'icon': '💾', 'text': '磁盘管理'},
        {'action': 'network', 'icon': '🌐', 'text': '网络管理'},
    ]

    if ctx.terminal_supported:
        items.insert(1, {'action': 'terminal', 'icon': '🖥️', 'text': '终端'})

    return api_ok({'items': items})


def _api_test_socket(_ctx):
    """Connectivity test endpoint."""

    return api_ok({
        'status': 'socket_test_ok',
        'message': 'Basic Auth and Socket.IO path working',
    })


def _api_stats(ctx):
    """Return conversation counters and server time."""

    conversations = json_utils.load_json(
        ctx.conversation_file,
        {'history': [], 'sent_count': 0},
    )
    return api_ok({
        'sent_count': conversations.get('sent_count', 0),
        'conv_count': len(conversations.get('history', [])),
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })


def _api_history(ctx):
    """Return conversation history."""

    conversations = json_utils.load_json(
        ctx.conversation_file,
        {'history': []},
    )
    return api_ok({'history': conversations.get('history', [])})


def _api_save(ctx):
    """Append a message to conversation history."""

    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)

    conversations = json_utils.load_json(
        ctx.conversation_file,
        {'history': [], 'sent_count': 0},
    )
    conversations.setdefault('history', [])
    conversations['history'].append({
        'type': data.get('type', 'bot'),
        'text': data.get('text', ''),
        'time': datetime.now().strftime('%H:%M:%S'),
    })
    if data.get('type') == 'user':
        conversations['sent_count'] = conversations.get('sent_count', 0) + 1
    json_utils.save_json(ctx.conversation_file, conversations)
    return api_ok()


def _api_clear(ctx):
    """Clear conversation history."""

    json_utils.save_json(
        ctx.conversation_file,
        {'history': [], 'sent_count': 0},
    )
    return api_ok()


def _api_search(ctx):
    """Search files under root directory."""

    query = request.args.get('q', '').strip()
    result = file_utils.search_files(ctx.root_dir, query)
    if isinstance(result, dict) and result.get('error'):
        return api_error(result.get('error'), status=500)
    return api_ok(result)


def _api_trash_list(ctx):
    """List items in trash directory."""

    os.makedirs(ctx.trash_dir, exist_ok=True)
    items = []
    for name in os.listdir(ctx.trash_dir):
        if name.startswith('.'):
            continue
        full_path = os.path.join(ctx.trash_dir, name)
        parts = name.split('_', 2)
        deleted_at = parts[0] if len(parts) >= 2 else '未知'
        try:
            dt = datetime.strptime(deleted_at, '%Y%m%d%H%M%S')
            deleted_at = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass

        display_name = name
        if len(name) > 15 and name[14] == '_':
            display_name = name[15:]

        items.append({
            'name': name,
            'display_name': display_name,
            'deleted_at': deleted_at,
            'is_dir': os.path.isdir(full_path),
        })

    items.sort(key=lambda x: x['name'], reverse=True)
    return api_ok({'items': items, 'count': len(items)})


def _api_trash_clear(ctx):
    """Remove all trash items."""

    os.makedirs(ctx.trash_dir, exist_ok=True)
    try:
        for name in os.listdir(ctx.trash_dir):
            if name.startswith('.'):
                continue
            full_path = os.path.join(ctx.trash_dir, name)
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
        return api_ok()
    except Exception as e:
        return api_error(str(e), status=500)


def _api_trash_restore(ctx, name):
    """Restore a trash item into a target path under root."""

    os.makedirs(ctx.trash_dir, exist_ok=True)
    if not name or '/' in name or '\\' in name:
        return api_error('Invalid trash item name', status=400)

    trash_item = os.path.normpath(os.path.join(ctx.trash_dir, name))
    if not trash_item.startswith(os.path.normpath(ctx.trash_dir)):
        return api_error('Invalid trash item path', status=400)

    if not os.path.exists(trash_item):
        return api_error('Not Found', status=404)

    payload = request.json if isinstance(request.json, dict) else {}
    target_path = (payload.get('target_path') or '').strip()
    if not target_path:
        return api_error('target_path is required', status=400)

    target_full = os.path.normpath(os.path.join(ctx.root_dir, target_path))
    if not target_full.startswith(os.path.normpath(ctx.root_dir)):
        return api_error('Invalid target path', status=403)
    if os.path.exists(target_full):
        return api_error('Target already exists', status=409)

    try:
        os.makedirs(os.path.dirname(target_full), exist_ok=True)
        shutil.move(trash_item, target_full)
        return api_ok()
    except Exception as e:
        return api_error(str(e), status=500)


def _api_file_info(ctx):
    """Return file details for a path."""

    path = request.args.get('path', '').strip()
    result = file_utils.get_file_details(path, ctx.root_dir)
    if result.get('success'):
        return api_ok(result.get('info'))

    message = result.get('message') or 'Bad Request'
    status = {'无效路径': 403, '文件不存在': 404}.get(message, 400)
    return api_error(message, status=status)

def _api_bot_token(_ctx):
    cfg_path = os.path.expanduser('~/.openclaw/openclaw.json')
    payload = json_utils.load_json(cfg_path, {})
    token = ''
    if isinstance(payload, dict):
        gateway = payload.get('gateway')
        if isinstance(gateway, dict):
            auth = gateway.get('auth')
            if isinstance(auth, dict):
                tok = auth.get('token')
                if isinstance(tok, str):
                    token = tok
    return api_ok({'token': token})


api_bp = Blueprint('api', __name__)


@api_bp.route('/api/menu')
def api_menu():
    return _api_menu(_get_ctx())


@api_bp.route('/api/test_socket')
def test_socket():
    return _api_test_socket(_get_ctx())


@api_bp.route('/api/stats')
def api_stats():
    return _api_stats(_get_ctx())


@api_bp.route('/api/history')
def api_history():
    return _api_history(_get_ctx())


@api_bp.route('/api/save', methods=['POST'])
def api_save():
    return _api_save(_get_ctx())


@api_bp.route('/api/clear', methods=['POST'])
def api_clear():
    return _api_clear(_get_ctx())


@api_bp.route('/api/search')
def api_search():
    return _api_search(_get_ctx())


@api_bp.route('/api/trash/list')
def api_trash_list():
    return _api_trash_list(_get_ctx())


@api_bp.route('/api/trash/clear', methods=['POST'])
def api_trash_clear():
    return _api_trash_clear(_get_ctx())


@api_bp.route('/api/trash/restore/<name>', methods=['POST'])
def api_trash_restore(name):
    return _api_trash_restore(_get_ctx(), name)


@api_bp.route('/api/file/info')
def api_file_info():
    return _api_file_info(_get_ctx())


@api_bp.route('/api/bot/token')
def api_bot_token():
    return _api_bot_token(_get_ctx())
