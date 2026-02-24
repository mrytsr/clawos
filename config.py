import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = os.path.expanduser('~')  # 动态获取当前用户home目录

DATA_DIR = os.path.abspath(os.path.join(os.path.expanduser('~'), '.local', 'clawos'))
os.makedirs(DATA_DIR, exist_ok=True)
TRASH_DIR = os.path.join(DATA_DIR, 'trash')
os.makedirs(TRASH_DIR, exist_ok=True)

CONVERSATION_FILE = os.path.join(DATA_DIR, 'conversations.json')
AUTH_FILE = os.path.join(DATA_DIR, 'auth.json')
PIN_FILE = os.path.join(DATA_DIR, 'pin.json')

import os as _os
_AUTH_FILE = _os.path.expanduser('~/.local/clawos/clawos_password.json')
if _os.path.exists(_AUTH_FILE):
    import json as _json
    AUTH_PASSWORD = _json.load(open(_AUTH_FILE))['password']
else:
    AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', '')

SERVER_HOST = '0.0.0.0'
SERVER_PORT = int(os.getenv('SERVER_PORT', '6002'))
SERVER_DEBUG = os.getenv('SERVER_DEBUG', '0') in {'1', 'true', 'True'}
SERVER_USE_RELOADER = os.getenv('SERVER_USE_RELOADER', '0') in {'1', 'true', 'True'}

# 文件打开方式配置
FILE_OPEN_CONFIG_FILE = os.path.join(DATA_DIR, 'file_open_config.json')
