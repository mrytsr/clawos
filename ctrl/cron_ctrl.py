#!/usr/bin/env python3
"""Cron job management API."""

import os
import subprocess
import re
import threading
from flask import Blueprint, request, jsonify, current_app, send_from_directory

from ctrl import api_error, api_ok

cron_bp = Blueprint('cron', __name__)
_cron_lock = threading.Lock()

@cron_bp.route('/cron/manager')
def cron_manager():
    return send_from_directory(current_app.template_folder, 'cron_manager.html')


def _parse_crontab(content):
    """解析 crontab 内容."""
    jobs = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # 检查是否以 # 开头（被注释的 cron 行）
        # 但要注意：#0 7 * * * 这种格式不是注释，# 是 minute=0 的一部分
        # 只有当 # 后面不是数字时才是注释
        is_comment = line.startswith('#') and not (len(line) > 1 and line[1].isdigit())
        is_enabled = not is_comment
        # 去掉开头的 # 用于后续解析（仅当 # 是注释时）
        clean_line = line[1:].strip() if is_comment and not line[1:1].isdigit() else line
        
        # 解析: 分 时 日 月 周 命令
        parts = clean_line.split(None, 5)
        if len(parts) >= 6:
            minute, hour, day, month, weekday, command = parts[:6]
            
            jobs.append({
                'raw': line,
                'minute': minute,
                'hour': hour,
                'day': day,
                'month': month,
                'weekday': weekday,
                'command': command[:100],
                'enabled': is_enabled
            })
        elif len(parts) >= 1 and clean_line.startswith('@'):
            # 特殊表达式: @reboot, @hourly, @daily, @weekly, @monthly, @yearly
            jobs.append({
                'raw': line,
                'minute': '',
                'hour': '',
                'day': '',
                'month': '',
                'weekday': '',
                'command': line,
                'enabled': not line.startswith('#')
            })
    
    return jobs


@cron_bp.route('/api/cron/list')
def api_cron_list():
    """获取用户 crontab 列表."""
    import time
    
    # 简单的缓存（进程内）
    cache_key = '_cron_list_cache'
    cache_time_key = '_cron_list_cache_time'
    
    # 使用 Blueprint 上的缓存属性
    if not hasattr(cron_bp, '_cron_cache'):
        cron_bp._cron_cache = {}
        cron_bp._cron_cache_time = {}
    
    now = time.time()
    if cache_key in cron_bp._cron_cache and cron_bp._cron_cache_time.get(cache_key, 0) > now - 0.5:
        return api_ok({'jobs': cron_bp._cron_cache[cache_key], 'has_crontab': True})
    
    # 加锁执行
    with _cron_lock:
        # 再次检查缓存（加锁后）
        if cache_key in cron_bp._cron_cache and cron_bp._cron_cache_time.get(cache_key, 0) > now - 0.5:
            return api_ok({'jobs': cron_bp._cron_cache[cache_key], 'has_crontab': True})
        
        # 最多重试 3 次
        for attempt in range(3):
            try:
                result = subprocess.run(
                    ['bash', '-c', 'crontab -l 2>/dev/null'],
                    capture_output=True, text=True, timeout=10
                )
                content = result.stdout
                
                if not content.strip():
                    cron_bp._cron_cache[cache_key] = []
                    cron_bp._cron_cache_time[cache_key] = now
                    return api_ok({'jobs': [], 'has_crontab': False})
                
                jobs = _parse_crontab(content)
                cron_bp._cron_cache[cache_key] = jobs
                cron_bp._cron_cache_time[cache_key] = now
                return api_ok({'jobs': jobs, 'has_crontab': True})
                
            except Exception as e:
                if attempt == 2:
                    return api_error(str(e), status=500)
                time.sleep(0.05)
    
    return api_ok({'jobs': [], 'has_crontab': False})


@cron_bp.route('/api/cron/add', methods=['POST'])
def api_cron_add():
    """添加 cron 任务."""
    data = request.get_json(silent=True) or {}
    
    minute = data.get('minute', '*')
    hour = data.get('hour', '*')
    day = data.get('day', '*')
    month = data.get('month', '*')
    weekday = data.get('weekday', '*')
    command = data.get('command', '').strip()
    
    if not command:
        return api_error('Missing command', status=400)
    
    # 安全检查：禁止危险命令
    dangerous = [';', '|', '&', '&&', '||', '>', '<', '>>', '$(', '`']
    for d in dangerous:
        if d in command:
            return api_error('Dangerous command detected', status=400)
    
    cron_line = f"{minute} {hour} {day} {month} {weekday} {command}"
    
    try:
        # 获取现有 crontab
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True, text=True, timeout=10
        )
        
        existing = result.stdout if result.returncode == 0 else ''
        
        # 添加新任务
        new_cron = existing.rstrip() + '\n' + cron_line + '\n'
        
        with _cron_lock:
            proc = subprocess.run(
                ['crontab', '-'],
                input=new_cron,
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if proc.returncode != 0:
            return api_error(proc.stderr or 'Failed to add cron', status=500)
        
        return api_ok({'success': True, 'job': cron_line})
        
    except Exception as e:
        return api_error(str(e), status=500)


@cron_bp.route('/api/cron/remove', methods=['POST'])
def api_cron_remove():
    """删除 cron 任务."""
    data = request.get_json(silent=True) or {}
    raw_line = data.get('raw', '')
    
    if not raw_line:
        return api_error('Missing job', status=400)
    
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return api_error('No crontab', status=400)
        
        lines = result.stdout.split('\n')
        new_lines = [l for l in lines if l.strip() and l.strip() != raw_line and l.strip() != '#' + raw_line]
        
        new_crontab = '\n'.join(new_lines) + '\n'
        
        with _cron_lock:
            proc = subprocess.run(
                ['crontab', '-'],
                input=new_crontab,
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if proc.returncode != 0:
            return api_error(proc.stderr or 'Failed to remove', status=500)
        
        return api_ok({'success': True})
        
    except Exception as e:
        return api_error(str(e), status=500)


@cron_bp.route('/api/cron/enable', methods=['POST'])
def api_cron_enable():
    """启用/禁用 cron 任务."""
    data = request.get_json(silent=True) or {}
    raw_line = data.get('raw', '')
    enabled = data.get('enabled', True)
    
    if not raw_line:
        return api_error('Missing job', status=400)
    
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True, text=True, timeout=10
        )
        
        lines = result.stdout.split('\n')
        new_lines = []
        for l in lines:
            if l.strip() == raw_line:
                new_lines.append('#' + l if enabled else l[1:] if l.startswith('#') else l)
            else:
                new_lines.append(l)
        
        new_crontab = '\n'.join(new_lines) + '\n'
        
        with _cron_lock:
            proc = subprocess.run(
                ['crontab', '-'],
                input=new_crontab,
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if proc.returncode != 0:
            return api_error(proc.stderr or 'Failed', status=500)
        
        return api_ok({'success': True})
        
    except Exception as e:
        return api_error(str(e), status=500)


@cron_bp.route('/api/cron/templates')
def api_cron_templates():
    """获取常用 cron 模板."""
    templates = [
        {'name': 'Every Minute', 'schedule': '* * * * *', 'command': ''},
        {'name': 'Every Hour', 'schedule': '0 * * * *', 'command': ''},
        {'name': 'Every Day 3AM', 'schedule': '0 3 * * *', 'command': ''},
        {'name': 'Every Week', 'schedule': '0 0 * * 0', 'command': ''},
        {'name': 'Every Month', 'schedule': '0 0 1 * *', 'command': ''},
        {'name': 'On Boot', 'schedule': '@reboot', 'command': ''},
    ]
    return api_ok({'templates': templates})


@cron_bp.route('/api/cron/run', methods=['POST'])
def api_cron_run():
    """立即执行一次 cron 命令."""
    data = request.get_json(silent=True) or {}
    command = data.get('command', '').strip()
    
    if not command:
        return api_error('缺少命令')
    
    try:
        # 直接执行命令
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return api_ok({
            'success': proc.returncode == 0,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
            'returncode': proc.returncode
        })
        
    except subprocess.TimeoutExpired:
        return api_error('执行超时', status=500)
    except Exception as e:
        return api_error(str(e), status=500)
