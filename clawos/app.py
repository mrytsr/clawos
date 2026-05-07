import atexit
import json
import os
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


def _frpc_log(message):
    text = '[frpc] ' + str(message)
    print(text, flush=True)
    try:
        app.logger.info(text)
    except Exception:
        pass


def _load_frpc_server_config():
    path = config.FRP_SERVER_CONFIG_FILE
    data = {'autostart': False}
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data['autostart'] = bool(raw.get('autostart', False))
    except Exception as e:
        _frpc_log('读取服务端 FRP 配置失败: ' + str(e))
    return data


def _save_frpc_server_config(data):
    path = config.FRP_SERVER_CONFIG_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {'autostart': bool((data or {}).get('autostart', False))}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def _set_frpc_autostart(enabled):
    return _save_frpc_server_config({'autostart': bool(enabled)})


def _get_frpc_runtime_state():
    cfg = _load_frpc_server_config()
    proc = _frpc_process
    running = bool(proc is not None and proc.poll() is None)
    return {
        'available': True,
        'id': 'embedded-frpc',
        'description': 'Embedded FRP Client',
        'running': running,
        'active_state': 'active' if running else 'inactive',
        'sub_state': 'running' if running else 'dead',
        'autostart': bool(cfg.get('autostart', False)),
        'pid': proc.pid if running else None,
        'source': 'app',
    }


def _print_frpc_mapping_summary(prefix):
    summary = frp_utils.load_frpc_mapping_summary(_base_dir)
    if not summary.get('ok'):
        _frpc_log(f'{prefix}，但解析 frpc.toml 失败: {summary.get("reason") or "未知错误"}')
        return
    server_addr = summary.get('server_addr') or '-'
    server_port = summary.get('server_port')
    _frpc_log(f'{prefix}，FRP 服务端: {server_addr}:{server_port if server_port else "-"}')
    items = summary.get('items') or []
    if not items:
        _frpc_log('未在 frpc.toml 中发现代理映射')
        return
    runtime = summary.get('runtime') or {}
    if runtime.get('ok') is False:
        _frpc_log('frpc status 获取失败: ' + str(runtime.get('reason') or '未知错误'))
    for item in items:
        _frpc_log(
            f'映射 {item.get("name")}: 本地 {item.get("local")} -> 远程 {item.get("remote")} '
            f'可复制访问: {item.get("url") or "-"}'
        )


def get_frpc_public_status():
    return frp_utils.load_frpc_mapping_summary(_base_dir)


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
    try:
        stream = proc.stdout
        if stream is None:
            return
        for line in iter(stream.readline, ''):
            text = (line or '').rstrip()
            if text:
                _frpc_log(text)
    except Exception as e:
        _frpc_log(f'输出监听异常: {e}')


def _start_embedded_frpc():
    global _frpc_process, _frpc_output_thread
    if _frpc_process is not None:
        return True, 'already running'
    if os.name != 'nt':
        try:
            service = _systemctl_user_show('frpc.service')
            if service.get('running'):
                _print_frpc_mapping_summary('检测到 frpc.service 已在运行，跳过 app.py 内置 frpc 启动')
                return False, 'frpc.service is already running'
        except Exception:
            pass
    frpc_path = frp_utils.current_frpc_binary_path(_base_dir)
    config_path = frp_utils.current_frpc_config_path(_base_dir)
    if not os.path.exists(frpc_path):
        _frpc_log('启动失败: 当前系统对应的 frpc 可执行文件不存在: ' + frpc_path)
        return False, 'frpc binary not found'
    if not os.path.exists(config_path):
        _frpc_log('启动失败: frpc.toml 不存在: ' + config_path)
        return False, 'frpc.toml not found'
    try:
        rewrite_result = frp_utils.rewrite_frpc_proxy_names_with_uuid(_base_dir)
        if not rewrite_result.get('ok'):
            reason = rewrite_result.get('reason') or 'rewrite proxy name failed'
            _frpc_log('启动失败: 写入 UUID name 失败: ' + reason)
            return False, reason
        if rewrite_result.get('updated'):
            _frpc_log(f'已写入 {rewrite_result.get("updated")} 个 UUID 代理名')
        if os.name != 'nt':
            os.chmod(frpc_path, 0o755)
        kwargs = {
            'cwd': _frp_packs_dir,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'text': True,
            'encoding': 'utf-8',
            'errors': 'replace',
            'bufsize': 1,
        }
        if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        _frpc_process = subprocess.Popen(
            [frpc_path, '-c', config_path],
            **kwargs,
        )
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if _frpc_process.poll() is not None:
                break
            time.sleep(0.1)
        if _frpc_process.poll() is not None:
            output = ''
            try:
                output = (_frpc_process.communicate(timeout=1)[0] or '').strip()
            except Exception:
                output = ''
            code = _frpc_process.returncode
            reason = output or f'退出码 {code}'
            _frpc_log(f'启动失败: {reason}')
            _frpc_process = None
            return False, reason
        _print_frpc_mapping_summary('启动成功')
        _frpc_output_thread = threading.Thread(target=_pump_frpc_output, args=(_frpc_process,), daemon=True)
        _frpc_output_thread.start()
    except Exception:
        app.logger.exception('Failed to start embedded frpc')
        _frpc_log('启动失败: ' + re.sub(r'\s+', ' ', str(os.sys.exc_info()[1]) or '未知错误').strip())
        _frpc_process = None
        return False, str(os.sys.exc_info()[1]) or '未知错误'
    return True, 'started'


def _stop_embedded_frpc():
    global _frpc_process, _frpc_output_thread
    proc = _frpc_process
    if proc is None:
        return True, 'not running'
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
    except Exception:
        return False, str(os.sys.exc_info()[1]) or 'stop failed'
    _frpc_process = None
    _frpc_output_thread = None
    _frpc_log('已停止')
    return True, 'stopped'


atexit.register(_stop_embedded_frpc)
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
