#!/usr/bin/env python3
"""
每日代码统计邮件脚本

使用前请在环境变量或配置文件中设置:
- SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS
- 或修改 lib/config.py
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

# 接收者邮箱
RECIPIENT = os.environ.get('RECIPIENT_EMAIL', 'your-email@example.com')

# 项目配置（可自定义）
PROJECTS = {
    'clawos': os.path.expanduser('~/clawos'),
}


def get_git_stats(date_str, project_dir):
    """获取指定日期的git代码统计"""
    result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59',
         '--pretty=format:%h', '--numstat', '--'],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    stats = {
        'insertions': 0,
        'deletions': 0,
        'files': set(),
        'commits': [],
        'authors': defaultdict(int)
    }

    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 3:
            insertions = parts[0]
            deletions = parts[1]
            file_path = parts[2]

            if insertions.isdigit():
                stats['insertions'] += int(insertions)
            if deletions.isdigit():
                stats['deletions'] += int(deletions)

            if file_path not in ['-', '']:
                stats['files'].add(file_path)

    # 获取提交信息
    commit_result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59',
         '--pretty=format:%h|%s|%an', '--'],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    for line in commit_result.stdout.strip().split('\n'):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                stats['commits'].append({
                    'hash': parts[0],
                    'message': parts[1],
                    'author': parts[2]
                })
                stats['authors'][parts[2]] += 1

    return stats


def get_file_type_stats(date_str, project_dir):
    """获取各文件类型的变更统计"""
    result = subprocess.run(
        ['git', 'log', f'--since={date_str} 00:00:00', f'--until={date_str} 23:59:59',
         '--pretty=format:%h', '--numstat', '--'],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    type_stats = defaultdict(lambda: {'files': set(), 'insertions': 0, 'deletions': 0})

    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) == 3:
            insertions = parts[0]
            deletions = parts[1]
            file_path = parts[2]

            if file_path in ['-', '']:
                continue

            ext = os.path.splitext(file_path)[1] or '无扩展名'
            type_stats[ext]['files'].add(file_path)

            if insertions.isdigit():
                type_stats[ext]['insertions'] += int(insertions)
            if deletions.isdigit():
                type_stats[ext]['deletions'] += int(deletions)

    return type_stats


def format_stats_html(project_name, stats, type_stats):
    """格式化统计信息为HTML"""
    total_changes = stats['insertions'] + stats['deletions']

    html = f"""
    <h2>{project_name}</h2>
    <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>提交次数</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px;">{len(stats['commits'])}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>文件变更</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px;">{len(stats['files'])}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>新增行数</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px; color: green;">+{stats['insertions']}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>删除行数</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px; color: red;">-{stats['deletions']}</td>
        </tr>
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px;"><strong>总变更</strong></td>
            <td style="border: 1px solid #ddd; padding: 8px;">{total_changes}</td>
        </tr>
    </table>
    """

    # 提交者统计
    if stats['authors']:
        html += "<h3>👥 提交者统计</h3><ul>"
        for author, count in sorted(stats['authors'].items(), key=lambda x: x[1], reverse=True)[:5]:
            html += f"<li>{author}: {count} 次提交</li>"
        html += "</ul>"

    # 文件类型统计
    if type_stats:
        html += "<h3>📁 文件类型统计</h3><table style='border-collapse: collapse; width: 100%;'>"
        html += "<tr style='background: #f5f5f5;'><th style='border: 1px solid #ddd; padding: 8px;'>类型</th><th style='border: 1px solid #ddd; padding: 8px;'>文件数</th><th style='border: 1px solid #ddd; padding: 8px;'>新增</th><th style='border: 1px solid #ddd; padding: 8px;'>删除</th></tr>"

        for ext, data in sorted(type_stats.items(), key=lambda x: x[1]['insertions'] + x[1]['deletions'], reverse=True)[:10]:
            html += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>{ext}</td><td style='border: 1px solid #ddd; padding: 8px;'>{len(data['files'])}</td><td style='border: 1px solid #ddd; padding: 8px; color: green;'>+{data['insertions']}</td><td style='border: 1px solid #ddd; padding: 8px; color: red;'>-{data['deletions']}</td></tr>"

        html += "</table>"

    # 最近提交
    if stats['commits']:
        html += "<h3>📝 最近提交</h3><ul>"
        for commit in stats['commits'][:10]:
            html += f"<li><code>{commit['hash'][:7]}</code> <strong>{commit['author']}</strong>: {commit['message']}</li>"
        html += "</ul>"

    return html


def send_email(html_content, date_str):
    """发送邮件"""
    if not SMTP_USER or not SMTP_PASS or not RECIPIENT:
        print("缺少邮件配置，跳过发送")
        print(f"SMTP_USER: {SMTP_USER}")
        print(f"RECIPIENT: {RECIPIENT}")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'📊 ClawOS 代码统计 - {date_str}'
    msg['From'] = f'ClawOS <{SMTP_USER}>'
    msg['To'] = RECIPIENT

    # HTML 内容
    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [RECIPIENT], msg.as_string())
        server.quit()
        print(f"邮件发送成功: {date_str}")
    except Exception as e:
        print(f"邮件发送失败: {e}")


def main():
    # 获取昨天日期
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = yesterday

    print(f"📊 生成 {date_str} 的代码统计...")

    all_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
            h3 {{ color: #666; margin-top: 20px; }}
            code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
            ul {{ padding-left: 20px; }}
            li {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <h1>📊 代码统计日报 - {date_str}</h1>
    """

    for project_name, project_dir in PROJECTS.items():
        if not os.path.exists(project_dir):
            print(f"⚠️ 项目目录不存在: {project_dir}")
            continue

        if not os.path.exists(os.path.join(project_dir, '.git')):
            print(f"⚠️ 不是 Git 仓库: {project_dir}")
            continue

        print(f"📂 处理项目: {project_name}")

        stats = get_git_stats(date_str, project_dir)
        type_stats = get_file_type_stats(date_str, project_dir)

        all_html += format_stats_html(project_name, stats, type_stats)

    all_html += "</body></html>"

    send_email(all_html, date_str)


if __name__ == '__main__':
    main()
