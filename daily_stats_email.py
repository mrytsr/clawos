#!/usr/bin/env python3
"""
每日代码统计邮件脚本
增强版：包含文件变更明细、提交者统计、类型统计
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

# 添加 clawos 路径
sys.path.insert(0, os.path.expanduser('~/clawos'))
os.chdir(os.path.expanduser('~/clawos'))

from lib.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

RECIPIENT = 'mrytsr@qq.com'

# 项目配置
PROJECTS = {
    'clawos': os.path.expanduser('~/clawos'),
    'xiandan': os.path.expanduser('~/xiandan'),
}

def get_git_stats(date_str, project_dir):
    """获取指定日期的git代码统计"""
    result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59',
         '--pretty=format:%h', '--numstat', '--'],
        capture_output=True, text=True, cwd=project_dir
    )
    
    total_added = 0
    total_deleted = 0
    commits = 0
    files_added = []
    files_modified = []
    files_deleted = []
    file_types = defaultdict(int)
    author_stats = defaultdict(lambda: {'additions': 0, 'deletions': 0, 'commits': 0})
    
    for line in result.stdout.split('\n'):
        parts = line.split('\t')
        if len(parts) >= 3:
            added_str = parts[0].strip()
            deleted_str = parts[1].strip()
            filename = parts[2].strip()
            
            if added_str.isdigit() and deleted_str.isdigit():
                added = int(added_str)
                deleted = int(deleted_str)
                total_added += added
                total_deleted += deleted
                
                if filename not in ['dev/null', '']:
                    ext = os.path.splitext(filename)[1] or '.无后缀'
                    file_types[ext] += 1
                    
                    if added > 0 and deleted == 0:
                        files_added.append({'name': filename, 'lines': added})
                    elif deleted > 0 and added == 0:
                        files_deleted.append({'name': filename, 'lines': deleted})
                    else:
                        files_modified.append({'name': filename, 'add': added, 'del': deleted})
    
    # 获取提交数
    commit_result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59', '--count', '--'],
        capture_output=True, text=True, cwd=project_dir
    )
    try:
        commits = int(commit_result.stdout.strip())
    except:
        pass
    
    # 获取提交者统计
    author_result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59',
         '--pretty=format:%an', '--numstat', '--'],
        capture_output=True, text=True, cwd=project_dir
    )
    
    for line in author_result.stdout.split('\n'):
        parts = line.split('\t')
        if len(parts) >= 3:
            author = parts[0].strip()
            if author:
                added_str = parts[1].strip()
                deleted_str = parts[2].strip()
                if added_str.isdigit() and deleted_str.isdigit():
                    author_stats[author]['additions'] += int(added_str)
                    author_stats[author]['deletions'] += int(deleted_str)
    
    # 统计每个作者的提交数
    commit_authors = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'until={date_str} 23:59:59', '--pretty=format:%an', '--'],
        capture_output=True, text=True, cwd=project_dir
    )
    author_commits = defaultdict(int)
    for author in commit_authors.stdout.strip().split('\n'):
        if author:
            author_commits[author] += 1
    
    for author, count in author_commits.items():
        author_stats[author]['commits'] = count
    
    return {
        'date': date_str,
        'date_short': datetime.strptime(date_str, '%Y-%m-%d').strftime('%m/%d'),
        'weekday': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][datetime.strptime(date_str, '%Y-%m-%d').weekday()],
        'added': total_added,
        'deleted': total_deleted,
        'net': total_added - total_deleted,
        'commits': commits,
        'files_added': sorted(files_added, key=lambda x: x['lines'], reverse=True)[:10],
        'files_modified': sorted(files_modified, key=lambda x: x['add'] + x['del'], reverse=True)[:10],
        'files_deleted': sorted(files_deleted, key=lambda x: x['lines'], reverse=True)[:10],
        'file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]),
        'top_authors': sorted(author_stats.items(), key=lambda x: x[1]['additions'], reverse=True)[:5]
    }

def get_last_10_days_stats(project_name='clawos'):
    """获取过去10天的统计数据"""
    project_dir = PROJECTS.get(project_name, PROJECTS['clawos'])
    stats = []
    for i in range(1, 11):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_stats = get_git_stats(date, project_dir)
        day_stats['project'] = project_name
        stats.append(day_stats)
    return stats

def sparkline(data, width=20):
    """生成迷你sparkline字符图"""
    if not data or max(data) == 0:
        return '─' * width
    
    min_val, max_val = min(data), max(data)
    range_val = max_val - min_val
    if range_val == 0:
        return '─' * width
    
    chars = '▁▂▃▄▅▆▇█'
    result = []
    for val in data:
        idx = int((val - min_val) / range_val * (len(chars) - 1))
        idx = max(0, min(idx, len(chars) - 1))  # 边界保护
        result.append(chars[idx])
    return ''.join(result)

def generate_ascii_chart(stats):
    """生成ASCII柱状图"""
    if not stats:
        return "无数据"
    
    active_stats = [s for s in stats if s['added'] > 0 or s['deleted'] > 0]
    if not active_stats:
        return "过去10天无代码变更"
    
    lines = []
    
    # 标题
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║           📊 代码贡献趋势 (新增行数)                     ║")
    lines.append("╠══════════════════════════════════════════════════════════╣")
    
    # 添加 sparkline
    added_data = [s['added'] for s in stats]
    spark = sparkline(added_data)
    lines.append(f"║ 趋势: {spark}  ║")
    
    # 柱状图
    max_val = max(max(s['added'] for s in active_stats), 1)
    
    for s in stats:
        date = s['date_short']
        weekday = s['weekday']
        
        if s['added'] > 0 or s['deleted'] > 0:
            # 绘制条形
            bar_width = int(s['added'] / max_val * 35)
            bar = '█' * bar_width
            
            # 添加对比（昨天vs今天）
            net = s['net']
            net_str = f"{net:+d}"
            if net > 0:
                net_str = f'✓{net:+,d}'
            elif net < 0:
                net_str = f'✗{net:,}'
            
            lines.append(f"║ {date} {weekday} │{bar:<35} {s['added']:>5,}  {net_str:>8} ║")
        else:
            lines.append(f"║ {date} {weekday} │{'·':<35}     0         ║")
    
    # 底部统计
    total_added = sum(s['added'] for s in stats)
    total_deleted = sum(s['deleted'] for s in stats)
    total_commits = sum(s['commits'] for s in stats)
    days_with_work = len([s for s in stats if s['added'] > 0])
    
    lines.append("╠══════════════════════════════════════════════════════════╣")
    lines.append(f"║ 总计: +{total_added:,} 行  -{total_deleted:,} 行  |  {total_commits} commits  |  {days_with_work}/10 天有提交 ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    
    return '\n'.join(lines)

def generate_html(all_stats):
    """生成HTML邮件内容"""
    today = datetime.now().strftime('%Y-%m-%d')
    project_names = ' + '.join(all_stats.keys())
    
    # 汇总所有项目的统计
    stats = []
    for project_stats in all_stats.values():
        stats.extend(project_stats)
    total_added = sum(s['added'] for s in stats)
    total_deleted = sum(s['deleted'] for s in stats)
    total_commits = sum(s['commits'] for s in stats)
    total_files = sum(len(s['files_added']) + len(s['files_modified']) + len(s['files_deleted']) for s in stats)
    active_days = len([s for s in stats if s['added'] > 0])
    avg_added = total_added // max(active_days, 1)
    
    # 昨日数据
    yesterday = stats[0] if stats else None
    day_before = stats[1] if len(stats) > 1 else None
    
    # 聚合文件类型
    all_file_types = defaultdict(int)
    for s in stats:
        for ft, count in s['file_types'].items():
            all_file_types[ft] += count
    
    # 聚合作者
    all_authors = defaultdict(lambda: {'additions': 0, 'deletions': 0, 'commits': 0})
    for s in stats:
        for author, data in s['top_authors']:
            all_authors[author]['additions'] += data['additions']
            all_authors[author]['deletions'] += data['deletions']
            all_authors[author]['commits'] += data['commits']
    
    top_authors = sorted(all_authors.items(), key=lambda x: x[1]['additions'], reverse=True)[:5]
    max_author_add = top_authors[0][1]['additions'] if top_authors else 1
    
    # 生成 sparkline 数据
    added_data = [s['added'] for s in stats]
    sparkline_svg = generate_sparkline_svg(added_data)
    
    ascii_chart = generate_ascii_chart(stats)
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; background: #0d1117; color: #c9d1d9; margin: 0; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        
        /* Header */
        .header {{ text-align: center; margin-bottom: 24px; }}
        .header h1 {{ color: #58a6ff; font-size: 24px; margin: 0 0 8px; }}
        .header .subtitle {{ color: #8b949e; font-size: 14px; }}
        
        /* Cards */
        .card {{ background: #161b22; border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #30363d; }}
        .card-title {{ color: #58a6ff; font-size: 14px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
        
        /* Stats Grid */
        .stats-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }}
        .stat-item {{ background: #21262d; border-radius: 8px; padding: 16px 12px; text-align: center; }}
        .stat-value {{ font-size: 28px; font-weight: 700; color: #58a6ff; }}
        .stat-value.green {{ color: #3fb950; }}
        .stat-value.red {{ color: #f85149; }}
        .stat-value.yellow {{ color: #d29922; }}
        .stat-label {{ font-size: 12px; color: #8b949e; margin-top: 4px; }}
        
        /* Sparkline */
        .sparkline {{ height: 60px; display: flex; align-items: flex-end; justify-content: space-between; gap: 4px; padding: 10px 0; }}
        .spark-bar {{ flex: 1; background: linear-gradient(to top, #1f6feb, #58a6ff); border-radius: 2px 2px 0 0; min-height: 4px; }}
        .spark-label {{ font-size: 10px; color: #8b949e; text-align: center; margin-top: 6px; }}
        
        /* Authors */
        .author-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .author-item {{ display: flex; align-items: center; gap: 12px; }}
        .author-rank {{ width: 24px; height: 24px; border-radius: 50%; background: #21262d; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #58a6ff; }}
        .author-rank.gold {{ background: linear-gradient(135deg, #d29922, #f0b429); color: #0d1117; }}
        .author-rank.silver {{ background: linear-gradient(135deg, #8b949e, #c9d1d9); color: #0d1117; }}
        .author-rank.bronze {{ background: linear-gradient(135deg, #bd561d, #db7c37); color: #0d1117; }}
        .author-name {{ width: 100px; font-size: 13px; color: #c9d1d9; }}
        .author-bar-wrap {{ flex: 1; height: 8px; background: #21262d; border-radius: 4px; overflow: hidden; }}
        .author-bar {{ height: 100%; background: linear-gradient(90deg, #1f6feb, #58a6ff); border-radius: 4px; }}
        .author-stats {{ width: 140px; text-align: right; font-size: 11px; color: #8b949e; }}
        .author-stats .adds {{ color: #3fb950; }}
        .author-stats .dels {{ color: #f85149; }}
        
        /* File Types */
        .type-grid {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .type-tag {{ display: flex; align-items: center; gap: 6px; background: #21262d; padding: 6px 12px; border-radius: 20px; font-size: 12px; }}
        .type-tag .ext {{ color: #58a6ff; font-weight: 500; }}
        .type-tag .count {{ color: #8b949e; }}
        
        /* Table */
        .data-table {{ width: 100%; border-collapse: collapse; }}
        .data-table th {{ text-align: left; padding: 10px 12px; background: #21262d; color: #8b949e; font-size: 12px; font-weight: 600; border-bottom: 1px solid #30363d; }}
        .data-table th.right {{ text-align: right; }}
        .data-table td {{ padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 13px; }}
        .data-table td.right {{ text-align: right; }}
        .data-table tr:hover {{ background: #161b22; }}
        .val-add {{ color: #3fb950; }}
        .val-del {{ color: #f85149; }}
        .val-net.positive {{ color: #3fb950; }}
        .val-net.negative {{ color: #f85149; }}
        
        /* Mini chart in table */
        .mini-bar-wrap {{ width: 60px; height: 16px; background: #21262d; border-radius: 2px; display: inline-block; }}
        .mini-bar {{ height: 100%; background: #1f6feb; border-radius: 2px; }}
        
        /* Footer */
        .footer {{ text-align: center; color: #484f58; font-size: 11px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>📊 代码统计</h1>
            <div class="subtitle">
            项目: {project_names}<br>
            过去 10 天 · {active_days} 天有提交 · {today}
        </div>
        </div>
        
        <!-- 核心指标 -->
        <div class="card">
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value green">+{total_added:,}</div>
                    <div class="stat-label">总新增行</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value red">-{total_deleted:,}</div>
                    <div class="stat-label">总删除行</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_commits}</div>
                    <div class="stat-label">提交次数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_files}</div>
                    <div class="stat-label">变更文件</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value yellow">{avg_added:,}</div>
                    <div class="stat-label">日均新增</div>
                </div>
            </div>
        </div>
        
        <!-- 趋势图 -->
        <div class="card">
            <div class="card-title">📈 贡献趋势</div>
            <div class="sparkline" style="height:50px;">'''
    
    max_add = max(added_data) if added_data else 1
    for s in stats:
        bar_height = max(3, int(s['added'] / max_add * 40))
        html += f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;"><div class="spark-bar" style="height:{bar_height}px;width:80%;"></div></div>'
    
    html += f'''</div>
        </div>
        
        <!-- ASCII 图 -->
        <div class="card">
            <div class="card-title">📊 详细趋势</div>
            <pre class="ascii-chart" style="background:#0d1117;color:#3fb950;font-family:monospace;font-size:9px;padding:8px;border-radius:6px;overflow-x:auto;margin:0;white-space:pre;">{ascii_chart}</pre>
        </div>
        
        <!-- 提交者排行 -->
        <div class="card">
            <div class="card-title">👤 贡献者排行</div>
            <div class="author-list">'''
    
    rank_classes = ['gold', 'silver', 'bronze', '', '']
    for i, (author, data) in enumerate(top_authors):
        rank_class = rank_classes[i] if i < 3 else ''
        bar_width = int((data['additions'] / max_author_add) * 100)
        medals = ['🥇', '🥈', '🥉', '4', '5'][i]
        html += f'''
                <div class="author-item">
                    <div class="author-rank {rank_class}">{medals}</div>
                    <div class="author-name">{author}</div>
                    <div class="author-bar-wrap">
                        <div class="author-bar" style="width: {bar_width}%"></div>
                    </div>
                    <div class="author-stats">
                        <span class="adds">+{data['additions']:,}</span> 
                        <span class="dels">-{data['deletions']:,}</span>
                    </div>
                </div>'''
    
    html += '''
            </div>
        </div>
        
        <!-- 文件类型 -->
        <div class="card">
            <div class="card-title">📁 文件类型分布</div>
            <div class="type-grid">'''
    
    for ext, count in list(all_file_types.items())[:12]:
        icons = {
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨', 
            '.json': '📋', '.md': '📝', '.sh': '⚡', '.ts': '💠',
            '.vue': '💚', '.yml': '📐', '.yaml': '📐', '.txt': '📄'
        }
        icon = icons.get(ext, '📄')
        html += f'<div class="type-tag"><span class="ext">{icon} {ext}</span><span class="count">{count}</span></div>'
    
    html += '''
            </div>
        </div>
        
        <!-- 每日明细 - 卡片形式 -->
        <div class="card">
            <div class="card-title">📋 每日明细</div>
            <div class="day-cards">'''
    
    max_added = max(s['added'] for s in stats) if stats else 1
    
    for s in reversed(stats):
        net_class = 'positive' if s['net'] >= 0 else 'negative'
        net_sign = '+' if s['net'] >= 0 else ''
        bar_width = max(2, int(s['added'] / max_added * 60))
        
        html += f'''
                    <tr>
                        <td>{s['date_short']}</td>
                        <td style="color:#8b949e;">{s['weekday']}</td>
                        <td class="right">{s['commits']}</td>
                        <td class="right val-add">+{s['added']:,}</td>
                        <td class="right val-del">-{s['deleted']:,}</td>
                        <td class="right val-net {net_class}">{net_sign}{s['net']:,}</td>
                        <td><div class="mini-bar-wrap"><div class="mini-bar" style="width:{bar_width}px;"></div></div></td>
                    </tr>'''
    
    html += '''
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            Generated by ClawOS Daily Stats
        </div>
    </div>
</body>
</html>'''
    
    return html

def generate_sparkline_svg(data):
    """生成SVG sparkline"""
    if not data:
        return ""
    
    width, height = 200, 40
    max_val = max(data)
    if max_val == 0:
        return ""
    
    points = []
    for i, v in enumerate(data):
        x = int(i / (len(data) - 1) * width) if len(data) > 1 else width // 2
        y = height - int(v / max_val * height)
        points.append(f"{x},{y}")
    
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <polyline fill="none" stroke="#58a6ff" stroke-width="2" points="{' '.join(points)}"/>
    </svg>'''

def send_email(all_stats):
    """发送邮件"""
    html = generate_html(all_stats)
    
    message = MIMEMultipart('alternative')
    message['From'] = f'ClawOS <{SMTP_USER}>'
    message['To'] = RECIPIENT
    project_names = ' + '.join(all_stats.keys())
    message['Subject'] = Header(f'📊 {project_names} 代码统计 (过去10天)', 'utf-8')
    message.attach(MIMEText(html, 'html', 'utf-8'))
    
    server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [RECIPIENT], message.as_string())
    server.quit()
    
    print('邮件发送成功!')

if __name__ == '__main__':
    all_stats = {}
    
    for project_name, project_dir in PROJECTS.items():
        if os.path.isdir(project_dir):
            print(f'获取 {project_name} 过去10天统计数据...')
            stats = get_last_10_days_stats(project_name)
            all_stats[project_name] = stats
    
    # 汇总
    total_added = sum(s['added'] for stats in all_stats.values() for s in stats)
    total_deleted = sum(s['deleted'] for stats in all_stats.values() for s in stats)
    total_commits = sum(s['commits'] for stats in all_stats.values() for s in stats)
    
    print(f'\n========== 汇总 ==========')
    print(f'总计: +{total_added:,} -{total_deleted:,} ({total_commits} commits)\n')
    
    for project_name, stats in all_stats.items():
        print(f'--- {project_name} ---')
        print(generate_ascii_chart(stats))
        print()
    
    send_email(all_stats)
