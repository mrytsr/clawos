import importlib
import collections
import json
import os
import select
import shutil
import struct
import subprocess
import threading
import time

from flask import request

import config


TERMINAL_PREEXEC_FN = getattr(os, 'setsid', None)

_terminal_root_dir = config.ROOT_DIR
_terminal_sessions = {}
fcntl = None
pty = None
termios = None

_node_bin = shutil.which('node') if os.name == 'nt' else None
_node_bridge = os.path.join(config.SCRIPT_DIR, 'win_pty_bridge.js')
_git_bash_path = ''
_terminal_backend_type = None
_terminal_backend_detail = {'type': None, 'missing': [], 'message': ''}

def _probe_node_pty_installed(node_bin):
    if not node_bin:
        return False
    try:
        r = subprocess.run(
            [node_bin, '-e', "require('node-pty');process.exit(0)"],
            cwd=config.SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=2,
        )
        return r.returncode == 0
    except Exception:
        return False


def _detect_terminal_backend():
    global fcntl, pty, termios, _terminal_backend_type, _terminal_backend_detail, _git_bash_path

    if os.name != 'nt':
        try:
            fcntl = importlib.import_module('fcntl')
            pty = importlib.import_module('pty')
            termios = importlib.import_module('termios')
            _terminal_backend_type = 'pty'
            _terminal_backend_detail = {'type': 'pty', 'missing': [], 'message': ''}
            return
        except Exception:
            fcntl = None
            pty = None
            termios = None

    missing = []
    if os.name == 'nt':
        if not _node_bin:
            missing.append('Node.js')
        if not os.path.exists(_node_bridge):
            missing.append('win_pty_bridge.js')
        _git_bash_path = _find_git_bash_path()
        if not _git_bash_path:
            missing.append('Git Bash')
        if _node_bin and not _probe_node_pty_installed(_node_bin):
            missing.append('node-pty')
        if not missing:
            _terminal_backend_type = 'node-pty'
            _terminal_backend_detail = {'type': 'node-pty', 'missing': [], 'message': ''}
            return

    _terminal_backend_type = None
    _terminal_backend_detail = {
        'type': None,
        'missing': missing,
        'message': '',
    }


def _find_git_bash_path():
    explicit = os.environ.get('GIT_BASH') or os.environ.get('GIT_BASH_PATH') or ''
    if explicit and os.path.exists(explicit):
        return explicit

    which = shutil.which('bash.exe') or shutil.which('bash')
    if which and os.path.exists(which):
        return which

    program_files = [
        os.environ.get('ProgramFiles') or '',
        os.environ.get('ProgramFiles(x86)') or '',
        os.environ.get('LocalAppData') or '',
    ]
    suffixes = [
        os.path.join('Git', 'bin', 'bash.exe'),
        os.path.join('Git', 'usr', 'bin', 'bash.exe'),
        os.path.join('Programs', 'Git', 'bin', 'bash.exe'),
        os.path.join('Programs', 'Git', 'usr', 'bin', 'bash.exe'),
    ]
    for base in program_files:
        if not base:
            continue
        for s in suffixes:
            cand = os.path.join(base, s)
            if os.path.exists(cand):
                return cand
    return ''


_detect_terminal_backend()


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
        if _terminal_backend_type is None:
            if os.name == 'nt':
                missing = list(_terminal_backend_detail.get('missing') or [])
                parts = []
                if 'Node.js' in missing:
                    parts.append('Node.js')
                if 'node-pty' in missing:
                    parts.append('node-pty（npm i node-pty）')
                if 'Git Bash' in missing:
                    parts.append('Git Bash')
                if 'win_pty_bridge.js' in missing:
                    parts.append('win_pty_bridge.js（项目文件缺失）')
                hint = '、'.join(parts) if parts else '依赖组件'
                message = (
                    '\r\n\x1b[31m*** 当前环境：Windows（终端后端：None）***\x1b[0m\r\n'
                    + '\r\n\x1b[31m*** 需要安装/满足：' + hint + ' 才能启用 Web 终端 ***\x1b[0m\r\n'
                )
            else:
                message = (
                    '\r\n\x1b[31m*** 当前环境：非 Windows（终端后端：None）***\x1b[0m\r\n'
                    + '\r\n\x1b[31m*** 需要 Python 标准库 fcntl/pty/termios 才能启用 Web 终端 ***\x1b[0m\r\n'
                )
            socketio.emit('output', {'data': message}, room=request.sid, namespace='/term')
            return

        if _terminal_backend_type == 'node-pty':
            cwd = _safe_cwd(data)
            bridge_env = os.environ.copy()
            if not bridge_env.get('LANG'):
                bridge_env['LANG'] = 'C.UTF-8'
            if not bridge_env.get('LC_ALL'):
                bridge_env['LC_ALL'] = 'C.UTF-8'
            if not bridge_env.get('LC_CTYPE'):
                bridge_env['LC_CTYPE'] = 'C.UTF-8'

            process = subprocess.Popen(
                [_node_bin, _node_bridge],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=config.SCRIPT_DIR,
                env=bridge_env,
            )
            out_q = collections.deque()
            out_lock = threading.Lock()
            out_ready = threading.Event()
            in_lock = threading.Lock()
            in_ready = threading.Event()
            _terminal_sessions[request.sid] = {
                'kind': 'node-pty',
                'process': process,
                'out_q': out_q,
                'out_lock': out_lock,
                'out_ready': out_ready,
                'out_dropped': 0,
                'in_parts': [],
                'in_len': 0,
                'in_resize': None,
                'in_lock': in_lock,
                'in_ready': in_ready,
            }

            try:
                init = {
                    'type': 'init',
                    'cwd': cwd,
                    'cols': 80,
                    'rows': 24,
                    'shell': _git_bash_path,
                    'args': ['--noprofile', '--norc', '-i'],
                }
                process.stdin.write(json.dumps(init, ensure_ascii=False) + '\n')
                process.stdin.flush()
            except Exception:
                pass

            def _read_nodepty_output(proc, sid, q, lock, ready):
                try:
                    while True:
                        if sid not in _terminal_sessions:
                            break
                        if proc.poll() is not None:
                            break
                        line = proc.stdout.readline()
                        if not line:
                            break
                        raw = line.rstrip('\n')
                        payload = ''
                        try:
                            msg = json.loads(raw)
                            if isinstance(msg, dict) and msg.get('type') == 'output':
                                payload = msg.get('data', '') or ''
                            else:
                                payload = raw + '\r\n'
                        except Exception:
                            payload = raw + '\r\n'

                        if payload:
                            with lock:
                                q.append(payload)
                                if len(q) > 400:
                                    while len(q) > 300:
                                        q.popleft()
                                    s = _terminal_sessions.get(sid) or {}
                                    try:
                                        s['out_dropped'] = int(s.get('out_dropped') or 0) + 1
                                    except Exception:
                                        pass
                            ready.set()
                except Exception:
                    pass
                finally:
                    try:
                        ready.set()
                    except Exception:
                        pass

            def _emit_nodepty_output(sid, q, lock, ready):
                last_emit_at = 0.0
                while True:
                    if sid not in _terminal_sessions:
                        break
                    try:
                        if not ready.wait(timeout=0.25):
                            pass
                    except Exception:
                        socketio.sleep(0.01)

                    ready.clear()

                    buf = []
                    dropped = 0
                    with lock:
                        while q:
                            buf.append(q.popleft())
                        s = _terminal_sessions.get(sid) or {}
                        dropped = int(s.get('out_dropped') or 0)
                        s['out_dropped'] = 0
                    if dropped:
                        buf.insert(0, '\r\n\x1b[33m*** 输出过快，已丢弃部分内容 ***\x1b[0m\r\n')

                    if buf:
                        now = time.time()
                        if now - last_emit_at < 0.016:
                            socketio.sleep(0.016)
                        last_emit_at = time.time()
                        socketio.emit('output', {'data': ''.join(buf)}, room=sid, namespace='/term')

                    proc = None
                    try:
                        s = _terminal_sessions.get(sid)
                        if s:
                            proc = s.get('process')
                    except Exception:
                        proc = None
                    if proc and proc.poll() is not None:
                        with lock:
                            if not q:
                                break
                    socketio.sleep(0)

            def _write_nodepty_input(sid):
                while True:
                    s = _terminal_sessions.get(sid)
                    if not s or s.get('kind') != 'node-pty':
                        break
                    proc = s.get('process')
                    if not proc or not getattr(proc, 'stdin', None):
                        break

                    lock = s.get('in_lock')
                    ready = s.get('in_ready')
                    if not lock or not ready:
                        break

                    try:
                        ready.wait(timeout=0.25)
                    except Exception:
                        socketio.sleep(0.01)
                    ready.clear()

                    resize = None
                    parts = None
                    with lock:
                        resize = s.get('in_resize')
                        s['in_resize'] = None
                        if s.get('in_parts'):
                            parts = s.get('in_parts')
                            s['in_parts'] = []
                            s['in_len'] = 0

                    if resize:
                        try:
                            cols, rows = resize
                            msg = {'type': 'resize', 'cols': int(cols or 0), 'rows': int(rows or 0)}
                            proc.stdin.write(json.dumps(msg, ensure_ascii=False) + '\n')
                            proc.stdin.flush()
                        except Exception:
                            pass

                    if parts:
                        try:
                            data = ''.join(parts)
                        except Exception:
                            data = ''
                        if data:
                            off = 0
                            while off < len(data):
                                chunk = data[off:off + 8192]
                                off += len(chunk)
                                try:
                                    msg = {'type': 'input', 'data': chunk}
                                    proc.stdin.write(json.dumps(msg, ensure_ascii=False) + '\n')
                                    proc.stdin.flush()
                                except Exception:
                                    break

                    if proc.poll() is not None:
                        break
                    socketio.sleep(0)

            socketio.start_background_task(_read_nodepty_output, process, request.sid, out_q, out_lock, out_ready)
            socketio.start_background_task(_emit_nodepty_output, request.sid, out_q, out_lock, out_ready)
            socketio.start_background_task(_write_nodepty_input, request.sid)
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
        _terminal_sessions[request.sid] = {'kind': 'pty', 'fd': master, 'process': process}
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
        if session and session.get('kind') == 'node-pty':
            try:
                s = session
                part = (data or {}).get('input', '')
                if not isinstance(part, str) or not part:
                    return
                lock = s.get('in_lock')
                ready = s.get('in_ready')
                if not lock or not ready:
                    return
                with lock:
                    cur_len = int(s.get('in_len') or 0)
                    if cur_len > 256 * 1024:
                        s['in_parts'] = []
                        s['in_len'] = 0
                        cur_len = 0
                    s.get('in_parts').append(part)
                    s['in_len'] = cur_len + len(part)
                ready.set()
            except Exception:
                pass
            return
        if session:
            os.write(session['fd'], (data or {}).get('input', '').encode())

    def term_on_resize(data):
        session = _terminal_sessions.get(request.sid)
        if session and session.get('kind') == 'node-pty':
            try:
                s = session
                cols = int((data or {}).get('cols') or 0)
                rows = int((data or {}).get('rows') or 0)
                lock = s.get('in_lock')
                ready = s.get('in_ready')
                if not lock or not ready:
                    return
                with lock:
                    s['in_resize'] = (cols, rows)
                ready.set()
            except Exception:
                pass
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
                if session.get('kind') == 'node-pty':
                    proc = session.get('process')
                    try:
                        ready = session.get('in_ready')
                        if ready:
                            ready.set()
                    except Exception:
                        pass
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
