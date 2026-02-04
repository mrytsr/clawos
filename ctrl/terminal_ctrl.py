import os
import select
import struct
import subprocess

from flask import request

import config


def register_terminal(socketio):
    root_dir = config.ROOT_DIR
    terminal_supported = os.name != 'nt'

    user_sessions = {}

    if terminal_supported:
        try:
            import fcntl
            import pty
            import termios
        except Exception:
            terminal_supported = False

    @socketio.on('connect', namespace='/term')
    def connect():
        pass

    @socketio.on('create_terminal', namespace='/term')
    def create_terminal(data):
        if not terminal_supported:
            socketio.emit(
                'output',
                {'data': '\r\n\x1b[31m*** 当前系统不支持 Web 终端（需要 Linux PTY/termios）***\x1b[0m\r\n'},
                room=request.sid,
                namespace='/term'
            )
            return

        cwd = data.get('cwd', root_dir)
        if not os.path.abspath(cwd).startswith(os.path.abspath(root_dir)):
            cwd = root_dir
        if not os.path.exists(cwd):
            cwd = root_dir

        (master, slave) = pty.openpty()
        p = subprocess.Popen(
            ['/bin/bash'],
            preexec_fn=os.setsid,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=cwd,
            env={**os.environ, "TERM": "xterm-256color"}
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
        if not terminal_supported:
            return
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
            except Exception:
                pass
            del user_sessions[request.sid]
