import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = '/home/tjx' #os.getenv('ROOT_DIR', os.path.dirname(SCRIPT_DIR))
CONVERSATION_FILE = os.path.join(SCRIPT_DIR, 'data', 'conversations.json')
TRASH_DIR = os.path.join(ROOT_DIR, '_trash')

AUTH_USERNAME = 'admin'
AUTH_PASSWORD = 'admin'

SERVER_HOST = '0.0.0.0'
SERVER_PORT = int(os.getenv('SERVER_PORT', '6002'))
SERVER_DEBUG = os.getenv('SERVER_DEBUG', '0') in {'1', 'true', 'True'}
SERVER_USE_RELOADER = os.getenv('SERVER_USE_RELOADER', '0') in {'1', 'true', 'True'}
