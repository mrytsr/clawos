import atexit
import json
import os
import random
import re
import subprocess
import threading
import time


from flask import Flask, jsonify, request
from flask import Response
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException

import config
from lib import frp_utils, path_utils

from ctrl.api_ctrl import api_bp
from ctrl.api_ctrl import _ApiContext
from ctrl.auth_ctrl import auth_bp
from ctrl.batch_ctrl import batch_bp
from ctrl.browser_ctrl import browser_bp
from ctrl.edit_ctrl import edit_bp
from ctrl.file_ctrl import file_bp
from ctrl.model_config_ctrl import model_config_bp
from ctrl.git_ctrl import git_bp
from ctrl.hermes_ctrl import hermes_bp
from ctrl.clash_ctrl import clash_bp
from ctrl.cron_ctrl import cron_bp
from ctrl.db_ctrl import db_bp
from ctrl.frp_ctrl import frp_bp, _systemctl_user_show
from ctrl.log_ctrl import log_bp
from ctrl.ollama_ctrl import ollama_bp
from ctrl.openclaw_ctrl import openclaw_bp
from ctrl.picoclaw_ctrl import picoclaw_bp
from ctrl.nanobot_ctrl import nanobot_bp
from ctrl.nullclaw_ctrl import nullclaw_bp
from ctrl.zeroclaw_ctrl import zeroclaw_bp
from ctrl.system_ctrl import system_bp
from ctrl.task_ctrl import task_bp
from ctrl.term_ctrl import register_term_socketio

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading',
)

_template_root_dir = config.ROOT_DIR
_base_dir = os.path.dirname(__file__)
_frp_packs_dir = frp_utils.frp_bin_dir(_base_dir)
_frpc_process = None
_frpc_output_thread = None
_frpc_cleanup_registered = False


try:
    import psutil
except Exception:
    psutil = None


def _frpc_log(message):
    text = '[frpc] ' + str(message)
    print(text, flush=True)
    try:
        app.logger.info(text)
    except Exception:
        pass


def _pid_alive(pid):
    try:
        pid_int = int(pid)
    except Exception:
        return False
    if pid_int <= 0:
        return False
    if psutil is not None:
        try:
            return bool(psutil.pid_exists(pid_int))
        except Exception:
            return False
    if os.name != 'nt':
        try:
            os.kill(pid_int, 0)
            return True
        except Exception:
            return False
    return False


def _kill_pid(pid):
    try:
        pid_int = int(pid)
    except Exception:
        return False
    if pid_int <= 0:
        return False
    if psutil is not None:
        try:
            try:
                p = psutil.Process(pid_int)
            except Exception:
                return False

            children = []
            try:
                children = p.children(recursive=True)
            except Exception:
                children = []

            for c in children:
                try:
                    c.terminate()
                except Exception:
                    pass

            try:
                _, alive = psutil.wait_procs(children, timeout=2)
            except Exception:
                alive = []

            for c in alive:
                try:
                    c.kill()
                except Exception:
                    pass

            try:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except Exception:
                    p.kill()
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

            try:
                return not psutil.pid_exists(pid_int)
            except Exception:
                return True
        except Exception:
            return False
    if os.name != 'nt':
        try:
            os.kill(pid_int, 15)
            return True
        except Exception:
            return False
    return False


def _load_frpc_server_config():
    path = config.FRP_SERVER_CONFIG_FILE
    data = {
        'autostart': False,
        'chml_p': None,
        'public_addr': '',
        'last_pid': None,
        'last_error': '',
    }
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data.update(raw)
                data['autostart'] = bool(data.get('autostart', False))
                if data.get('chml_p') is not None:
                    try:
                        data['chml_p'] = int(data.get('chml_p'))
                    except Exception:
                        data['chml_p'] = None
                if data.get('last_pid') is not None:
                    try:
                        data['last_pid'] = int(data.get('last_pid'))
                    except Exception:
                        data['last_pid'] = None
                data['public_addr'] = str(data.get('public_addr') or '').strip()
                data['last_error'] = str(data.get('last_error') or '').strip()
    except Exception as e:
        _frpc_log('读取服务端 FRP 配置失败: ' + str(e))
    return data


def _save_frpc_server_config(data):
    path = config.FRP_SERVER_CONFIG_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = {}
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                existing = raw
    except Exception:
        existing = {}
    payload = dict(existing)
    payload.update(dict(data or {}))
    payload['autostart'] = bool(payload.get('autostart', False))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _set_frpc_autostart(enabled):
    return _save_frpc_server_config({'autostart': bool(enabled)})


def _get_frpc_runtime_state():
    cfg = _load_frpc_server_config()
    proc = _frpc_process
    pid = None
    if proc is not None and proc.poll() is None:
        pid = proc.pid
    else:
        pid = cfg.get('last_pid')
    running = bool(pid and _pid_alive(pid))
    return {
        'available': True,
        'id': 'embedded-frpc',
        'description': 'Embedded FRP Client',
        'running': running,
        'active_state': 'active' if running else 'inactive',
        'sub_state': 'running' if running else 'dead',
        'autostart': bool(cfg.get('autostart', False)),
        'pid': int(pid) if running else None,
        'source': 'app',
    }


def _print_frpc_mapping_summary(prefix):
    cfg = _load_frpc_server_config()
    token, profile = frp_utils.resolve_chml_profile(cfg.get('chml_p'))
    p = cfg.get('chml_p') if cfg.get('chml_p') is not None else (profile or {}).get('p')
    remote_addr = cfg.get('public_addr') or (profile or {}).get('remote') or ''
    proc = _frpc_process
    pid = proc.pid if (proc is not None and proc.poll() is None) else cfg.get('last_pid')
    running = bool(pid and _pid_alive(pid))
    reason = None if running else (cfg.get('last_error') or '未运行')
    summary = frp_utils.build_chml_mapping_summary(config.SERVER_PORT, p, remote_addr, running, pid=(int(pid) if running else None), reason=reason)
    if not summary.get('ok'):
        _frpc_log(f'{prefix}，但解析 frpc.toml 失败: {summary.get("reason") or "未知错误"}')
        return
    _frpc_log(prefix)
    items = summary.get('items') or []
    if not items:
        _frpc_log('未发现公网映射')
        return
    runtime = summary.get('runtime') or {}
    if runtime.get('ok') is False:
        _frpc_log('chmlfrpc 状态: ' + str(runtime.get('reason') or '未知错误'))
    for item in items:
        _frpc_log(
            f'映射 {item.get("name")}: 本地 {item.get("local")} -> 远程 {item.get("remote")} '
            f'可复制访问: {item.get("url") or "-"}'
        )


def get_frpc_public_status():
    cfg = _load_frpc_server_config()
    token, profile = frp_utils.resolve_chml_profile(cfg.get('chml_p'))
    p = cfg.get('chml_p') if cfg.get('chml_p') is not None else (profile or {}).get('p')
    remote_addr = cfg.get('public_addr') or (profile or {}).get('remote') or ''
    proc = _frpc_process
    pid = proc.pid if (proc is not None and proc.poll() is None) else cfg.get('last_pid')
    running = bool(pid and _pid_alive(pid))
    reason = None if running else (cfg.get('last_error') or '未运行')
    return frp_utils.build_chml_mapping_summary(config.SERVER_PORT, p, remote_addr, running, pid=(int(pid) if running else None), reason=reason)


def get_frpc_public_urls():
    summary = get_frpc_public_status()
    urls = []
    seen = set()
    for item in summary.get('items') or []:
        url = str(item.get('url') or '').strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _print_public_running_on():
    urls = get_frpc_public_urls()
    for url in urls:
        print(f' * Public Running on {url}', flush=True)


def _schedule_public_running_on_log():
    def _job():
        time.sleep(1.2)
        try:
            _print_public_running_on()
        except Exception:
            pass
    threading.Thread(target=_job, daemon=True).start()


def _pump_frpc_output(proc):
    return _pump_frpc_output_with_queue(proc, None)


def _pump_frpc_output_with_queue(proc, line_queue):
    try:
        stream = proc.stdout
        if stream is None:
            return
        for line in iter(stream.readline, ''):
            text = (line or '').rstrip()
            if text:
                _frpc_log(text)
                if line_queue is not None:
                    try:
                        line_queue.put_nowait(text)
                    except Exception:
                        pass
    except Exception as e:
        _frpc_log(f'输出监听异常: {e}')


def _start_embedded_frpc():
    global _frpc_process, _frpc_output_thread
    global _frpc_cleanup_registered
    runtime_cfg = _load_frpc_server_config()
    if _frpc_process is not None and _frpc_process.poll() is None:
        return True, 'already running'
    if runtime_cfg.get('last_pid') and _pid_alive(runtime_cfg.get('last_pid')):
        return True, 'already running'
    if os.name != 'nt':
        try:
            service = _systemctl_user_show('frpc.service')
            if service.get('running'):
                _print_frpc_mapping_summary('检测到 frpc.service 已在运行，跳过 app.py 内置 frpc 启动')
                return False, 'frpc.service is already running'
        except Exception:
            pass
    frpc_path = frp_utils.current_chmlfrpc_binary_path(_base_dir)
    if not os.path.exists(frpc_path):
        _frpc_log('启动失败: 当前系统对应的 frpc 可执行文件不存在: ' + frpc_path)
        _save_frpc_server_config({'last_error': 'frpc binary not found'})
        return False, 'frpc binary not found'
    try:
        token = frp_utils.chml_profiles().get('token') or ''
        if not token:
            _frpc_log('启动失败: 未配置可用的 chmlfrpc token')
            _save_frpc_server_config({'last_error': 'missing chmlfrpc token'})
            return False, 'missing chmlfrpc token'
        log_path = os.path.join(config.DATA_DIR, 'chmlfrpc.nohup.log')
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        kwargs = {
            'cwd': _frp_packs_dir,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'bufsize': 1,
        }
        if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            flags = subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, 'DETACHED_PROCESS'):
                flags |= subprocess.DETACHED_PROCESS
            if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP'):
                flags |= subprocess.CREATE_NEW_PROCESS_GROUP
            kwargs['creationflags'] = flags
        if os.name != 'nt':
            kwargs['start_new_session'] = True

        success_patterns = [
            re.compile(r'login to server success', re.IGNORECASE),
            re.compile(r'start proxy success', re.IGNORECASE),
            re.compile(r'proxy added', re.IGNORECASE),
            re.compile(r'成功登录至服务器'),
            re.compile(r'映射启动成功'),
            re.compile(r'已启动隧道'),
        ]
        failure_patterns = [
            re.compile(r'start error', re.IGNORECASE),
            re.compile(r'login to server failed', re.IGNORECASE),
            re.compile(r'connect to server.*(error|fail)', re.IGNORECASE),
            re.compile(r'登录.*失败'),
            re.compile(r'获取.*配置.*失败'),
            re.compile(r'启动.*失败'),
        ]

        last_reason = ''
        remaining = list((frp_utils.chml_profiles().get('items') or []))
        random.shuffle(remaining)
        while remaining:
            idx = random.randrange(0, len(remaining))
            profile = remaining.pop(idx)
            p = (profile or {}).get('p')
            remote_addr = (profile or {}).get('remote') or ''
            if not p:
                continue
            attempt_started_at = time.time()

            start_pos = 0
            try:
                if os.path.exists(log_path):
                    start_pos = os.path.getsize(log_path)
            except Exception:
                start_pos = 0

            log_fp = open(log_path, 'a', encoding='utf-8', errors='replace', newline='\n')
            proc = subprocess.Popen([frpc_path, '-u', token, '-p', str(p)], stdout=log_fp, stderr=subprocess.STDOUT, **kwargs)
            log_fp.flush()
            log_fp.close()

            ok = False
            reason = ''
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if proc.poll() is not None:
                    reason = f'退出码 {proc.returncode}'
                    break
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='replace') as rf:
                        rf.seek(start_pos)
                        chunk = rf.read()
                        start_pos = rf.tell()
                    if chunk:
                        for raw in chunk.splitlines():
                            if raw:
                                _frpc_log(raw)
                                for rx in failure_patterns:
                                    if rx.search(raw):
                                        reason = raw
                                        break
                                if reason:
                                    break
                                for rx in success_patterns:
                                    if rx.search(raw):
                                        ok = True
                                        break
                                if ok:
                                    break
                except Exception:
                    pass
                if reason or ok:
                    break
                time.sleep(0.2)
            if not ok and not reason and proc.poll() is None:
                reason = '5秒内未检测到启动成功'
            if ok:
                pid_to_track = None
                if proc.poll() is None:
                    _frpc_process = proc
                    _frpc_output_thread = None
                    pid_to_track = proc.pid
                else:
                    _frpc_process = None
                    _frpc_output_thread = None
                    if psutil is not None:
                        try:
                            best = None
                            for pinfo in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                                info = pinfo.info or {}
                                ctime = float(info.get('create_time') or 0)
                                if ctime and ctime < (attempt_started_at - 2):
                                    continue
                                cmd = info.get('cmdline') or []
                                if isinstance(cmd, str):
                                    cmd = [cmd]
                                if not any(str(x).lower().endswith('frpc.ini') for x in cmd):
                                    continue
                                name = str(info.get('name') or '').lower()
                                if 'frpc' not in name:
                                    continue
                                if best is None or ctime > float(best.get('create_time') or 0):
                                    best = info
                            if best and best.get('pid'):
                                pid_to_track = int(best['pid'])
                        except Exception:
                            pid_to_track = None
                _save_frpc_server_config({'last_error': '', 'last_pid': pid_to_track, 'chml_p': int(p), 'public_addr': str(remote_addr)})
                if not _frpc_cleanup_registered:
                    try:
                        atexit.register(_stop_embedded_frpc)
                    except Exception:
                        pass
                    _frpc_cleanup_registered = True
                print('=>'+str(remote_addr), flush=True)
                _print_frpc_mapping_summary('启动成功')
                return True, 'started'

            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        proc.kill()
            except Exception:
                pass

            last_reason = reason or last_reason or '启动失败'
            _save_frpc_server_config({'last_error': last_reason, 'last_pid': None})

        _frpc_log('启动失败: ' + (last_reason or '未知错误'))
        _frpc_process = None
        _frpc_output_thread = None
        return False, last_reason or 'start failed'
    except Exception:
        app.logger.exception('Failed to start embedded frpc')
        _frpc_log('启动失败: ' + re.sub(r'\s+', ' ', str(os.sys.exc_info()[1]) or '未知错误').strip())
        _save_frpc_server_config({'last_error': str(os.sys.exc_info()[1]) or '未知错误', 'last_pid': None})
        _frpc_process = None
        return False, str(os.sys.exc_info()[1]) or '未知错误'
    return True, 'started'


def _stop_embedded_frpc():
    global _frpc_process, _frpc_output_thread
    proc = _frpc_process
    cfg = _load_frpc_server_config()
    pid = None
    if proc is not None and proc.poll() is None:
        pid = proc.pid
    else:
        pid = cfg.get('last_pid')
    if not pid or not _pid_alive(pid):
        _frpc_process = None
        _frpc_output_thread = None
        _save_frpc_server_config({'last_pid': None})
        return True, 'not running'
    try:
        stopped = _kill_pid(pid)
        if (not stopped) and _pid_alive(pid) and proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        stopped = stopped or (not _pid_alive(pid))
    except Exception:
        return False, str(os.sys.exc_info()[1]) or 'stop failed'
    if not stopped:
        return False, 'stop failed'
    _frpc_process = None
    _frpc_output_thread = None
    _save_frpc_server_config({'last_pid': None})
    _frpc_log('已停止')
    return True, 'stopped'


app.extensions['frpc_runtime'] = {
    'get_state': _get_frpc_runtime_state,
    'start': _start_embedded_frpc,
    'stop': _stop_embedded_frpc,
    'set_autostart': _set_frpc_autostart,
    'get_config': _load_frpc_server_config,
    'get_mapping_summary': get_frpc_public_status,
    'get_public_status': get_frpc_public_status,
}


@app.get('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')


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
app.register_blueprint(git_bp)
app.register_blueprint(hermes_bp)
app.register_blueprint(system_bp)
app.register_blueprint(frp_bp)
app.register_blueprint(clash_bp)
app.register_blueprint(cron_bp)
app.register_blueprint(db_bp)
app.register_blueprint(log_bp)
app.register_blueprint(ollama_bp)
app.register_blueprint(openclaw_bp)
app.register_blueprint(picoclaw_bp)
app.register_blueprint(nanobot_bp)
app.register_blueprint(task_bp)
app.register_blueprint(nullclaw_bp)
app.register_blueprint(zeroclaw_bp)
app.register_blueprint(browser_bp)
app.register_blueprint(edit_bp)
app.register_blueprint(file_bp)
app.register_blueprint(model_config_bp)
register_term_socketio(socketio, terminal_root_dir=config.ROOT_DIR)

@app.after_request
def add_default_headers(resp):
    try:
        if not resp.headers.get('X-Content-Type-Options'):
            resp.headers['X-Content-Type-Options'] = 'nosniff'
    except Exception:
        pass
    return resp


@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception('Unhandled exception')
    if request.path.startswith('/api/'):
        trace_on = False
        try:
            trace_on = bool(config.SERVER_DEBUG) or (request.headers.get('X-ClawOS-Trace') == '1')
        except Exception:
            trace_on = False
        if trace_on:
            import traceback
            return jsonify({
                'success': False,
                'error': {'message': str(e) or 'Internal Server Error'},
                'trace': traceback.format_exc(),
            }), 500
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
        should_start_frpc = (not config.SERVER_USE_RELOADER) or (os.environ.get('WERKZEUG_RUN_MAIN') == 'true')
        if should_start_frpc:
            runtime_cfg = _load_frpc_server_config()
            if runtime_cfg.get('autostart'):
                _start_embedded_frpc()
            else:
                _frpc_log('未启用自启动')
            _schedule_public_running_on_log()
        socketio.run(
            app,
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.SERVER_DEBUG,
            use_reloader=config.SERVER_USE_RELOADER,
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        pass
    finally:
        _stop_embedded_frpc()
