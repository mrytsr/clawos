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
DB_CONFIG_DIR = os.path.expanduser('~/.local/clawos')
os.makedirs(DB_CONFIG_DIR, exist_ok=True)
DB_CONFIG_FILE = os.path.join(DB_CONFIG_DIR, 'db_connections.json')
UI_STATE_KEY = '__ui_state__'

# 迁移旧数据
OLD_CONFIG_DIR = os.path.expanduser('~/.local/share/clawos')
if os.path.exists(OLD_CONFIG_DIR) and not os.path.exists(DB_CONFIG_FILE):
    OLD_FILE = os.path.join(OLD_CONFIG_DIR, 'db_connections.json')
    if os.path.exists(OLD_FILE):
        import shutil
        shutil.copy(OLD_FILE, DB_CONFIG_FILE)

# 加密密钥
ENCRYPTION_KEY = os.environ.get('DB_ENCRYPTION_KEY', 'clawos-db-secret-key-32chars!')[:32]

# SQLAlchemy 引擎缓存
_engines = {}
_engines_lock = Lock()




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

def _is_meta_key(k):
    return isinstance(k, str) and k.startswith('__')


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
        password = conn.get('password', '')
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
        if _is_meta_key(k):
            continue
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
    password = password if password else ''
    
    conn = {
        'name': data.get('name', ''),
        'host': data.get('host', 'localhost'),
        'port': int(data.get('port', 3306)),
        'user': data.get('user', 'root'),
        'password': password,
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
    
    # 如果提供了conn_id，使用已保存的连接信息
    conn_id = data.get('conn_id')
    saved_conn = None
    if conn_id:
        conns = _load_connections()
        saved_conn = conns.get(conn_id)
    
    # 构建临时连接数据，优先使用传入值，否则用已保存的值
    conn = {
        'host': data.get('host', '') or (saved_conn.get('host') if saved_conn else ''),
        'port': str(data.get('port', 3306)) or str(saved_conn.get('port', 3306)) if saved_conn else '3306',
        'user': data.get('user', '') or (saved_conn.get('user') if saved_conn else ''),
        'password': data.get('password', '') or (saved_conn.get('password', '') if saved_conn else ''),
        'database': data.get('database', '') or (saved_conn.get('database') if saved_conn else ''),
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
        
        connect_args = {"connect_timeout": 10} if engine_type != "sqlite" else {}
        engine = create_engine(url, echo=False, connect_args=connect_args)
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
    password = password if password else old_conn.get('password', '')
    
    conn = {
        'name': data.get('name', old_conn.get('name', '')),
        'engine': data.get('engine', old_conn.get('engine', 'mysql')),
        'host': data.get('host', old_conn.get('host', '')),
        'port': int(data.get('port', old_conn.get('port', 3306))),
        'user': data.get('user', old_conn.get('user', '')),
        'password': password,
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
    password = conn.get('password', '')
    
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


@db_bp.route('/api/db/<conn_id>/databases/<db>/tables')
def api_db_tables_by_db(conn_id, db):
    """获取指定数据库的表列表."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id].copy()
    conn['database'] = db  # 切换到指定数据库
    
    try:
        from sqlalchemy import create_engine, text, inspect
        from sqlalchemy.engine.url import make_url
        
        password = conn.get('password', '')
        url = f"mysql+pymysql://{conn['user']}:{password}@{conn['host']}:{conn['port']}/{db}"
        engine = create_engine(url, echo=False)
        inspector = inspect(engine)
        tables = []
        for t in inspector.get_table_names():
            tables.append({'name': t})
        engine.dispose()
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
    
    # 允许 SELECT, SHOW, DESCRIBE, EXPLAIN, INSERT, UPDATE, DELETE 查询
    query_lower = query.strip().lower()
    allowed_prefixes = ('select', 'show', 'describe', 'explain', 'insert', 'update', 'delete')
    if not any(query_lower.startswith(p) for p in allowed_prefixes):
        return api_error('Only SELECT/SHOW/DESCRIBE/INSERT/UPDATE/DELETE queries are allowed')
    
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
            if conn_id in conns and not _is_meta_key(conn_id):
                # 更新连接配置中的状态
                conns[conn_id]['state'] = state
        _save_connections(conns)
        return api_ok({'saved': True})
    
    # GET
    state = {}
    for conn_id, conn in conns.items():
        if _is_meta_key(conn_id):
            continue
        if 'state' in conn:
            state[conn_id] = conn['state']
    return api_ok(state)

@db_bp.route('/api/db/ui-state', methods=['GET', 'POST', 'DELETE'])
def api_db_ui_state():
    if request.method == 'DELETE':
        conns = _load_connections()
        if UI_STATE_KEY in conns:
            del conns[UI_STATE_KEY]
            _save_connections(conns)
        return api_ok({'deleted': True})

    conns = _load_connections()
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return api_error('Invalid payload')

        prev = conns.get(UI_STATE_KEY) if isinstance(conns.get(UI_STATE_KEY), dict) else {}
        merged = dict(prev)
        allow = {
            'conn_id': str,
            'db': str,
            'table': str,
            'sql': str,
            'sql_open': bool,
            'tab': str,
            'ai_prompt': str,
        }
        for k, t in allow.items():
            if k not in data:
                continue
            v = data.get(k)
            if t is bool:
                merged[k] = bool(v)
            elif isinstance(v, str):
                merged[k] = v
            else:
                merged[k] = ''

        if isinstance(merged.get('sql'), str) and len(merged['sql']) > 20000:
            merged['sql'] = merged['sql'][:20000]
        merged['updated_at'] = datetime.utcnow().isoformat(timespec='seconds') + 'Z'

        conns[UI_STATE_KEY] = merged
        _save_connections(conns)
        return api_ok({'saved': True, 'state': merged})

    state = conns.get(UI_STATE_KEY) if isinstance(conns.get(UI_STATE_KEY), dict) else {}
    return api_ok(state)


@db_bp.route('/api/db/tree')
def api_db_tree():
    """获取完整的数据库树结构."""
    conns = _load_connections()
    result = []
    
    for conn_id, conn in conns.items():
        if _is_meta_key(conn_id):
            continue
        try:
            from sqlalchemy import create_engine, text, inspect
            from sqlalchemy.engine.url import make_url
            
            # 构建引擎 URL
            password = conn.get('password', '')
            
            if conn.get('engine') == 'sqlite':
                url = f"sqlite:///{conn.get('database', '')}"
            else:
                url = f"mysql+pymysql://{conn['user']}:{password}@{conn['host']}:{conn['port']}/{conn.get('database', '')}"
            
            engine = create_engine(url, echo=False)
            
            # 获取数据库列表
            try:
                with engine.connect() as c:
                    db_result = c.execute(text('SHOW DATABASES'))
                    databases = [row[0] for row in db_result.fetchall()]
            except:
                databases = [conn.get('database', '')] if conn.get('database') else []
            
            # 构建树节点
            conn_node = {
                'id': conn_id,
                'name': conn.get('name', conn_id),
                'engine': conn.get('engine', 'mysql'),
                'database': conn.get('database', ''),
                'children': []
            }
            
            # 获取每个数据库的表
            for db in databases:
                try:
                    db_url = f"mysql+pymysql://{conn['user']}:{password}@{conn['host']}:{conn['port']}/{db}"
                    db_engine = create_engine(db_url, echo=False)
                    inspector = inspect(db_engine)
                    tables = [{'name': t} for t in inspector.get_table_names()]
                    conn_node['children'].append({
                        'name': db,
                        'children': tables
                    })
                    db_engine.dispose()
                except:
                    continue
            
            engine.dispose()
            result.append(conn_node)
            
        except Exception as e:
            # 连接失败时返回基本信息
            result.append({
                'id': conn_id,
                'name': conn.get('name', conn_id),
                'engine': conn.get('engine', 'mysql'),
                'database': conn.get('database', ''),
                'children': [],
                'error': str(e)
            })
    
    return api_ok(result)


@db_bp.route('/api/db/<conn_id>/table/<table>/columns')
def api_db_table_columns(conn_id, table):
    """获取表的字段列表（用于SQL自动补全）."""
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import text
        with _get_connection(conn) as c:
            result = c.execute(text(f'DESCRIBE `{table}`'))
            columns = []
            for row in result.fetchall():
                columns.append(row[0])  # 字段名
        return api_ok({'columns': columns})
    except Exception as e:
        return api_error(str(e))


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


AI_HISTORY_FILE = os.path.expanduser('~/.local/clawos/ai_sql_history.json')


def _load_ai_history(limit=10):
    """加载 AI SQL 生成历史."""
    try:
        if os.path.exists(AI_HISTORY_FILE):
            with open(AI_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                return history[-limit:]
    except Exception:
        pass
    return []


def _save_ai_history(prompt, sql):
    """保存到历史."""
    try:
        history = []
        if os.path.exists(AI_HISTORY_FILE):
            with open(AI_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        history.append({'prompt': prompt, 'sql': sql, 'time': datetime.utcnow().isoformat()})
        history = history[-50:]  # 只保留最近 50 条
        with open(AI_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@db_bp.route('/db/ai-history')
def api_ai_history():
    """获取 AI SQL 生成历史."""
    history = _load_ai_history(limit=10)
    return api_ok({'history': history})


@db_bp.route('/db/ai-generate-sql', methods=['POST'])
def ai_generate_sql():
    """AI 生成 SQL."""
    import re
    import json

    data = request.json
    prompt = data.get('prompt', '').strip()
    current_sql = data.get('current_sql', '').strip()
    connection = data.get('connection', {})
    table = data.get('table', '')
    schema = data.get('schema', [])

    if not prompt:
        return api_error('请输入 prompt')

    # 获取数据库下所有表（用于关联查询）
    all_tables_schema = {}
    if connection.get('id'):
        try:
            conns = _load_connections()
            conn = conns.get(connection['id'])
            if conn:
                from sqlalchemy import text
                with _get_connection(conn) as c:
                    # 获取所有表名
                    result = c.execute(text('SHOW TABLES'))
                    tables = [list(row)[0] for row in result.fetchall()]
                    for t in tables[:30]:  # 限制最多 30 个表
                        try:
                            cols = c.execute(text(f'DESCRIBE `{t}`'))
                            cols_data = []
                            for row in cols.fetchall():
                                cols_data.append({'name': row[0], 'type': str(row[1])})
                            all_tables_schema[t] = cols_data
                        except Exception:
                            pass
        except Exception:
            pass

    # 获取历史记录
    history = _load_ai_history(limit=5)

    # 构建系统 prompt
    engine = connection.get('engine', 'mysql')
    database = connection.get('database', '')

    system_prompt = f"""你是一个 SQL 专家。根据用户的自然语言需求，生成或修改 SQL 查询。

数据库信息:
- 引擎: {engine}
- 数据库: {database}
"""

    # 所有表结构（用于关联查询）
    if all_tables_schema:
        system_prompt += f"\n数据库中的表结构:\n{json.dumps(all_tables_schema, ensure_ascii=False)}\n"

    # 当前表结构
    if table and schema:
        system_prompt += f"\n当前选中表 '{table}' 的详细结构:\n{json.dumps(schema, ensure_ascii=False)}\n"

    # 当前 SQL
    if current_sql:
        system_prompt += f"\n当前 SQL: {current_sql}\n"

    # 历史记录
    if history:
        system_prompt += "\n最近的操作历史:\n"
        for i, h in enumerate(history):
            system_prompt += f"{i+1}. 用户: {h.get('prompt', '')} -> SQL: {h.get('sql', '')}\n"

    system_prompt += """
要求:
1. 只返回 SQL 语句，不要解释
2. 根据需求选择合适的表，如果需要关联多个表，请使用 JOIN
3. 如果需求与当前 SQL 相关，在当前 SQL 基础上修改
4. SQL 要语法正确，可直接执行
"""

    try:
        from lib.ai_client import AiClient
        client = AiClient('deepseek:deepseek-chat')
        response = client.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])

        generated_sql = response.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

        # 清理 markdown 代码块
        generated_sql = re.sub(r'^```sql?\n', '', generated_sql)
        generated_sql = re.sub(r'\n```$', '', generated_sql)
        generated_sql = generated_sql.strip()

        # 保存到历史
        _save_ai_history(prompt, generated_sql)

        return jsonify({'success': True, 'sql': generated_sql})

    except Exception as e:
        return api_error(f'AI 生成失败: {str(e)}')


@db_bp.route('/api/db/schema', methods=['POST'])
def api_db_schema():
    """获取表结构（用于 AI 生成 SQL）."""
    data = request.json
    conn_id = data.get('connection')
    table = data.get('table')
    
    if not conn_id or not table:
        return api_error('缺少 connection 或 table 参数')
    
    conns = _load_connections()
    if conn_id not in conns:
        return api_error('Connection not found')
    
    conn = conns[conn_id]
    
    try:
        from sqlalchemy import text
        with _get_connection(conn) as c:
            result = c.execute(text(f'DESCRIBE `{table}`'))
            columns = []
            for row in result.fetchall():
                columns.append({
                    'name': row[0],
                    'type': str(row[1]),
                    'nullable': row[2] == 'YES',
                    'key': row[3] == 'PRI',
                    'default': row[4],
                    'extra': row[5]
                })
        return api_ok({'schema': columns})
    except Exception as e:
        return api_error(str(e))
