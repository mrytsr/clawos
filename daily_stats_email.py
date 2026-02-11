#!/usr/bin/env python3
"""
每日代码统计邮件脚本
每天早上8点发送前一天的代码统计
"""

import sys
import os

# 添加 clawos 路径
sys.path.insert(0, '/home/tjx/clawos')
os.chdir('/home/tjx/clawos')

import subprocess
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 配置
from lib.config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS

YESTERDAY = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
RECIPIENT = 'mrytsr@qq.com'

def get_git_stats():
    """获取指定日期的git代码统计"""
    date = YESTERDAY
    
    result = subprocess.run(
        ['git', 'log', f'--since={date} 00:00:00', f'--until={date} 23:59:59', 
         '--pretty=format:%h %s', '--numstat'],
        capture_output=True, text=True
    )
    
    stats = {}
    total_added = 0
    total_deleted = 0
    
    for line in result.stdout.split('\n'):
        parts = line.split('\t')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            added = int(parts[0])
            deleted = int(parts[1])
            total_added += added
            total_deleted += deleted
        elif len(parts) == 2 and parts[0].startswith('http'):
            # commit line, ignore
            pass
    
    return total_added, total_deleted

def generate_html(added, deleted):
    """生成HTML邮件内容"""
    return f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
table{{border-collapse:collapse;width:100%;font-family:Arial}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
th{{background:#1f883d;color:#fff}}
tr:nth-child(even){{background:#f9f9f9}}
.total{{font-weight:bold;background:#f0f0f0}}
</style></head>
<body>
<h2>📊 ClawOS 代码统计 ({YESTERDAY})</h2>
<p>昨日新增：{added:,} 行 | 删除：{deleted:,} 行</p>
</body></html>'''

def send_email(added, deleted):
    """发送邮件"""
    html = generate_html(added, deleted)
    
    message = MIMEMultipart('alternative')
    message['From'] = f'ClawOS <{SMTP_USER}>'
    message['To'] = RECIPIENT
    message['Subject'] = Header(f'ClawOS {YESTERDAY} 代码统计', 'utf-8')
    message.attach(MIMEText(html, 'html', 'utf-8'))
    
    server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    server.login(SMTP_USER, SMTP_PASS)
    server.sendmail(SMTP_USER, [RECIPIENT], message.as_string())
    server.quit()
    
    print(f'邮件发送成功: {YESTERDAY} +{added:,} -{deleted:,}')

if __name__ == '__main__':
    added, deleted = get_git_stats()
    print(f'{YESTERDAY}: 新增 {added} 行，删除 {deleted} 行')
    send_email(added, deleted)
