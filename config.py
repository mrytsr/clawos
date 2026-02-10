import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = os.path.expanduser('~')  # 动态获取当前用户home目录
# ROOT_DIR = '/home/tjx'  # 硬编码示例
DATA_DIR = os.path.abspath(os.path.join(os.path.expanduser('~'), '.local', 'clawos'))
os.makedirs(DATA_DIR, exist_ok=True)
TRASH_DIR = os.path.join(DATA_DIR, 'trash')
os.makedirs(TRASH_DIR, exist_ok=True)

CONVERSATION_FILE = os.path.join(DATA_DIR, 'conversations.json')
AUTH_FILE = os.path.join(DATA_DIR, 'auth.json')
PIN_FILE = os.path.join(DATA_DIR, 'pin.json')

AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', '46e9b994b1cd055')

SERVER_HOST = '0.0.0.0'
SERVER_PORT = int(os.getenv('SERVER_PORT', '6002'))
SERVER_DEBUG = os.getenv('SERVER_DEBUG', '0') in {'1', 'true', 'True'}
SERVER_USE_RELOADER = os.getenv('SERVER_USE_RELOADER', '0') in {'1', 'true', 'True'}
