import os
import shutil
from datetime import datetime

from flask import request

import config
from ctrl import api_error, api_ok

from lib import file_utils, json_utils


def register_api(app):
    root_dir = config.ROOT_DIR
    conversation_file = config.CONVERSATION_FILE
    trash_dir = config.TRASH_DIR
    terminal_supported = os.name != 'nt'

    @app.route('/api/menu')
    def api_menu():
        items = [
            {'action': 'bot', 'icon': '🤖', 'text': 'claw对话'},
            {'action': 'config', 'icon': '⚙️', 'text': '配置'},
            {'action': 'git', 'icon': '🔀', 'text': 'Git管理'},
            {'action': 'process', 'icon': '📊', 'text': '进程管理'},
            {'action': 'system-package', 'icon': '📦', 'text': '系统包管理'},
            {'action': 'pip', 'icon': '🐍', 'text': 'pip包管理'},
            {'action': 'npm', 'icon': '📦', 'text': 'npm包管理'},
            {'action': 'docker', 'icon': '🐳', 'text': 'docker管理'},
            {'action': 'systemd', 'icon': '🔧', 'text': 'systemd管理'},
            {'action': 'disk', 'icon': '💾', 'text': '磁盘管理'},
            {'action': 'network', 'icon': '🌐', 'text': '网络管理'},
        ]
        if terminal_supported:
            items.insert(1, {'action': 'terminal', 'icon': '🖥️', 'text': '终端'})

        return api_ok({'items': items})

    @app.route('/api/test_socket')
    def test_socket():
        return api_ok({'status': 'socket_test_ok', 'message': 'Basic Auth and Socket.IO path working'})

    @app.route('/api/stats')
    def api_stats():
        conversations = json_utils.load_json(conversation_file, {'history': [], 'sent_count': 0})
        return api_ok({
            'sent_count': conversations.get('sent_count', 0),
            'conv_count': len(conversations.get('history', [])),
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    @app.route('/api/history')
    def api_history():
        conversations = json_utils.load_json(conversation_file, {'history': []})
        return api_ok({'history': conversations.get('history', [])})

    @app.route('/api/save', methods=['POST'])
    def api_save():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        conversations = json_utils.load_json(conversation_file, {'history': [], 'sent_count': 0})
        if 'history' not in conversations:
            conversations['history'] = []
        conversations['history'].append({
            'type': data.get('type', 'bot'),
            'text': data.get('text', ''),
            'time': datetime.now().strftime('%H:%M:%S')
        })
        if data.get('type') == 'user':
            conversations['sent_count'] = conversations.get('sent_count', 0) + 1
        json_utils.save_json(conversation_file, conversations)
        return api_ok()

    @app.route('/api/clear', methods=['POST'])
    def api_clear():
        json_utils.save_json(conversation_file, {'history': [], 'sent_count': 0})
        return api_ok()

    @app.route('/api/search')
    def api_search():
        result = file_utils.search_files(root_dir, request.args.get('q', '').strip())
        if isinstance(result, dict) and result.get('error'):
            return api_error(result.get('error'), status=500)
        return api_ok(result)

    @app.route('/api/trash/list')
    def api_trash_list():
        os.makedirs(trash_dir, exist_ok=True)
        items = []
        for name in os.listdir(trash_dir):
            if name.startswith('.'):
                continue
            full_path = os.path.join(trash_dir, name)
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

    @app.route('/api/trash/clear', methods=['POST'])
    def api_trash_clear():
        os.makedirs(trash_dir, exist_ok=True)
        try:
            for name in os.listdir(trash_dir):
                if name.startswith('.'):
                    continue
                full_path = os.path.join(trash_dir, name)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
            return api_ok()
        except Exception as e:
            return api_error(str(e), status=500)

    @app.route('/api/trash/restore/<name>', methods=['POST'])
    def api_trash_restore(name):
        os.makedirs(trash_dir, exist_ok=True)
        if not name or '/' in name or '\\' in name:
            return api_error('Invalid trash item name', status=400)
        trash_item = os.path.normpath(os.path.join(trash_dir, name))
        if not trash_item.startswith(os.path.normpath(trash_dir)):
            return api_error('Invalid trash item path', status=400)
        if not os.path.exists(trash_item):
            return api_error('Not Found', status=404)

        payload = request.json if isinstance(request.json, dict) else {}
        target_path = (payload.get('target_path') or '').strip()
        if not target_path:
            return api_error('target_path is required', status=400)

        target_full = os.path.normpath(os.path.join(root_dir, target_path))
        if not target_full.startswith(os.path.normpath(root_dir)):
            return api_error('Invalid target path', status=403)
        if os.path.exists(target_full):
            return api_error('Target already exists', status=409)

        try:
            os.makedirs(os.path.dirname(target_full), exist_ok=True)
            shutil.move(trash_item, target_full)
            return api_ok()
        except Exception as e:
            return api_error(str(e), status=500)

    @app.route('/api/file/info')
    def api_file_info():
        result = file_utils.get_file_details(request.args.get('path', '').strip(), root_dir)
        if not result.get('success'):
            message = result.get('message') or 'Bad Request'
            status = 400
            if message == '无效路径':
                status = 403
            elif message == '文件不存在':
                status = 404
            return api_error(message, status=status)
        return api_ok(result.get('info'))
