#!/usr/bin/env python3
"""Enhanced Database management API using SQLAlchemy."""

import os
import json
import base64
from datetime import datetime
from contextlib import contextmanager
from threading import Lock
from flask import Blueprint, request, jsonify

from ctrl import api_error, api_ok

db_bp = Blueprint('db', __name__)

# 数据库连接配置存储路径
DB_CONFIG_DIR = os.path.expanduser('~/.local/share/clawos')
os.makedirs(DB_CONFIG_DIR, exist_ok=True)
DB_CONFIG_FILE = os.path.join(DB_CONFIG_DIR, 'db_connections.json')

# 加密密钥
ENCRYPTION_KEY = os.environ.get('DB_ENCRYPTION_KEY', 'clawos-db-secret-key-32chars!')[:32]

# SQLAlchemy 引擎缓存
_engines = {}
_engines_lock = Lock()


def _encrypt(text):
    """简单加密."""
    if not text:
        return ''
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


def _get_engine(conn):
    """获取或创建数据库引擎 (带缓存)."""
    conn_id = conn.get('id') or f"{conn['host']}:{conn['port']}"
    
    with _engines_lock:
        # 检查缓存的引擎是否仍然有效
        if conn_id in _engines:
            engine, cached_conn = _engines[conn_id]
            # 检查连接参数是否变化
            if (cached_conn.get('host') == conn.get('host') and
                cached_conn.get('port') == conn.get('port') and
                cached_conn.get('user') == conn.get('user') and
                cached_conn.get('database') == conn.get('database')):
                return engine
        
        # 创建新引擎
        from sqlalchemy import create_engine
        
        # 构建连接 URL
        password = _decrypt(conn.get('password', '')) if conn.get('password') else ''
        database = conn.get('database', '')
        
        # MySQL URL
        url = f"mysql+pymysql://{conn['user']}:{password}@{conn['host']}:{conn['port']}"
        if database:
            url += f"/{database}"
        
        # 创建引擎，设置池参数
        engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            echo=False
        )
        
        _engines[conn_id] = (engine, conn.copy())
        return engine


@contextmanager
def _get_connection(conn):
    """获取数据库连接上下文."""
    engine = _get_engine(conn)
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()


@db_bp.route('/api/db/connections')
def api_db_connections():
    """获取保存的数据库连接列表."""
    conns = _load_connections()
    result = []
    for k, v in conns.items():
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
        return api_error('Missing connection id or name')
    
    # 加密密码
    password = data.get('password', '')
    encrypted_password = _encrypt(password) if password else ''
    
    conn = {
        'name': data.get('name', ''),
        'host': data.get('host', 'localhost'),
        'port': int(data.get('port', 3306)),
        'user': data.get('user', 'root'),
        'password': encrypted_password,
        'database': data.get('database', ''),
        'charset': data.get('charset', 'utf8mb4'),
        'created_at': datetime.now().isoformat(),
    }
    
    conns = _load_connections()
    conns[conn_id] = conn
    _save_connections(conns)
    
    # 清除旧引擎缓存
    with _engines_lock:
        if conn_id in _engines:
            try:
                _engines[conn_id][0].dispose()
            except:
                pass
            del _engines[conn_id]
    
    return api_ok({'id': conn_id, **conn})


@db_bp.route('/api/db/test', methods=['POST'])
def api_db_test():
    """测试数据库连接."""
    data = request.get_json(silent=True) or {}
    engine_type = data.get('engine', 'mysql')
    
    # 构建临时连接数据
    conn = {
        'host': data.get('host', ''),
        'port': str(data.get('port', 3306)),
        'user': data.get('user', ''),
        'password': data.get('password', ''),
        'database': data.get('database', ''),
    }
    
    # SQLite 特殊处理
    if engine_type == 'sqlite':
        conn['host'] = ''
        conn['user'] = ''
        conn['password'] = ''
        conn['database'] = data.get('database', '')
    
    try:
        from sqlalchemy import create_engine, text
        
        if engine_type == 'sqlite':
            url = f"sqlite:///{conn['database']}"
        else:
            password = conn['password']
            user = conn['user']
            host = conn['host']
            port = conn['port']
            database = conn['database']
            
            url_map = {
                'mysql': f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
                'postgresql': f'postgresql://{user}:{password}@{host}:{port}/{database}',
                'mariadb': f'mariadb+pymysql://{user}:{password}@{host}:{port}/{database}',
                'oracle': f'oracle://{user}:{password}@{host}:{port}/{database}',
                'mssql': f'mssql+pymysql://{user}:{password}@{host}:{port}/{database}',
                'firebird': f'firebird://{user}:{password}@{host}:{port}/{database}',
                'sybase': f'sybase://{user}:{password}@{host}:{port}/{database}',
            }
            url = url_map.get(engine_type, url_map['mysql'])
        
        engine = create_engine(url, echo=False, timeout=10)
        with engine.connect() as c:
            c.execute(text('SELECT 1'))
        engine.dispose()
        
        return api_ok({'message': '连接成功'})
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/connection/<conn_id>', methods=['PUT'])
def api_db_update_connection(conn_id):
    """更新数据库连接."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    data = request.get_json(silent=True) or {}
    old_conn = conns[conn_id]
    
    # 保留原密码（如果未提供新密码）
    password = data.get('password', '')
    encrypted_password = password if password else old_conn.get('password', '')
    
    conn = {
        'name': data.get('name', old_conn.get('name', '')),
        'engine': data.get('engine', old_conn.get('engine', 'mysql')),
        'host': data.get('host', old_conn.get('host', '')),
        'port': int(data.get('port', old_conn.get('port', 3306))),
        'user': data.get('user', old_conn.get('user', '')),
        'password': encrypted_password,
        'database': data.get('database', old_conn.get('database', '')),
        'created_at': old_conn.get('created_at', datetime.now().isoformat()),
    }
    
    conns[conn_id] = conn
    _save_connections(conns)
    
    # 清除旧引擎缓存
    with _engines_lock:
        if conn_id in _engines:
            try:
                _engines[conn_id][0].dispose()
            except:
                pass
            del _engines[conn_id]
    
    return api_ok({'id': conn_id, **conn})


@db_bp.route('/api/db/connection/<conn_id>/password')
def api_db_get_password(conn_id):
    """获取连接密码（解密后）."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    password = _decrypt(conn.get('password', '')) if conn.get('password') else ''
    
    return api_ok({'password': password})


@db_bp.route('/api/db/connections/<conn_id>', methods=['DELETE'])
def api_db_delete_connection(conn_id):
    """删除数据库连接."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    del conns[conn_id]
    _save_connections(conns)
    
    # 清除引擎缓存
    with _engines_lock:
        if conn_id in _engines:
            try:
                _engines[conn_id][0].dispose()
            except:
                pass
            del _engines[conn_id]
    
    return api_ok({'deleted': conn_id})


@db_bp.route('/api/db/<conn_id>/tables')
def api_db_tables(conn_id):
    """获取数据库表列表."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import inspect
        engine = _get_engine(conn)
        inspector = inspect(engine)
        tables = []
        for t in inspector.get_table_names():
            tables.append({'name': t})
        return api_ok({'tables': tables})
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/<conn_id>/table/<table>/schema')
def api_db_table_schema(conn_id, table):
    """获取表结构."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import inspect
        engine = _get_engine(conn)
        inspector = inspect(engine)
        
        # 列信息
        columns = []
        for c in inspector.get_columns(table):
            columns.append({
                'field': c['name'],
                'type': str(c['type']),
                'null': 'YES' if c['nullable'] else 'NO',
                'key': c.get('primary_key', '') or '',
                'default': str(c.get('default', '')) if c.get('default') else ''
            })
        
        # 索引信息
        indexes = []
        for idx in inspector.get_indexes(table):
            indexes.append({
                'name': idx['name'],
                'columns': ', '.join(idx['column_names']),
                'unique': idx.get('unique', False)
            })
        
        return api_ok({'columns': columns, 'indexes': indexes})
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/<conn_id>/table/<table>/count')
def api_db_table_count(conn_id, table):
    """获取表行数."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import text
        with _get_connection(conn) as c:
            result = c.execute(text(f'SELECT COUNT(*) FROM `{table}`'))
            count = result.scalar()
        return api_ok({'count': count})
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/<conn_id>/describe/<table>')
def api_db_describe(conn_id, table):
    """DESCRIBE table."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import text
        with _get_connection(conn) as c:
            result = c.execute(text(f'DESCRIBE `{table}`'))
            rows = [dict(row._mapping) for row in result.fetchall()]
        return api_ok({'rows': rows})
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/<conn_id>/primary-key/<table>')
def api_db_primary_key(conn_id, table):
    """获取表主键."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import inspect
        engine = _get_engine(conn)
        inspector = inspect(engine)
        pk = inspector.get_pk_constraint(table)
        return api_ok({'primary_key': pk})
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/execute', methods=['POST'])
def api_db_execute():
    """执行 SQL 查询."""
    data = request.get_json(silent=True) or {}
    conn_id = data.get('connection')
    query = data.get('query', '')
    
    if not conn_id:
        return api_error('Missing connection id')
    if not query:
        return api_error('Missing query')
    
    # 限制返回行数
    if not query.strip().lower().startswith('select'):
        return api_error('Only SELECT queries are allowed')
    
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import text
        with _get_connection(conn) as c:
            # 执行查询
            result = c.execute(text(query))
            
            # 获取列名
            if result.returns_rows:
                rows = [dict(row._mapping) for row in result.fetchall()]
                # 限制返回行数
                MAX_ROWS = 10000
                if len(rows) > MAX_ROWS:
                    rows = rows[:MAX_ROWS]
                headers = list(rows[0].keys()) if rows else []
                return api_ok({'headers': headers, 'rows': [[row.get(h, '') for h in headers] for row in rows]})
            else:
                # INSERT/UPDATE/DELETE
                c.commit()
                return api_ok({'affected': result.rowcount})
                
    except Exception as e:
        return api_error(str(e))


@db_bp.route('/api/db/state', methods=['GET', 'POST', 'DELETE'])
def api_db_state():
    """获取/保存/清除数据库状态."""
    if request.method == 'DELETE':
        return api_ok({'deleted': True})
    
    conns = _load_connections()
    
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        for conn_id, state in data.items():
            if conn_id in conns:
                # 更新连接配置中的状态
                conns[conn_id]['state'] = state
        _save_connections(conns)
        return api_ok({'saved': True})
    
    # GET
    state = {}
    for conn_id, conn in conns.items():
        if 'state' in conn:
            state[conn_id] = conn['state']
    return api_ok(state)


@db_bp.route('/api/db/<conn_id>/databases')
def api_db_databases(conn_id):
    """获取数据库列表 (SHOW DATABASES)."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import text
        with _get_connection(conn) as c:
            result = c.execute(text('SHOW DATABASES'))
            dbs = [row[0] for row in result.fetchall()]
        return api_ok({'databases': dbs})
    except Exception as e:
        return api_error(str(e))
