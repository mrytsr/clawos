import importlib
import json
import os
import select
import shutil
import struct
import subprocess

from flask import request

import config


TERMINAL_PREEXEC_FN = getattr(os, 'setsid', None)

_terminal_root_dir = config.ROOT_DIR
_terminal_supported = True
_terminal_sessions = {}
fcntl = None
pty = None
termios = None

_node_bin = shutil.which('node') if os.name == 'nt' else None
_node_bridge = os.path.join(config.SCRIPT_DIR, 'win_pty_bridge.js')

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


def register_term_socketio(socketio, terminal_root_dir=None):
    global _terminal_root_dir
    if terminal_root_dir:
        _terminal_root_dir = terminal_root_dir

    def _safe_cwd(data):
        cwd = (data or {}).get('cwd', _terminal_root_dir)
        try:
            if not os.path.abspath(cwd).startswith(os.path.abspath(_terminal_root_dir)):
                cwd = _terminal_root_dir
        except Exception:
            cwd = _terminal_root_dir
        if not os.path.exists(cwd):
            cwd = _terminal_root_dir
        return cwd

    def term_connect():
        return

    def term_create_terminal(data):
        if os.name == 'nt':
            if not _node_bin or not os.path.exists(_node_bridge):
                message = (
                    '\r\n\x1b[31m*** 当前系统未启用 Web 终端（Windows 需要 Node.js + node-pty）***\x1b[0m\r\n'
                )
                socketio.emit('output', {'data': message}, room=request.sid, namespace='/term')
                return

            cwd = _safe_cwd(data)

            process = subprocess.Popen(
                [_node_bin, _node_bridge],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=config.SCRIPT_DIR,
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

        cwd = _safe_cwd(data)

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

    def term_on_resize(data):
        session = _terminal_sessions.get(request.sid)
        if session and session.get('kind') == 'nodepty':
            proc = session.get('process')
            if proc and proc.stdin:
                try:
                    msg = {
                        'type': 'resize',
                        'cols': int((data or {}).get('cols') or 0),
                        'rows': int((data or {}).get('rows') or 0),
                    }
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

    socketio.on('connect', namespace='/term')(term_connect)
    socketio.on('create_terminal', namespace='/term')(term_create_terminal)
    socketio.on('input', namespace='/term')(term_on_input)
    socketio.on('resize', namespace='/term')(term_on_resize)
    socketio.on('disconnect', namespace='/term')(term_disconnect)
