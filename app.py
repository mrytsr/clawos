import os
import re


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
from ctrl.browser_ctrl import browser_bp
from ctrl.edit_ctrl import edit_bp
from ctrl.file_ctrl import file_bp
from ctrl.ai_eval_ctrl import ai_eval_bp
from ctrl.git_ctrl import git_bp
from ctrl.clash_ctrl import clash_bp
from ctrl.cron_ctrl import cron_bp
from ctrl.db_ctrl import db_bp
from ctrl.frp_ctrl import frp_bp
from ctrl.log_ctrl import log_bp
from ctrl.ollama_ctrl import ollama_bp
from ctrl.openclaw_ctrl import openclaw_bp
from ctrl.system_ctrl import system_bp
from ctrl.task_ctrl import task_bp
from ctrl.term_ctrl import register_term_socketio

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading' if os.name == 'nt' else None,
)

_template_root_dir = config.ROOT_DIR


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
app.register_blueprint(system_bp)
app.register_blueprint(frp_bp)
app.register_blueprint(clash_bp)
app.register_blueprint(cron_bp)
app.register_blueprint(db_bp)
app.register_blueprint(log_bp)
app.register_blueprint(ollama_bp)
app.register_blueprint(openclaw_bp)
app.register_blueprint(task_bp)
app.register_blueprint(browser_bp)
app.register_blueprint(edit_bp)
app.register_blueprint(file_bp)
app.register_blueprint(ai_eval_bp)
register_term_socketio(socketio, terminal_root_dir=config.ROOT_DIR)


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
        socketio.run(
            app,
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            debug=config.SERVER_DEBUG,
            use_reloader=config.SERVER_USE_RELOADER,
        )
    except KeyboardInterrupt:
        pass
