import os
import json
import importlib
import re
import select
import shutil
import struct
import subprocess

from flask import Flask, jsonify, request
from flask import Response
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException

import config
from lib import path_utils

from ctrl.api_ctrl import api_bp
from ctrl.api_ctrl import _ApiContext
from ctrl.auth_ctrl import auth_bp
from ctrl.batch_ctrl import batch_bp
from ctrl.file_ctrl import file_bp
from ctrl.system_ctrl import system_bp
from ctrl.task_ctrl import task_bp

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading' if os.name == 'nt' else None,
)

_template_root_dir = config.ROOT_DIR


@app.template_global()
def get_relative_path(path):
    return path_utils.get_relative_path(path, _template_root_dir)


@app.template_filter('starts_with_port')
def starts_with_port_filter(name):
    return bool(re.match(r'^[0-9]{4}_', name))


@app.template_filter('extract_port')
def extract_port_filter(name):
    match = re.match(r'^([0-9]{4})_', name)
    return match.group(1) if match else ''


@app.template_filter('dirname')
def dirname_filter(path):
    return os.path.dirname(path)


@app.template_global()
def server_is_windows():
    return os.name == 'nt'


app.extensions['api_ctx'] = _ApiContext(
    root_dir=config.ROOT_DIR,
    conversation_file=config.CONVERSATION_FILE,
    trash_dir=config.TRASH_DIR,
    terminal_supported=True,
)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(batch_bp)
app.register_blueprint(system_bp)
app.register_blueprint(task_bp)
app.register_blueprint(file_bp)

_terminal_root_dir = config.ROOT_DIR
_terminal_supported = True
_terminal_sessions = {}
TERMINAL_PREEXEC_FN = getattr(os, 'setsid', None)
fcntl = None
pty = None
termios = None
_node_bin = shutil.which('node') if os.name == 'nt' else None
_node_bridge = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'win_pty_bridge.js')

if os.name != 'nt' and _terminal_supported:
    try:
        fcntl = importlib.import_module('fcntl')
        pty = importlib.import_module('pty')
        termios = importlib.import_module('termios')
    except Exception:
        _terminal_supported = False
        fcntl = None
        pty = None
        termios = None


@socketio.on('connect', namespace='/term')
def term_connect():
    return


@socketio.on('create_terminal', namespace='/term')
def term_create_terminal(data):
    if os.name == 'nt':
        if not _node_bin or not os.path.exists(_node_bridge):
            message = (
                '\r\n\x1b[31m*** 当前系统未启用 Web 终端（Windows 需要 Node.js + node-pty）***\x1b[0m\r\n'
            )
            socketio.emit('output', {'data': message}, room=request.sid, namespace='/term')
            return

        cwd = (data or {}).get('cwd', _terminal_root_dir)
        if not os.path.abspath(cwd).startswith(os.path.abspath(_terminal_root_dir)):
            cwd = _terminal_root_dir
        if not os.path.exists(cwd):
            cwd = _terminal_root_dir

        process = subprocess.Popen(
            [_node_bin, _node_bridge],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            env=os.environ.copy(),
        )
        _terminal_sessions[request.sid] = {'kind': 'nodepty', 'process': process}

        try:
            init = {
                'type': 'init',
                'cwd': cwd,
                'cols': 80,
                'rows': 24,
                'shell': 'powershell.exe',
                'args': ['-NoLogo'],
            }
            process.stdin.write(json.dumps(init, ensure_ascii=False) + '\n')
            process.stdin.flush()
        except Exception:
            pass

        def _read_nodepty_output(proc, sid):
            try:
                while True:
                    socketio.sleep(0.01)
                    if sid not in _terminal_sessions:
                        break
                    if proc.poll() is not None:
                        break
                    line = proc.stdout.readline()
                    if not line:
                        break
                    raw = line.rstrip('\n')
                    try:
                        msg = json.loads(raw)
                        if isinstance(msg, dict) and msg.get('type') == 'output':
                            socketio.emit('output', {'data': msg.get('data', '')}, room=sid, namespace='/term')
                        else:
                            socketio.emit('output', {'data': raw + '\r\n'}, room=sid, namespace='/term')
                    except Exception:
                        socketio.emit('output', {'data': raw + '\r\n'}, room=sid, namespace='/term')
            except Exception:
                pass

        socketio.start_background_task(_read_nodepty_output, process, request.sid)
        return

    if not _terminal_supported or pty is None:
        message = (
            '\r\n\x1b[31m*** 当前系统不支持 Web 终端（需要 Linux '
            'PTY/termios）***\x1b[0m\r\n'
        )
        socketio.emit('output', {'data': message}, room=request.sid, namespace='/term')
        return

    cwd = (data or {}).get('cwd', _terminal_root_dir)
    if not os.path.abspath(cwd).startswith(
        os.path.abspath(_terminal_root_dir)
    ):
        cwd = _terminal_root_dir
    if not os.path.exists(cwd):
        cwd = _terminal_root_dir

    master, slave = pty.openpty()
    process = subprocess.Popen(
        ['/bin/bash'],
        preexec_fn=TERMINAL_PREEXEC_FN,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=cwd,
        env={**os.environ, "TERM": "xterm-256color"},
    )
    _terminal_sessions[request.sid] = {'fd': master, 'process': process}
    os.close(slave)

    def _read_terminal_output(fd, sid):
        try:
            while True:
                socketio.sleep(0.01)
                if sid not in _terminal_sessions:
                    break
                readable, _w, _e = select.select([fd], [], [], 0)
                if fd in readable:
                    output = os.read(fd, 10240)
                    if not output:
                        break
                    socketio.emit(
                        'output',
                        {'data': output.decode('utf-8', 'ignore')},
                        room=sid,
                        namespace='/term',
                    )
        except OSError:
            pass

    socketio.start_background_task(_read_terminal_output, master, request.sid)
    return


@socketio.on('input', namespace='/term')
def term_on_input(data):
    session = _terminal_sessions.get(request.sid)
    if session and session.get('kind') == 'nodepty':
        proc = session.get('process')
        if proc and proc.stdin:
            try:
                msg = {'type': 'input', 'data': (data or {}).get('input', '')}
                proc.stdin.write(json.dumps(msg, ensure_ascii=False) + '\n')
                proc.stdin.flush()
            except Exception:
                pass
        return
    if session:
        os.write(session['fd'], (data or {}).get('input', '').encode())


@socketio.on('resize', namespace='/term')
def term_on_resize(data):
    session = _terminal_sessions.get(request.sid)
    if session and session.get('kind') == 'nodepty':
        proc = session.get('process')
        if proc and proc.stdin:
            try:
                msg = {'type': 'resize', 'cols': int((data or {}).get('cols') or 0), 'rows': int((data or {}).get('rows') or 0)}
                proc.stdin.write(json.dumps(msg, ensure_ascii=False) + '\n')
                proc.stdin.flush()
            except Exception:
                pass
        return
    if not _terminal_supported or fcntl is None or termios is None:
        return
    if session:
        fd = session['fd']
        winsize = struct.pack(
            "HHHH",
            int((data or {}).get('rows') or 0),
            int((data or {}).get('cols') or 0),
            0,
            0,
        )
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
    return


@socketio.on('disconnect', namespace='/term')
def term_disconnect():
    session = _terminal_sessions.get(request.sid)
    if session:
        try:
            if session.get('kind') == 'nodepty':
                proc = session.get('process')
                if proc and proc.stdin:
                    try:
                        proc.stdin.write(json.dumps({'type': 'close'}, ensure_ascii=False) + '\n')
                        proc.stdin.flush()
                    except Exception:
                        pass
                if proc:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
            else:
                os.close(session['fd'])
                session['process'].terminate()
        except Exception:
            pass
        del _terminal_sessions[request.sid]


@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception('Unhandled exception')
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': {'message': 'Internal Server Error'},
        }), 500
    return '服务器内部错误', 500


@app.route('/@vite/client')
def vite_client_noop():
    return Response('export {};', mimetype='application/javascript')


if __name__ == '__main__':
    try:
        socketio.run(
            app,
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.SERVER_DEBUG,
            use_reloader=config.SERVER_USE_RELOADER,
        )
    except KeyboardInterrupt:
        pass
