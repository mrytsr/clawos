import logging
import os

from flask import Flask, jsonify, request
from flask import Response
from flask_socketio import SocketIO
from werkzeug.exceptions import HTTPException

import config

from ctrl.api_ctrl import register_api
from ctrl.auth_ctrl import register_auth
from ctrl.batch_ctrl import register_batch
from ctrl.bot_proxy_ctrl import register_bot_proxy
from ctrl.file_ctrl import register_file
from ctrl.system_ctrl import register_system
from ctrl.template_ctrl import register_template_helpers
from ctrl.terminal_ctrl import register_terminal

if os.name != 'nt':
    import eventlet
    eventlet.monkey_patch()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading' if os.name == 'nt' else None,
)

register_auth(app)
register_template_helpers(app)
register_api(app)
register_batch(app)
register_system(app)
register_file(app)
register_terminal(socketio)
register_bot_proxy(socketio)

logging.basicConfig(level=logging.INFO)


@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception('Unhandled exception')
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': {'message': 'Internal Server Error'}}), 500
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
