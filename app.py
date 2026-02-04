import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for
from flask_socketio import SocketIO
import os
import mimetypes
import json
from datetime import datetime
import select
import struct
import subprocess
import shutil

TERMINAL_SUPPORTED = os.name != 'nt'
if TERMINAL_SUPPORTED:
    try:
        import pty
        import fcntl
        import termios
    except Exception:
        TERMINAL_SUPPORTED = False

BOT_PROXY_SUPPORTED = True
try:
    import websocket
except Exception:
    BOT_PROXY_SUPPORTED = False

# ============ 导入拆分后的模块 ============
from system_monitor import (
    list_processes, kill_process, get_process_ports_detail,
    list_system_packages, uninstall_system_package,
    list_pip_packages, install_pip_package, uninstall_pip_package,
    list_npm_packages, install_npm_package, uninstall_npm_package,
    list_docker_images, list_docker_containers,
    remove_docker_image, remove_docker_container,
    stop_docker_container, start_docker_container,
    list_systemd_services, control_systemd_service,
    list_disks, list_network,
    get_all_git_repos_info
)
from core import list_directory, get_file_details, search_files, MARKDOWN_EXTENSIONS, CODE_EXTENSIONS
from utils import get_relative_path, get_breadcrumbs, format_size


# ============ Flask 应用初始化 ============
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins='*')

# ============ 配置 ============
# ROOT_DIR 默认值改为 clawos 的父文件夹（相对路径）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.getenv('ROOT_DIR', os.path.dirname(_SCRIPT_DIR))
CONVERSATION_FILE = os.path.join(_SCRIPT_DIR, 'conversations.json')
TRASH_DIR = os.path.join(ROOT_DIR, '_trash')
AUTH_USERNAME = 'admin'
AUTH_PASSWORD = 'admin'


# ============ 认证中间件 ============
@app.before_request
def require_auth():
    if request.endpoint == 'static':
        return
    if request.path.startswith('/socket.io'):
        return
    auth = request.authorization
    if not auth or not (auth.username == AUTH_USERNAME and auth.password == AUTH_PASSWORD):
        body = (
            '<!doctype html>'
            '<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>需要登录</title></head>'
            '<body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif;padding:24px;">'
            '<h2 style="margin:0 0 12px 0;">需要登录</h2>'
            '<div style="color:#57606a;line-height:1.6;">'
            '此页面启用了 Basic Auth。请在浏览器弹窗中输入账号密码。'
            '</div>'
            '<div style="margin-top:12px;padding:12px;border:1px solid #d0d7de;border-radius:8px;background:#f6f8fa;">'
            '<div>用户名：admin</div><div>密码：admin</div>'
            '</div>'
            '</body></html>'
        )
        return (body, 401, {'WWW-Authenticate': 'Basic realm="Login Required"', 'Content-Type': 'text/html; charset=utf-8'})


# ============ 辅助函数 ============
def load_json(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else {}

def save_json(filepath, data):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving JSON: {e}")


# ============ API 路由 ============

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
    if TERMINAL_SUPPORTED:
        items.insert(1, {'action': 'terminal', 'icon': '🖥️', 'text': '终端'})

    return jsonify({
        'items': items
    })

@app.route('/api/test_socket')
def test_socket():
    return jsonify({'status': 'socket_test_ok', 'message': 'Basic Auth and Socket.IO path working'})

@app.route('/api/stats')
def api_stats():
    conversations = load_json(CONVERSATION_FILE, {'history': [], 'sent_count': 0})
    return jsonify({
        'sent_count': conversations.get('sent_count', 0),
        'conv_count': len(conversations.get('history', [])),
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/history')
def api_history():
    conversations = load_json(CONVERSATION_FILE, {'history': []})
    return jsonify({'history': conversations.get('history', [])})

@app.route('/api/save', methods=['POST'])
def api_save():
    data = request.json
    conversations = load_json(CONVERSATION_FILE, {'history': [], 'sent_count': 0})
    if 'history' not in conversations:
        conversations['history'] = []
    conversations['history'].append({
        'type': data.get('type', 'bot'),
        'text': data.get('text', ''),
        'time': datetime.now().strftime('%H:%M:%S')
    })
    if data.get('type') == 'user':
        conversations['sent_count'] = conversations.get('sent_count', 0) + 1
    save_json(CONVERSATION_FILE, conversations)
    return jsonify({'success': True})

@app.route('/api/clear', methods=['POST'])
def api_clear():
    save_json(CONVERSATION_FILE, {'history': [], 'sent_count': 0})
    return jsonify({'success': True})

@app.route('/api/search')
def api_search():
    return jsonify(search_files(ROOT_DIR, request.args.get('q', '').strip()))

@app.route('/api/file/info')
def api_file_info():
    result = get_file_details(request.args.get('path', '').strip(), ROOT_DIR)
    return jsonify(result)


# ============ 批量操作 API ============

@app.route('/api/batch/delete', methods=['POST'])
def batch_delete():
    data = request.json
    paths = data.get('paths', [])
    if not paths:
        return jsonify({'success': False, 'message': '请选择要删除的文件'})
    
    deleted, errors = [], []
    for path in paths:
        full_path = os.path.join(ROOT_DIR, path)
        full_path = os.path.normpath(full_path)
        if not full_path.startswith(ROOT_DIR):
            errors.append({'path': path, 'error': '非法路径'})
            continue
        if not os.path.exists(full_path):
            errors.append({'path': path, 'error': '文件不存在'})
            continue
        try:
            os.makedirs(TRASH_DIR, exist_ok=True)
            item_name = os.path.basename(full_path)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            trash_name = f"{timestamp}_{item_name}"
            trash_path = os.path.join(TRASH_DIR, trash_name)
            shutil.move(full_path, trash_path)
            deleted.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})
    
    return jsonify({'success': True, 'deleted': deleted, 'errors': errors, 'message': f'已删除 {len(deleted)} 个项目'})

@app.route('/api/batch/copy', methods=['POST'])
def batch_copy():
    data = request.json
    paths, target_path = data.get('paths', []), data.get('target', '').strip()
    if not paths or not target_path:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    target_full = os.path.normpath(os.path.join(ROOT_DIR, target_path))
    if not target_full.startswith(ROOT_DIR) or not os.path.isdir(target_full):
        return jsonify({'success': False, 'message': '目标位置无效'})
    
    copied, errors = [], []
    for path in paths:
        full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
        if not full_path.startswith(ROOT_DIR) or not os.path.exists(full_path):
            errors.append({'path': path, 'error': '无效路径'})
            continue
        try:
            item_name = os.path.basename(full_path)
            new_path = os.path.join(target_full, item_name)
            counter = 1
            while os.path.exists(new_path):
                name, ext = os.path.splitext(item_name)
                new_name = f"{name}_copy_{counter}{ext if not os.path.isdir(full_path) else ''}"
                new_path = os.path.join(target_full, new_name)
                counter += 1
            if os.path.isdir(full_path):
                shutil.copytree(full_path, new_path)
            else:
                shutil.copy2(full_path, new_path)
            copied.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})
    
    return jsonify({'success': True, 'copied': copied, 'errors': errors, 'message': f'已复制 {len(copied)} 个项目'})

@app.route('/api/batch/move', methods=['POST'])
def batch_move():
    data = request.json
    paths, target_path = data.get('paths', []), data.get('target', '').strip()
    if not paths or not target_path:
        return jsonify({'success': False, 'message': '参数不完整'})
    
    target_full = os.path.normpath(os.path.join(ROOT_DIR, target_path))
    if not target_full.startswith(ROOT_DIR) or not os.path.isdir(target_full):
        return jsonify({'success': False, 'message': '目标位置无效'})
    
    moved, errors = [], []
    for path in paths:
        full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
        if not full_path.startswith(ROOT_DIR) or not os.path.exists(full_path):
            errors.append({'path': path, 'error': '无效路径'})
            continue
        try:
            item_name = os.path.basename(full_path)
            new_path = os.path.join(target_full, item_name)
            if os.path.exists(new_path):
                errors.append({'path': path, 'error': f'{item_name} 已存在'})
                continue
            shutil.move(full_path, new_path)
            moved.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})
    
    return jsonify({'success': True, 'moved': moved, 'errors': errors, 'message': f'已移动 {len(moved)} 个项目'})


# ============ 进程管理 API ============

@app.route('/api/process/list')
def api_process_list():
    result = list_processes()
    return jsonify(result)

@app.route('/api/process/kill/<int:pid>', methods=['POST'])
def api_process_kill(pid):
    result = kill_process(pid)
    return jsonify(result)

@app.route('/api/process/ports/<int:pid>')
def api_process_ports(pid):
    result = get_process_ports_detail(pid)
    return jsonify(result)


# ============ 系统包管理 API ============

@app.route('/api/system-packages/list')
def api_system_packages():
    result = list_system_packages()
    return jsonify(result)

@app.route('/api/system-packages/uninstall', methods=['POST'])
def api_system_packages_uninstall():
    data = request.json
    result = uninstall_system_package(data.get('name'), data.get('manager'))
    return jsonify(result)


# ============ Pip 包管理 API ============

@app.route('/api/pip/list')
def api_pip_list():
    result = list_pip_packages()
    return jsonify(result)

@app.route('/api/pip/install', methods=['POST'])
def api_pip_install():
    result = install_pip_package(request.json.get('package'))
    return jsonify(result)

@app.route('/api/pip/uninstall', methods=['POST'])
def api_pip_uninstall():
    result = uninstall_pip_package(request.json.get('package'))
    return jsonify(result)


# ============ NPM 包管理 API ============

@app.route('/api/npm/list')
def api_npm_list():
    result = list_npm_packages()
    return jsonify(result)

@app.route('/api/npm/install', methods=['POST'])
def api_npm_install():
    result = install_npm_package(request.json.get('package'))
    return jsonify(result)

@app.route('/api/npm/uninstall', methods=['POST'])
def api_npm_uninstall():
    result = uninstall_npm_package(request.json.get('package'))
    return jsonify(result)


# ============ Docker 管理 API ============

@app.route('/api/docker/images')
def api_docker_images():
    result = list_docker_images()
    return jsonify(result)

@app.route('/api/docker/containers')
def api_docker_containers():
    result = list_docker_containers()
    return jsonify(result)

@app.route('/api/docker/image/rm', methods=['POST'])
def api_docker_image_rm():
    result = remove_docker_image(request.json.get('id'))
    return jsonify(result)

@app.route('/api/docker/container/rm', methods=['POST'])
def api_docker_container_rm():
    result = remove_docker_container(request.json.get('id'), request.json.get('force', False))
    return jsonify(result)

@app.route('/api/docker/container/stop', methods=['POST'])
def api_docker_container_stop():
    result = stop_docker_container(request.json.get('id'))
    return jsonify(result)

@app.route('/api/docker/container/start', methods=['POST'])
def api_docker_container_start():
    result = start_docker_container(request.json.get('id'))
    return jsonify(result)


# ============ Systemd 服务管理 API ============

@app.route('/api/systemd/list')
def api_systemd_list():
    result = list_systemd_services()
    return jsonify(result)

@app.route('/api/systemd/control', methods=['POST'])
def api_systemd_control():
    data = request.json
    result = control_systemd_service(data.get('service'), data.get('action'))
    return jsonify(result)


# ============ 磁盘管理 API ============

@app.route('/api/disk/list')
def api_disk_list():
    result = list_disks()
    return jsonify(result)


# ============ 网络管理 API ============

@app.route('/api/network/list')
def api_network_list():
    result = list_network()
    return jsonify(result)

@app.route('/api/git/list')
def api_git_list():
    result = get_all_git_repos_info()
    return jsonify({'success': True, 'repos': result})


# ============ 终端 WebSocket ============

user_sessions = {}

@socketio.on('connect', namespace='/term')
def connect():
    pass

@socketio.on('create_terminal', namespace='/term')
def create_terminal(data):
    if not TERMINAL_SUPPORTED:
        socketio.emit(
            'output',
            {'data': '\r\n\x1b[31m*** 当前系统不支持 Web 终端（需要 Linux PTY/termios）***\x1b[0m\r\n'},
            room=request.sid,
            namespace='/term'
        )
        return

    cwd = data.get('cwd', ROOT_DIR)
    if not os.path.abspath(cwd).startswith(os.path.abspath(ROOT_DIR)):
        cwd = ROOT_DIR
    if not os.path.exists(cwd):
        cwd = ROOT_DIR
    
    (master, slave) = pty.openpty()
    p = subprocess.Popen(
        ['/bin/bash'], preexec_fn=os.setsid, stdin=slave, stdout=slave, stderr=slave,
        cwd=cwd, env={**os.environ, "TERM": "xterm-256color"}
    )
    user_sessions[request.sid] = {'fd': master, 'process': p}
    os.close(slave)
    
    def read_terminal_output(fd, sid):
        try:
            while True:
                socketio.sleep(0.01)
                if sid not in user_sessions:
                    break
                r, w, e = select.select([fd], [], [], 0)
                if fd in r:
                    output = os.read(fd, 10240)
                    if not output:
                        break
                    socketio.emit('output', {'data': output.decode('utf-8', 'ignore')}, room=sid, namespace='/term')
        except OSError:
            pass
    socketio.start_background_task(read_terminal_output, master, request.sid)

@socketio.on('input', namespace='/term')
def on_input(data):
    if request.sid in user_sessions:
        os.write(user_sessions[request.sid]['fd'], data['input'].encode())

@socketio.on('resize', namespace='/term')
def on_resize(data):
    if request.sid in user_sessions:
        fd = user_sessions[request.sid]['fd']
        winsize = struct.pack("HHHH", data['rows'], data['cols'], 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

@socketio.on('disconnect', namespace='/term')
def disconnect():
    if request.sid in user_sessions:
        session = user_sessions[request.sid]
        try:
            os.close(session['fd'])
            session['process'].terminate()
        except:
            pass
        del user_sessions[request.sid]


# ============ Bot WebSocket Proxy ============

bot_gateway_clients = {}

def on_ws_message(ws, message):
    sid = getattr(ws, 'sid', None)
    if sid:
        try:
            socketio.server.emit('bot_to_proxy', message, room=sid, namespace='/')
        except Exception as e:
            print(f'Emit error: {e}')

def on_ws_error(ws, error):
    print(f'WebSocket error: {error}')

def on_ws_close(ws, close_status_code, close_msg):
    sid = getattr(ws, 'sid', None)
    if sid and sid in bot_gateway_clients:
        del bot_gateway_clients[sid]

def create_bot_connection(sid):
    if not BOT_PROXY_SUPPORTED:
        return None
    if sid in bot_gateway_clients:
        return bot_gateway_clients[sid]
    ws = websocket.WebSocketApp(
        'ws://127.0.0.1:18789',
        on_message=on_ws_message,
        on_error=on_ws_error,
        on_close=on_ws_close
    )
    ws.sid = sid
    bot_gateway_clients[sid] = ws
    def run_ws():
        ws.run_forever()
    eventlet.spawn(run_ws)
    return ws

@socketio.on('proxy_to_bot')
def bot_forward_message(data):
    if not BOT_PROXY_SUPPORTED:
        return
    sid = request.sid
    try:
        ws = create_bot_connection(sid)
        if ws is None:
            return
        if ws.sock and ws.sock.connected:
            ws.send(data)
        else:
            if sid in bot_gateway_clients:
                del bot_gateway_clients[sid]
            ws = create_bot_connection(sid)
    except Exception as e:
        if sid in bot_gateway_clients:
            del bot_gateway_clients[sid]

@socketio.on('disconnect')
def bot_disconnect():
    sid = request.sid
    if sid in bot_gateway_clients:
        try:
            bot_gateway_clients[sid].close()
        except:
            pass
        del bot_gateway_clients[sid]


# ============ 文件浏览器路由 ============

@app.template_global()
def get_relative_path(path):
    """获取相对于ROOT_DIR的路径（模板全局函数）"""
    from utils import get_relative_path as _get_rel
    return _get_rel(path, ROOT_DIR)

@app.template_filter('starts_with_port')
def starts_with_port_filter(name):
    import re
    return bool(re.match(r'^[0-9]{4}_', name))

@app.template_filter('extract_port')
def extract_port_filter(name):
    import re
    match = re.match(r'^([0-9]{4})_', name)
    return match.group(1) if match else ''

@app.template_filter('dirname')
def dirname_filter(path):
    return os.path.dirname(path)

@app.route('/')
@app.route('/browse/')
@app.route('/browse/<path:path>')
def browse(path=''):
    current_dir = ROOT_DIR if path == '.' or path == '' else os.path.join(ROOT_DIR, path)
    current_dir = os.path.normpath(current_dir)
    if not current_dir.startswith(ROOT_DIR):
        current_dir = ROOT_DIR
    if not os.path.exists(current_dir) or not os.path.isdir(current_dir):
        return "目录不存在", 404
    
    items = list_directory(current_dir)
    breadcrumbs = get_breadcrumbs(current_dir, ROOT_DIR)
    
    return render_template('index.html',
        items=items, current_dir=current_dir, breadcrumbs=breadcrumbs,
        message=request.args.get('message'), msg_type=request.args.get('msg_type', 'success'),
        ROOT_DIR=ROOT_DIR, os=os
    )

@app.route('/view/<path:path>')
def view_file(path):
    from core import IMAGE_EXTENSIONS, MARKDOWN_EXTENSIONS, CODE_EXTENSIONS
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return "非法路径", 403
    if not os.path.exists(full_path):
        return "文件不存在", 404
    if os.path.isdir(full_path):
        return redirect(url_for('browse', path=path))
    
    mime_type, _ = mimetypes.guess_type(full_path)
    _, ext = os.path.splitext(full_path)
    
    # Chrome 原生支持的格式 → 新窗口打开
    chrome_native = [
        '.pdf', '.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv',
        '.mp3', '.wav', '.flac', '.aac', '.m4a',
        '.svg', '.ico', '.webp', '.avif'
    ]
    
    if ext.lower() in chrome_native:
        return redirect(url_for('serve_file', path=path))
    
    # 图片 → 预览
    elif mime_type and (mime_type.startswith('image') or ext.lower() in IMAGE_EXTENSIONS):
        return render_template('image_viewer.html', filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path))
    
    # Excel → SheetJS 预览
    elif ext.lower() in ['.xlsx', '.xls']:
        return render_template('excel_viewer.html', filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path))
    
    # Word → Mammoth 预览
    elif ext.lower() in ['.docx', '.doc']:
        return render_template('word_viewer.html', filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path))
    
    # 文本文件 → CodeMirror 查看器
    elif mime_type and mime_type.startswith('text'):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return render_template("code_mirror.html", content=content, filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path), extension=ext.lower())
        except UnicodeDecodeError:
            try:
                with open(full_path, 'r', encoding='gbk') as f:
                    content = f.read()
                return render_template("code_mirror.html", content=content, filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path), extension=ext.lower())
            except:
                return redirect(url_for('download_file', path=path))
    
    # 其他 → 下载
    return redirect(url_for('download_file', path=path))

@app.route('/edit/<path:path>')
def edit_file(path):
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return "非法路径", 403
    if not os.path.exists(full_path):
        return "文件不存在", 404
    if os.path.isdir(full_path):
        return redirect(url_for('browse', path=path))
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(full_path, 'r', encoding='gbk') as f:
                content = f.read()
        except:
            return "无法读取文件内容", 400
    
    _, ext = os.path.splitext(full_path)
    if ext.lower() in MARKDOWN_EXTENSIONS:
        return render_template("markdown_editor.html", content=content, filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path))
    return render_template("code_editor.html", content=content, filename=os.path.basename(full_path), file_path=path, current_dir=os.path.dirname(path), extension=ext.lower() if ext.lower() in CODE_EXTENSIONS else '.txt')

@app.route('/save_file/<path:path>', methods=['POST'])
def save_file(path):
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(request.get_json().get('content', ''))
        return jsonify({'success': True, 'message': '文件保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<path:path>')
def download_file(path):
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return "非法路径", 403
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return "文件不存在", 404
    return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path), as_attachment=True)

@app.route('/serve/<path:path>')
def serve_file(path):
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return "非法路径", 403
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return "文件不存在", 404
    mime_types = {'.html': 'text/html', '.htm': 'text/html', '.css': 'text/css', '.js': 'application/javascript', '.json': 'application/json', '.xml': 'application/xml', '.txt': 'text/plain', '.md': 'text/markdown', '.py': 'text/x-python', '.sh': 'application/x-sh', '.yaml': 'application/yaml', '.yml': 'application/yaml', '.csv': 'text/csv', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.webp': 'image/webp'}
    ext = os.path.splitext(path)[1].lower()
    return send_from_directory(os.path.dirname(full_path), os.path.basename(full_path), mimetype=mime_types.get(ext, None))

@app.route('/thumbnail/<path:path>')
def thumbnail(path):
    return serve_file(path)

@app.route('/upload/', methods=['POST'])
@app.route('/upload/<path:path>', methods=['POST'])
def upload_file(path=''):
    if 'file' not in request.files:
        return redirect(url_for('browse', path=path, message='没有选择文件', msg_type='error'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('browse', path=path, message='没有选择文件', msg_type='error'))
    upload_dir = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not upload_dir.startswith(ROOT_DIR):
        upload_dir = ROOT_DIR
    if file:
        filename = file.filename
        filepath = os.path.join(upload_dir, filename)
        counter = 1
        name, ext = os.path.splitext(filename)
        while os.path.exists(filepath):
            filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(upload_dir, filename)
            counter += 1
        file.save(filepath)
        return redirect(url_for('browse', path=path, message='文件上传成功', msg_type='success'))

@app.route('/delete/<path:path>', methods=['DELETE'])
def delete_item(path):
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    if full_path == TRASH_DIR:
        return jsonify({'success': False, 'message': '不能删除回收站文件夹'})
    try:
        os.makedirs(TRASH_DIR, exist_ok=True)
        item_name = os.path.basename(full_path)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        trash_name = f"{timestamp}_{item_name}"
        trash_path = os.path.join(TRASH_DIR, trash_name)
        counter = 1
        while os.path.exists(trash_path):
            trash_name = f"{timestamp}_{item_name}_{counter}"
            trash_path = os.path.join(TRASH_DIR, trash_name)
            counter += 1
        shutil.move(full_path, trash_path)
        return jsonify({'success': True, 'message': '已移到回收站'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/rename/<path:path>', methods=['POST'])
def rename_item(path):
    new_name = request.json.get('new_name', '').strip()
    if not new_name:
        return jsonify({'success': False, 'message': '请输入新名称'})
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        new_path = os.path.normpath(os.path.join(os.path.dirname(full_path), new_name))
        if not new_path.startswith(ROOT_DIR):
            return jsonify({'success': False, 'message': '非法路径'})
        os.rename(full_path, new_path)
        return jsonify({'success': True, 'message': '重命名成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/move/<path:path>', methods=['POST'])
def move_item(path):
    target_path = request.json.get('target_path', '').strip()
    if not target_path:
        return jsonify({'success': False, 'message': '请输入目标路径'})
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        target_full = os.path.normpath(os.path.join(ROOT_DIR, target_path))
        if not target_full.startswith(ROOT_DIR):
            return jsonify({'success': False, 'message': '非法路径'})
        os.makedirs(target_full, exist_ok=True)
        item_name = os.path.basename(full_path)
        new_location = os.path.join(target_full, item_name)
        if os.path.exists(new_location):
            return jsonify({'success': False, 'message': '目标位置已存在同名文件'})
        shutil.move(full_path, new_location)
        return jsonify({'success': True, 'message': '移动成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/clone/<path:path>', methods=['POST'])
def clone_item(path):
    full_path = os.path.normpath(os.path.join(ROOT_DIR, path))
    if not full_path.startswith(ROOT_DIR):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        item_name = os.path.basename(full_path)
        if os.path.isdir(full_path):
            clone_name = f"{item_name}_clone"
            clone_path = os.path.join(os.path.dirname(full_path), clone_name)
            counter = 1
            while os.path.exists(clone_path):
                clone_name = f"{item_name}_clone_{counter}"
                clone_path = os.path.join(os.path.dirname(full_path), clone_name)
                counter += 1
            shutil.copytree(full_path, clone_path)
        else:
            name, ext = os.path.splitext(item_name)
            clone_name = f"{name}_clone{ext}"
            clone_path = os.path.join(os.path.dirname(full_path), clone_name)
            counter = 1
            while os.path.exists(clone_path):
                clone_name = f"{name}_clone_{counter}{ext}"
                clone_path = os.path.join(os.path.dirname(full_path), clone_name)
                counter += 1
            shutil.copy2(full_path, clone_path)
        return jsonify({'success': True, 'message': f'克隆到 {clone_name}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/trash')
def trash():
    os.makedirs(TRASH_DIR, exist_ok=True)
    items = []
    for name in os.listdir(TRASH_DIR):
        if name.startswith('.'): continue
        path = os.path.join(TRASH_DIR, name)
        stat = os.stat(path)
        parts = name.split('_', 2)
        deleted_at = parts[0] if len(parts) >= 2 else '未知'
        try:
            dt = datetime.strptime(deleted_at, '%Y%m%d%H%M%S')
            deleted_at = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
        items.append({'name': name, 'path': path, 'deleted_at': deleted_at, 'is_dir': os.path.isdir(path)})
    items.sort(key=lambda x: x['name'], reverse=True)
    return render_template("trash.html", items=items)

@app.route('/trash/clear', methods=['POST'])
def trash_clear():
    """清空回收站"""
    os.makedirs(TRASH_DIR, exist_ok=True)
    try:
        for name in os.listdir(TRASH_DIR):
            if name.startswith('.'): continue
            path = os.path.join(TRASH_DIR, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        return jsonify({'success': True, 'message': '回收站已清空'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=6002, debug=False, use_reloader=False)
