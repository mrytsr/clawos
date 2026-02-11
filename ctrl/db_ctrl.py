#!/usr/bin/env python3
"""Enhanced MySQL database management API."""

import os
import json
import subprocess
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify

from ctrl import api_error, api_ok

db_bp = Blueprint('db', __name__)

# 数据库连接配置存储路径
DB_CONFIG_DIR = os.path.expanduser('~/.local/share/clawos')
os.makedirs(DB_CONFIG_DIR, exist_ok=True)
DB_CONFIG_FILE = os.path.join(DB_CONFIG_DIR, 'db_connections.json')

# 加密密钥
ENCRYPTION_KEY = os.environ.get('DB_ENCRYPTION_KEY', 'clawos-db-secret-key-32chars!')[:32]


def _encrypt(text):
    """简单加密（实际项目建议用 Fernet）."""
    if not text:
        return ''
    import base64
    return base64.b64encode(text.encode()).decode()


def _decrypt(encrypted):
    """解密."""
    if not encrypted:
        return ''
    try:
        return base64.b64decode(encrypted.encode()).decode()
    except:
        return ''


def _load_connections():
    """加载保存的数据库连接."""
    try:
        if os.path.exists(DB_CONFIG_FILE):
            with open(DB_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def _save_connections(conns):
    """保存数据库连接."""
    with open(DB_CONFIG_FILE, 'w') as f:
        json.dump(conns, f, indent=2)


def _run_mysql(conn, query, timeout=30):
    """执行 MySQL 命令."""
    cmd = [
        'mysql', '-h', conn['host'],
        '-P', str(conn['port']),
        '-u', conn['user'],
        '--ssl=0',
    ]
    if conn.get('password'):
        cmd.append(f"-p{conn['password']}")
    if conn.get('database'):
        cmd.extend(['-D', conn['database']])
    cmd.extend(['-e', query, '--batch', '--raw', '--skip-column-names'])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result
    except subprocess.TimeoutExpired:
        return None


@db_bp.route('/api/db/connections')
def api_db_connections():
    """获取保存的数据库连接列表."""
    conns = _load_connections()
    result = []
    for k, v in conns.items():
        # 不返回密码
        v_copy = v.copy()
        v_copy['id'] = k
        if 'password' in v_copy:
            del v_copy['password']
        result.append(v_copy)
    return api_ok({'connections': result})


@db_bp.route('/api/db/connect', methods=['POST'])
def api_db_connect():
    """保存数据库连接."""
    data = request.get_json(silent=True) or {}
    conn_id = data.get('id') or data.get('name', '')
    if not conn_id:
        conn_id = f"mysql_{data.get('host')}_{data.get('port')}"
    
    conns = _load_connections()
    conns[conn_id] = {
        'id': conn_id,
        'name': data.get('name', conn_id),
        'type': 'mysql',
        'host': data.get('host', ''),
        'port': data.get('port', '3306'),
        'user': data.get('user', ''),
        'password': _encrypt(data.get('password', '')),
        'database': data.get('database', ''),
        'created': datetime.now().isoformat()
    }
    
    _save_connections(conns)
    return api_ok({'id': conn_id})


@db_bp.route('/api/db/connection/<conn_id>', methods=['DELETE'])
def api_db_delete_connection(conn_id):
    """删除数据库连接."""
    conns = _load_connections()
    if conn_id in conns:
        del conns[conn_id]
        _save_connections(conns)
        return api_ok({'success': True})
    return api_error('连接不存在', status=404)


@db_bp.route('/api/db/test', methods=['POST'])
def api_db_test():
    """测试数据库连接."""
    data = request.get_json(silent=True) or {}
    conn = {
        'host': data.get('host', ''),
        'port': data.get('port', '3306'),
        'user': data.get('user', ''),
        'password': data.get('password', ''),
        'database': data.get('database', '')
    }
    
    result = _run_mysql(conn, 'SELECT 1', timeout=5)
    if result and result.returncode == 0:
        return api_ok({'success': True, 'message': 'Connected'})
    return api_error(result.stderr if result else 'Connection failed', status=400)


@db_bp.route('/api/db/<conn_id>/databases')
def api_db_databases(conn_id):
    """获取数据库列表."""
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    # 解密密码
    conn['password'] = _decrypt(conn.get('password', ''))
    
    result = _run_mysql(conn, 'SHOW DATABASES')
    if not result or result.returncode != 0:
        return api_error(result.stderr if result else 'Failed', status=400)
    
    dbs = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
    return api_ok({'databases': dbs})


@db_bp.route('/api/db/<conn_id>/tables')
def api_db_tables(conn_id):
    """获取指定数据库的表列表."""
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    conn['password'] = _decrypt(conn.get('password', ''))
    
    # 获取用户选择的数据库，优先使用请求参数，其次使用连接配置的默认库
    database = request.args.get('database') or conn.get('database')
    if not database:
        return api_error('请先选择数据库', status=400)
    
    conn['database'] = database
    
    result = _run_mysql(conn, 'SHOW TABLE STATUS')
    if not result or result.returncode != 0:
        return api_error(result.stderr if result else 'Failed', status=400)
    
    tables = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            parts = line.split('\t')
            if len(parts) >= 8:
                tables.append({
                    'name': parts[0],
                    'engine': parts[1] or '-',
                    'rows': parts[4] or '0',
                    'data_length': parts[6] or '0',
                    'index_length': parts[7] or '0',
                    'collation': parts[14] or '-',
                    'comment': parts[17] or ''
                })
    
    return api_ok({'tables': tables})


@db_bp.route('/api/db/<conn_id>/table/<table>/schema')
def api_db_table_schema(conn_id, table):
    """获取表结构."""
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    conn['password'] = _decrypt(conn.get('password', ''))
    conn['database'] = conn.get('database', '')
    
    # 获取列信息
    result = _run_mysql(conn, f'DESCRIBE `{table}`')
    if not result or result.returncode != 0:
        return api_error(result.stderr if result else 'Failed', status=400)
    
    columns = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            parts = line.split('\t')
            if len(parts) >= 6:
                columns.append({
                    'field': parts[0],
                    'type': parts[1],
                    'null': parts[2],
                    'key': parts[3] or '',
                    'default': parts[4] if parts[4] != 'NULL' else None,
                    'extra': parts[5] or ''
                })
    
    # 获取索引信息
    result = _run_mysql(conn, f'SHOW INDEX FROM `{table}`')
    indexes = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            parts = line.split('\t')
            if len(parts) >= 4:
                indexes.append({
                    'name': parts[2],
                    'unique': parts[1] == '0',
                    'columns': parts[3] or ''
                })
    
    return api_ok({'columns': columns, 'indexes': indexes})


@db_bp.route('/api/db/<conn_id>/table/<table>/data')
def api_db_table_data(conn_id, table):
    """获取表数据（分页）."""
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    conn['password'] = _decrypt(conn.get('password', ''))
    
    # 分页参数
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 100))
    offset = (page - 1) * page_size
    
    # 获取总数
    count_result = _run_mysql(conn, f'SELECT COUNT(*) FROM `{table}`')
    total = 0
    if count_result and count_result.returncode == 0:
        total = int(count_result.stdout.strip() or 0)
    
    # 获取数据
    query = f'SELECT * FROM `{table}` LIMIT {page_size} OFFSET {offset}'
    result = _run_mysql(conn, query)
    
    if not result or result.returncode != 0:
        return api_error(result.stderr if result else 'Failed', status=400)
    
    # 解析结果
    rows = []
    for line in result.stdout.strip().split('\n'):
        if line.strip():
            rows.append(line.split('\t'))
    
    # 获取列名
    schema_result = _run_mysql(conn, f'DESCRIBE `{table}`')
    headers = []
    if schema_result and schema_result.returncode == 0:
        for line in schema_result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.split('\t')
                headers.append(parts[0])
    
    return api_ok({
        'headers': headers,
        'rows': rows,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size
        }
    })


@db_bp.route('/api/db/execute', methods=['POST'])
def api_db_execute():
    """执行 SQL 查询."""
    data = request.get_json(silent=True) or {}
    conn_id = data.get('connection', '')
    query = data.get('query', '').strip()
    
    if not conn_id:
        return api_error('Missing connection', status=400)
    if not query:
        return api_error('Missing query', status=400)
    
    # 安全检查
    dangerous = ['DROP DATABASE', 'TRUNCATE TABLE', 'DROP TABLE', 'DELETE FROM']
    for d in dangerous:
        if query.upper().startswith(d):
            return api_error('Restricted operation', status=403)
    
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    conn['password'] = _decrypt(conn.get('password', ''))
    
    # 根据查询类型处理
    query_upper = query.upper().strip()
    
    if query_upper.startswith('SELECT') or query_upper.startswith('SHOW') or query_upper.startswith('DESCRIBE') or query_upper.startswith('EXPLAIN'):
        # 查询类型
        result = _run_mysql(conn, query, timeout=60)
        if not result or result.returncode != 0:
            return api_error(result.stderr if result else 'Query failed', status=400)
        
        headers = []
        rows = []
        
        for i, line in enumerate(result.stdout.strip().split('\n')):
            if line.strip():
                cells = line.split('\t')
                if i == 0:
                    headers = cells
                else:
                    rows.append(cells)
        
        return api_ok({
            'headers': headers,
            'rows': rows,
            'affected': len(rows)
        })
    
    elif query_upper.startswith('INSERT') or query_upper.startswith('UPDATE') or query_upper.startswith('DELETE'):
        # 修改类型
        result = _run_mysql(conn, query, timeout=60)
        if not result or result.returncode != 0:
            return api_error(result.stderr if result else 'Query failed', status=400)
        
        affected = 0
        for line in result.stderr.strip().split('\n'):
            if 'Changed' in line or 'Rows matched' in line:
                try:
                    affected = int(line.split(':')[1].strip())
                except:
                    pass
        
        return api_ok({
            'affected': affected,
            'message': 'Query executed successfully'
        })
    
    else:
        return api_error('Unsupported query type', status=400)


@db_bp.route('/api/db/<conn_id>/quick-actions', methods=['POST'])
def api_db_quick_action(conn_id):
    """快速操作（清空表、优化表等）."""
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    conn['password'] = _decrypt(conn.get('password', ''))
    
    data = request.get_json(silent=True) or {}
    action = data.get('action', '')
    table = data.get('table', '')
    
    if not action or not table:
        return api_error('Missing action or table', status=400)
    
    queries = {
        'truncate': f'TRUNCATE TABLE `{table}`',
        'optimize': f'OPTIMIZE TABLE `{table}`',
        'analyze': f'ANALYZE TABLE `{table}`',
        'repair': f'REPAIR TABLE `{table}`'
    }
    
    query = queries.get(action)
    if not query:
        return api_error('Unknown action', status=400)
    
    result = _run_mysql(conn, query, timeout=60)
    if result and result.returncode == 0:
        return api_ok({'message': f'{action} completed'})
    return api_error(result.stderr if result else 'Failed', status=400)


@db_bp.route('/api/db/<conn_id>/export', methods=['GET'])
def api_db_export(conn_id):
    """导出查询结果为 CSV."""
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('连接不存在', status=404)
    
    conn['password'] = _decrypt(conn.get('password', ''))
    query = request.args.get('query', '')
    
    if not query:
        return api_error('Missing query', status=400)
    
    result = _run_mysql(conn, query, timeout=60)
    if not result or result.returncode != 0:
        return api_error(result.stderr if result else 'Failed', status=400)
    
    from flask import Response
    output = result.stdout
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=export.csv'}
    )


# 用户会话状态存储
DB_STATE_FILE = os.path.join(DB_CONFIG_DIR, 'db_state.json')


def _load_state():
    """加载用户会话状态."""
    try:
        if os.path.exists(DB_STATE_FILE):
            with open(DB_STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}


def _save_state(state):
    """保存用户会话状态."""
    with open(DB_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


@db_bp.route('/api/db/state')
def api_db_get_state():
    """获取用户会话状态."""
    state = _load_state()
    # 不返回敏感信息
    return api_ok(state)


@db_bp.route('/api/db/state', methods=['POST'])
def api_db_save_state():
    """保存用户会话状态."""
    data = request.get_json(silent=True) or {}
    state = {
        'connId': data.get('connId'),
        'dbName': data.get('dbName'),
        'tableName': data.get('tableName'),
        'expandedDatabases': data.get('expandedDatabases', []),
        'lastSql': data.get('lastSql'),
        'sqlHistory': data.get('sqlHistory', []),
        'updated': datetime.now().isoformat()
    }
    _save_state(state)
    return api_ok({'success': True})


@db_bp.route('/api/db/state', methods=['DELETE'])
def api_db_clear_state():
    """清除用户会话状态."""
    if os.path.exists(DB_STATE_FILE):
        os.remove(DB_STATE_FILE)
    return api_ok({'success': True})
