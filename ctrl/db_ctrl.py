#!/usr/bin/env python3
"""Database management API (MySQL/MariaDB, Redis, PostgreSQL)."""

import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify

from ctrl import api_error, api_ok

db_bp = Blueprint('db', __name__)

# 数据库连接配置存储路径
DB_CONFIG_DIR = os.path.expanduser('~/.local/share/clawos')
os.makedirs(DB_CONFIG_DIR, exist_ok=True)
DB_CONFIG_FILE = os.path.join(DB_CONFIG_DIR, 'db_connections.json')


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
        json.dump(conns, f)


@db_bp.route('/api/db/connections')
def api_db_connections():
    """获取保存的数据库连接列表."""
    conns = _load_connections()
    return api_ok({'connections': list(conns.values())})


@db_bp.route('/api/db/test', methods=['POST'])
def api_db_test():
    """测试数据库连接."""
    data = request.get_json(silent=True) or {}
    db_type = data.get('type', '')
    host = data.get('host', '')
    port = data.get('port', '')
    user = data.get('user', '')
    password = data.get('password', '')
    database = data.get('database', '')
    
    import subprocess
    
    if db_type == 'mysql':
        cmd = ['mysql', '-h', host, '-P', str(port), '-u', user, f'-p{password}', '-e', 'SELECT 1;']
        if database:
            cmd.extend(['-D', database])
    elif db_type == 'redis':
        cmd = ['redis-cli', '-h', host, '-p', str(port), '-a', password, 'PING']
    elif db_type == 'postgresql':
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        cmd = ['psql', '-h', host, '-p', str(port), '-U', user, '-c', 'SELECT 1;']
        if database:
            cmd.extend(['-d', database])
    else:
        return api_error('Unsupported database type', status=400)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        connected = result.returncode == 0
        return api_ok({'success': connected, 'message': 'Connected' if connected else result.stderr[:200]})
    except Exception as e:
        return api_error(str(e), status=500)


@db_bp.route('/api/db/connect', methods=['POST'])
def api_db_connect():
    """保存数据库连接."""
    data = request.get_json(silent=True) or {}
    conns = _load_connections()
    
    conn_id = data.get('id') or data.get('name', '')
    if not conn_id:
        conn_id = f"{data.get('type')}_{data.get('host')}_{data.get('port')}"
    
    conns[conn_id] = {
        'id': conn_id,
        'name': data.get('name', conn_id),
        'type': data.get('type', ''),
        'host': data.get('host', ''),
        'port': data.get('port', ''),
        'user': data.get('user', ''),
        'password': data.get('password', ''),
        'database': data.get('database', ''),
        'created': datetime.now().isoformat()
    }
    
    _save_connections(conns)
    return api_ok({'id': conn_id})


@db_bp.route('/api/db/execute', methods=['POST'])
def api_db_execute():
    """执行数据库查询."""
    data = request.get_json(silent=True) or {}
    conn_id = data.get('connection', '')
    query = data.get('query', '').strip()
    
    if not conn_id:
        return api_error('Missing connection', status=400)
    if not query:
        return api_error('Missing query', status=400)
    
    conns = _load_connections()
    conn = conns.get(conn_id)
    if not conn:
        return api_error('Connection not found', status=404)
    
    import subprocess
    
    try:
        if conn['type'] == 'mysql':
            cmd = ['mysql', '-h', conn['host'], '-P', str(conn['port']), 
                   '-u', conn['user'], f"-p{conn['password']}", '-e', query]
            if conn.get('database'):
                cmd.extend(['-D', conn['database']])
        elif conn['type'] == 'redis':
            cmd = ['redis-cli', '-h', conn['host'], '-p', str(conn['port'])]
            if conn.get('password'):
                cmd.extend(['-a', conn['password']])
            cmd.extend(['--raw', query])
        else:
            return api_error('Unsupported type', status=400)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # 解析结果
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode != 0:
            return api_error(error or 'Query failed', status=400)
        
        # 简单表格化输出
        rows = []
        if conn['type'] == 'mysql':
            lines = output.split('\n')
            if len(lines) >= 2:
                headers = lines[0].split('\t')
                for line in lines[1:]:
                    if line.strip():
                        rows.append(line.split('\t'))
        elif conn['type'] == 'redis':
            rows = [[output]] if output else []
        
        return api_ok({
            'success': True,
            'headers': headers if 'headers' in dir() else [],
            'rows': rows[:100],  # 限制100行
            'affected': result.returncode
        })
        
    except Exception as e:
        return api_error(str(e), status=500)


@db_bp.route('/api/db/redis/info')
def api_db_redis_info():
    """获取 Redis 服务器信息."""
    data = request.args
    host = data.get('host', 'localhost')
    port = data.get('port', '6379')
    password = data.get('password', '')
    
    import subprocess
    
    cmd = ['redis-cli', '-h', host, '-p', port]
    if password:
        cmd.extend(['-a', password])
    cmd.extend(['INFO', 'server,clients,memory,stats'])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return api_error(result.stderr or 'Connection failed', status=400)
        
        info = {}
        for line in result.stdout.split('\n'):
            if ':' in line and not line.startswith('#'):
                k, v = line.split(':', 1)
                info[k.strip()] = v.strip()
        
        return api_ok({'info': info})
        
    except Exception as e:
        return api_error(str(e), status=500)


@db_bp.route('/api/db/mysql/status')
def api_db_mysql_status():
    """获取 MySQL 状态信息."""
    data = request.args
    host = data.get('host', 'localhost')
    port = data.get('port', '3306')
    user = data.get('user', 'root')
    password = data.get('password', '')
    database = data.get('database', '')
    
    import subprocess
    
    cmd = ['mysql', '-h', host, '-P', str(port), '-u', user, f"-p{password}", 
           '-e', 'SHOW STATUS; SHOW DATABASES;']
    if database:
        cmd = ['mysql', '-h', host, '-P', str(port), '-u', user, f"-p{password}", 
               '-D', database, '-e', 'SHOW TABLES;']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return api_error(result.stderr or 'Connection failed', status=400)
        
        return api_ok({'output': result.stdout[:5000]})
    except Exception as e:
        return api_error(str(e), status=500)
