#!/usr/bin/env python3
"""
每日代码统计邮件脚本
过去十天代码统计 + 可视化图表
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta

# 添加 clawos 路径
sys.path.insert(0, os.path.expanduser('~/clawos'))
os.chdir(os.path.expanduser('~/clawos'))

from lib.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

RECIPIENT = 'mrytsr@qq.com'

def get_git_stats(date_str):
    """获取指定日期的git代码统计"""
    result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59',
         '--pretty=format:%h', '--numstat', '--'],
        capture_output=True, text=True, cwd=os.path.expanduser('~/clawos')
    )
    
    total_added = 0
    total_deleted = 0
    commits = 0
    
    for line in result.stdout.split('\n'):
        parts = line.split('\t')
        if len(parts) >= 2:
            added_str = parts[0].strip()
            deleted_str = parts[1].strip()
            if added_str.isdigit() and deleted_str.isdigit():
                total_added += int(added_str)
                total_deleted += int(deleted_str)
    
    # 获取提交数
    commit_result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59', '--count', '--'],
        capture_output=True, text=True, cwd=os.path.expanduser('~/clawos')
    )
    try:
        commits = int(commit_result.stdout.strip())
    except:
        pass
    
    return {
        'date': date_str,
        'added': total_added,
        'deleted': total_deleted,
        'net': total_added - total_deleted,
        'commits': commits
    }

def get_last_10_days_stats():
    """获取过去10天的统计数据"""
    stats = []
    for i in range(1, 11):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_stats = get_git_stats(date)
        stats.append(day_stats)
    return stats

def generate_ascii_chart(stats):
    """生成ASCII柱状图"""
    if not stats:
        return "无数据"
    
    max_val = max(max(s['added'] for s in stats), 1)
    chart_lines = []
    
    # 标题
    chart_lines.append("📈 代码行数趋势 (新增)")
    chart_lines.append("-" * 50)
    
    # 简化版柱状图（每50行一个字符）
    unit = max(50, max_val // 30)  # 动态调整单位
    max_bar = 30
    
    for s in stats:
        bar_len = min(int(s['added'] / unit), max_bar)
        bar = '█' * bar_len
        date = s['date'][5:]  # MM-DD
        chart_lines.append(f"{date} |{bar:<30} {s['added']:,}")
    
    chart_lines.append("-" * 50)
    return '\n'.join(chart_lines)

def generate_html(stats):
    """生成HTML邮件内容"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 计算汇总
    total_added = sum(s['added'] for s in stats)
    total_deleted = sum(s['deleted'] for s in stats)
    total_commits = sum(s['commits'] for s in stats)
    avg_added = total_added // len(stats) if stats else 0
    
    # ASCII 图表
    ascii_chart = generate_ascii_chart(stats)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: #f6f8fa; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #1f883d; border-bottom: 2px solid #1f883d; padding-bottom: 10px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-box {{ flex: 1; background: #f6f8fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #1f883d; }}
        .stat-label {{ color: #57606a; font-size: 14px; }}
        .chart {{ background: #1f1f1f; color: #4af626; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 12px; overflow-x: auto; white-space: pre; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #d0d7de; padding: 10px; text-align: center; }}
        th {{ background: #1f883d; color: #fff; }}
        tr:nth-child(even) {{ background: #f6f8fa; }}
        .positive {{ color: #1a7f37; }}
        .negative {{ color: #cf222e; }}
        .trend {{ height: 60px; vertical-align: bottom; }}
        .bar {{ width: 20px; background: #1f883d; margin: 0 auto; border-radius: 2px 2px 0 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 ClawOS 代码统计 (过去10天)</h1>
        
        <div class="summary">
            <div class="stat-box">
                <div class="stat-value">{total_added:,}</div>
                <div class="stat-label">总新增行</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{total_deleted:,}</div>
                <div class="stat-label">总删除行</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{total_commits:,}</div>
                <div class="stat-label">总提交数</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{avg_added:,}</div>
                <div class="stat-label">日均新增</div>
            </div>
        </div>
        
        <h3>📈 趋势图 (ASCII)</h3>
        <div class="chart">{ascii_chart}</div>
        
        <h3>📋 每日明细</h3>
        <table>
            <tr>
                <th>日期</th>
                <th>提交</th>
                <th>新增</th>
                <th>删除</th>
                <th>净增</th>
                <th>趋势</th>
            </tr>'''
    
    max_added = max(s['added'] for s in stats) if stats else 1
    
    for s in reversed(stats):  # 从早到晚
        net_class = 'positive' if s['net'] >= 0 else 'negative'
        net_sign = '+' if s['net'] >= 0 else ''
        bar_height = max(5, int(s['added'] / max_added * 60))
        html += f'''
            <tr>
                <td>{s['date']}</td>
                <td>{s['commits']}</td>
                <td>{s['added']:,}</td>
                <td>{s['deleted']:,}</td>
                <td class="{net_class}">{net_sign}{s['net']:,}</td>
                <td class="trend"><div class="bar" style="height: {bar_height}px;"></div></td>
            </tr>'''
    
    html += '''
        </table>
        
        <p style="color: #8c959f; font-size: 12px; text-align: center; margin-top: 20px;">
            Generated by ClawOS Daily Stats • ''' + today + '''
        </p>
    </div>
</body>
</html>'''
    
    return html

def send_email(stats):
    """发送邮件"""
    html = generate_html(stats)
    
    message = MIMEMultipart('alternative')
    message['From'] = f'ClawOS <{SMTP_USER}>'
    message['To'] = RECIPIENT
    message['Subject'] = Header(f'ClawOS 代码统计 (过去10天)', 'utf-8')
    message.attach(MIMEText(html, 'html', 'utf-8'))
    
    server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [RECIPIENT], message.as_string())
    server.quit()
    
    print(f'邮件发送成功!')

if __name__ == '__main__':
    print('获取过去10天统计数据...')
    stats = get_last_10_days_stats()
    
    total_added = sum(s['added'] for s in stats)
    total_deleted = sum(s['deleted'] for s in stats)
    total_commits = sum(s['commits'] for s in stats)
    
    print(f'\n汇总: +{total_added:,} -{total_deleted:,} ({total_commits} commits)\n')
    print(generate_ascii_chart(stats))
    
    send_email(stats)
