#!/usr/bin/env python3
"""System log viewer API."""

import os
import subprocess
import re
from datetime import datetime
from flask import Blueprint, request, jsonify

from ctrl import api_error, api_ok

log_bp = Blueprint('log', __name__)

SERVICES = [
    'frpc', 'clash', 'openclaw-gateway', 
    'clawos', 'docker', 'nginx'
]

def _parse_journal_line(line):
    """解析 journalctl 输出行."""
    parts = line.split(None, 2)  # 时间、优先级、消息
    if len(parts) >= 3:
        timestamp, priority, message = parts
        return {
            'timestamp': timestamp,
            'priority': priority,
            'message': message,
            'is_audit': line.startswith('audit')
        }
    return {'raw': line}


@log_bp.route('/api/log/services')
def api_log_services():
    """获取可用日志服务列表."""
    services = []
    for svc in SERVICES:
        result = subprocess.run(
            ['systemctl', '--user', 'status', svc + '.service'],
            capture_output=True, text=True, timeout=5
        )
        services.append({
            'name': svc,
            'installed': result.returncode != 4  # 4 = no such service
        })
    return api_ok({'services': services})


@log_bp.route('/api/log/journal')
def api_log_journal():
    """获取 journalctl 日志."""
    service = request.args.get('service', '')
    lines = int(request.args.get('lines', '100'))
    level = request.args.get('level', '')
    keyword = request.args.get('keyword', '')
    scope = request.args.get('scope', 'user')  # user 或 system
    
    cmd = ['journalctl']
    if scope == 'user':
        cmd.append('--user')
    cmd.extend(['-n', str(lines), '-o', 'short'])
    
    if service:
        # 去掉可能已经存在的 .service 后缀
        svc = service[:-8] if service.endswith('.service') else service
        cmd.extend(['-u', svc + '.service'])
    
    if level:
        cmd.extend(['-p', level])
    
    if keyword:
        cmd.extend(['-g', keyword])
    
    try:
        # system 级别使用 sg 切换到 systemd-journal 组
        if scope == 'system':
            cmd_str = 'sg systemd-journal "journalctl -n {} -o short'.format(lines)
            if service:
                cmd_str += ' -u {}.service'.format(svc)
            if level:
                cmd_str += ' -p {}'.format(level)
            if keyword:
                cmd_str += ' -g {}'.format(keyword)
            cmd_str += '"'
            result = subprocess.run(cmd_str, capture_output=True, text=True, timeout=10, shell=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        logs = []
        for line in result.stdout.strip().split('\n')[-lines:]:
            line = line.strip()
            if not line:
                continue
            
            # 解析时间戳
            time_match = re.match(r'([A-Z][a-z]\s+\d+\s+\d+:\d+:\d+)', line)
            time_str = time_match.group(1) if time_match else ''
            
            # 解析优先级
            priority = 'INFO'
            if 'ERR' in line or 'ERROR' in line:
                priority = 'ERR'
            elif 'WARN' in line:
                priority = 'WARN'
            elif 'CRIT' in line or 'FATAL' in line:
                priority = 'CRIT'
            elif 'DEBUG' in line:
                priority = 'DEBUG'
            
            # 提取消息内容
            msg = line
            for prefix in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRIT', 'audit']:
                if line.startswith(prefix):
                    msg = line[len(prefix):].strip()
                    break
            
            logs.append({
                'timestamp': time_str,
                'priority': priority,
                'message': msg[:500],  # 限制长度
                'raw': line[:200]
            })
        
        return api_ok({'logs': logs})
        
    except subprocess.TimeoutExpired:
        return api_error('日志查询超时', status=408)
    except Exception as e:
        return api_error(str(e), status=500)


@log_bp.route('/api/log/tail')
def api_log_tail():
    """实时日志流 (WebSocket)."""
    service = request.args.get('service', '')
    cmd = ['journalctl', '--user', '-f', '-n', '50', '-o', 'short', '--no-pager']
    
    if service:
        cmd.extend(['-u', service + '.service'])
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return api_ok({'pid': proc.pid})
    except Exception as e:
        return api_error(str(e), status=500)


@log_bp.route('/api/log/file')
def api_log_file():
    """读取日志文件."""
    path = request.args.get('path', '')
    
    if not path:
        return api_error('Missing path')
    
    # 安全检查
    log_dirs = ['/var/log', os.path.expanduser('~/.local/share')]
    if not any(path.startswith(d) for d in log_dirs):
        return api_error('Path not allowed', status=403)
    
    try:
        if not os.path.exists(path):
            return api_error('File not found', status=404)
        
        lines = int(request.args.get('lines', '200'))
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            content = ''.join(all_lines[-lines:])
        
        return api_ok({'content': content, 'path': path})
    except Exception as e:
        return api_error(str(e), status=500)
