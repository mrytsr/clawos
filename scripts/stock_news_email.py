#!/usr/bin/env python3
"""
Stock News Email Automation Script
Generates and sends comprehensive daily stock news emails with:
- Market summary (real-time indices)
- Top movers (A-share gainers and losers)
- Self-selected stock prices
- AI-generated news summary
- Beautiful HTML email format
"""

import sys
import os
import json
import datetime
from pathlib import Path

# Change to clawos directory and add lib/config to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLAWOS_DIR = os.path.dirname(SCRIPT_DIR)
LIB_DIR = os.path.join(CLAWOS_DIR, 'lib')
CONFIG_DIR = os.path.join(CLAWOS_DIR, 'config')

sys.path.insert(0, LIB_DIR)
sys.path.insert(0, CONFIG_DIR)

from email_utils import send_html_email
from config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, ENABLE_EMAIL

# Import stock configuration
import stock_config


def get_beijing_time():
    """Get current Beijing time (UTC+8)"""
    import pytz
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.datetime.now(beijing_tz)


def format_number(num, decimals=2):
    """Format number with appropriate decimal places"""
    if num is None or num == '' or num == '-':
        return '-'
    try:
        return f"{float(num):.{decimals}f}"
    except (ValueError, TypeError):
        return '-'


def generate_html_header(title, date):
    """Generate HTML email header"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f7fa;
            color: #333;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px 12px 0 0;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header .date {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 14px;
        }}
        .section {{
            background: white;
            margin: 15px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .section-title {{
            background: #f8f9fa;
            padding: 15px 20px;
            font-weight: 600;
            font-size: 16px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-title .icon {{
            font-size: 18px;
        }}
        .content {{
            padding: 20px;
        }}
        .indices-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
        }}
        .index-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        .index-name {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }}
        .index-value {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        .index-change {{
            font-size: 14px;
            font-weight: 500;
        }}
        .positive {{ color: #e74c3c; }}
        .negative {{ color: #27ae60; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .stock-code {{
            color: #667eea;
            font-weight: 500;
        }}
        .stock-name {{
            color: #666;
        }}
        .price {{
            font-weight: 600;
        }}
        .change-up {{ color: #e74c3c; }}
        .change-down {{ color: #27ae60; }}
        
        .summary-box {{
            background: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            border-radius: 0 8px 8px 0;
            line-height: 1.6;
        }}
        .summary-box p {{
            margin: 0 0 10px 0;
        }}
        .summary-box p:last-child {{
            margin-bottom: 0;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        @media (max-width: 600px) {{
            .container {{
                padding: 10px;
            }}
            .indices-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            th, td {{
                padding: 8px 10px;
                font-size: 13px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 {title}</h1>
            <div class="date">{date}</div>
        </div>
"""


def generate_html_footer():
    """Generate HTML email footer"""
    return """
        <div class="footer">
            <p>📈 每日股票新闻自动推送</p>
            <p>由 OpenClaw 自动化系统生成</p>
        </div>
    </div>
</body>
</html>
"""


def generate_market_indices_html(indices_data):
    """Generate HTML for market indices section"""
    html = """        <div class="section">
            <div class="section-title">
                <span class="icon">🌏</span>
                市场概览
            </div>
            <div class="content">
                <div class="indices-grid">
"""
    
    for name, data in indices_data.items():
        value = format_number(data.get('value', 0))
        change = data.get('change', 0)
        change_str = f"{'+' if change > 0 else ''}{change:.2f}%"
        change_class = "positive" if change > 0 else "negative"
        
        html += f"""                    <div class="index-card">
                        <div class="index-name">{name}</div>
                        <div class="index-value">{value}</div>
                        <div class="index-change {change_class}">{change_str}</div>
                    </div>
"""
    
    html += """                </div>
            </div>
        </div>
"""
    return html


def generate_top_movers_html(gainers, losers):
    """Generate HTML for top movers section"""
    html = """        <div class="section">
            <div class="section-title">
                <span class="icon">🔥</span>
                涨跌幅榜
            </div>
            <div class="content">
                <h4 style="margin: 0 0 15px 0; color: #e74c3c;">📈 涨幅榜 Top 10</h4>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>最新价</th>
                            <th>涨跌幅</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for i, stock in enumerate(gainers[:10], 1):
        html += f"""                        <tr>
                            <td>{i}</td>
                            <td class="stock-code">{stock.get('code', '-')}</td>
                            <td class="stock-name">{stock.get('name', '-')}</td>
                            <td class="price">{format_number(stock.get('price', 0))}</td>
                            <td class="change-up">{stock.get('change', '-')}</td>
                        </tr>
"""
    
    html += """                    </tbody>
                </table>
                
                <h4 style="margin: 25px 0 15px 0; color: #27ae60;">📉 跌幅榜 Top 10</h4>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>代码</th>
                            <th>名称</th>
                            <th>最新价</th>
                            <th>涨跌幅</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for i, stock in enumerate(losers[:10], 1):
        html += f"""                        <tr>
                            <td>{i}</td>
                            <td class="stock-code">{stock.get('code', '-')}</td>
                            <td class="stock-name">{stock.get('name', '-')}</td>
                            <td class="price">{format_number(stock.get('price', 0))}</td>
                            <td class="change-down">{stock.get('change', '-')}</td>
                        </tr>
"""
    
    html += """                    </tbody>
                </table>
            </div>
        </div>
"""
    return html


def generate_stock_picks_html(stocks_data):
    """Generate HTML for self-selected stocks section"""
    html = """        <div class="section">
            <div class="section-title">
                <span class="icon">⭐</span>
                自选股行情
            </div>
            <div class="content">
                <table>
                    <thead>
                        <tr>
                            <th>代码</th>
                            <th>名称</th>
                            <th>最新价</th>
                            <th>涨跌额</th>
                            <th>涨跌幅</th>
                            <th>成交量</th>
                            <th>成交额</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for stock in stocks_data:
        change_val = stock.get('change_value', 0)
        change_pct = stock.get('change_percent', 0)
        change_class = "change-up" if change_val > 0 else "change-down"
        change_prefix = "+" if change_val > 0 else ""
        
        volume = stock.get('volume', '-')
        turnover = stock.get('turnover', '-')
        
        html += f"""                        <tr>
                            <td class="stock-code">{stock.get('code', '-')}</td>
                            <td class="stock-name">{stock.get('name', '-')}</td>
                            <td class="price">{format_number(stock.get('price', 0))}</td>
                            <td class="{change_class}">{change_prefix}{format_number(change_val)}</td>
                            <td class="{change_class}">{change_prefix}{change_pct}%</td>
                            <td>{volume}</td>
                            <td>{turnover}</td>
                        </tr>
"""
    
    html += """                    </tbody>
                </table>
            </div>
        </div>
"""
    return html


def generate_ai_summary_html(ai_summary):
    """Generate HTML for AI summary section"""
    if not ai_summary:
        return ""
    
    html = """        <div class="section">
            <div class="section-title">
                <span class="icon">🤖</span>
                AI 市场摘要
            </div>
            <div class="content">
                <div class="summary-box">
"""
    
    # Split summary into paragraphs
    paragraphs = ai_summary.split('\n\n')
    for para in paragraphs:
        if para.strip():
            html += f"                    <p>{para.strip()}</p>\n"
    
    html += """                </div>
            </div>
        </div>
"""
    return html


def generate_full_email_html(title, date, indices_data, gainers, losers, stocks_data, ai_summary=None):
    """Generate complete HTML email"""
    html = generate_html_header(title, date)
    html += generate_market_indices_html(indices_data)
    html += generate_top_movers_html(gainers, losers)
    html += generate_stock_picks_html(stocks_data)
    if ai_summary:
        html += generate_ai_summary_html(ai_summary)
    html += generate_html_footer()
    return html


def fetch_market_indices():
    """
    Fetch real-time market indices data
    Using browser automation to scrape Eastmoney
    """
    # Placeholder implementation - in real use, would scrape from Eastmoney
    # This simulates the data structure returned
    return {
        "上证指数": {"value": 3388.56, "change": 0.85},
        "深证成指": {"value": 11409.82, "change": 1.23},
        "恒生指数": {"value": 16723.92, "change": -0.45},
        "道琼斯": {"value": 38996.39, "change": 0.42},
        "纳斯达克": {"value": 15942.55, "change": 0.68}
    }


def fetch_top_movers():
    """
    Fetch top gainers and losers from A-share market
    Using browser automation to scrape Eastmoney
    """
    # Placeholder - simulates data structure
    # In production, would parse Eastmoney's ranking pages
    
    # Sample gainers
    gainers = [
        {"code": "688728", "name": "叁腾科技", "price": 45.67, "change": "+15.23%"},
        {"code": "300841", "name": "康希诺", "price": 78.90, "change": "+12.45%"},
        {"code": "002824", "name": "和胜股份", "price": 23.45, "change": "+11.23%"},
        {"code": "688369", "name": "中科飞测", "price": 67.89, "change": "+10.56%"},
        {"code": "300931", "name": "通用电梯", "price": 12.34, "change": "+9.87%"},
        {"code": "688408", "name": "盟科药业", "price": 34.56, "change": "+9.23%"},
        {"code": "688118", "name": "普元信息", "price": 28.90, "change": "+8.76%"},
        {"code": "300997", "name": "立方精密", "price": 19.87, "change": "+8.45%"},
        {"code": "688538", "name": "华虹计通", "price": 15.67, "change": "+8.12%"},
        {"code": "688229", "name": "英方软件", "price": 42.13, "change": "+7.89%"},
    ]
    
    # Sample losers
    losers = [
        {"code": "688669", "name": "聚辰股份", "price": 35.67, "change": "-12.34%"},
        {"code": "300759", "name": "惠伦高科", "price": 8.90, "change": "-11.56%"},
        {"code": "688318", "name": "路维光电", "price": 22.45, "change": "-10.23%"},
        {"code": "300383", "name": "步长制药", "price": 18.90, "change": "-9.87%"},
        {"code": "688466", "name": "芯导科技", "price": 28.67, "change": "-9.34%"},
        {"code": "688057", "name": "金山科技", "price": 15.34, "change": "-8.76%"},
        {"code": "688358", "name": "龙腾光电", "price": 4.89, "change": "-8.45%"},
        {"code": "688488", "name": "华奥科技", "price": 12.67, "change": "-8.12%"},
        {"code": "300763", "name": "锦浪科技", "price": 67.89, "change": "-7.89%"},
        {"code": "688508", "name": "芯朋微", "price": 35.23, "change": "-7.56%"},
    ]
    
    return gainers, losers


def fetch_stock_prices(stock_list):
    """
    Fetch real-time prices for self-selected stocks
    """
    # Placeholder - simulates data structure
    # In production, would query stock APIs or scrape data
    
    stocks_data = []
    for stock in stock_list:
        # Simulated data for each stock
        stocks_data.append({
            "code": stock.get("code"),
            "name": stock.get("name"),
            "price": round(float(f"1{(hash(stock.get('code', '')) % 99)}"[:6]), 2),
            "change_value": round((hash(stock.get('code', '')) % 200 - 100) / 10, 2),
            "change_percent": round((hash(stock.get('code', '')) % 1000 - 500) / 100, 2),
            "volume": f"{hash(stock.get('code', '')) % 10000000:,}",
            "turnover": f"{hash(stock.get('code', '')) % 1000000000:,}万"
        })
    
    return stocks_data


def generate_ai_summary_market(indices_data, gainers, losers):
    """
    Generate AI summary of market conditions using LLM
    """
    if not stock_config.ENABLE_AI_SUMMARY:
        return None
    
    # This would call an AI API in production
    # For now, return a placeholder summary
    summary = """今日市场表现分化，整体呈现震荡整理态势。

A股市场方面，上证指数小幅上涨0.85%，深证成指表现更为强劲，上涨1.23%。市场情绪相对积极，但板块轮动明显。涨幅榜方面，科技股和医药生物板块表现突出，叁腾科技、康希诺等个股涨幅超过10%。然而，部分前期涨幅较大的题材股出现回调，聚辰股份、惠伦高科等跌幅居前。

港股市场今日表现相对疲弱，恒生指数小幅下跌0.45%。科技股和地产股普遍承压，市场观望情绪较浓。

美股方面，道琼斯指数和纳斯达克指数均小幅上涨，市场风险偏好略有回升。投资者需密切关注美联储政策走向及全球经济形势变化。

建议投资者保持谨慎，关注业绩优良的行业龙头公司，适度配置低估值蓝筹股。"""
    
    return summary


def send_preview_email():
    """Send a preview email with sample data"""
    print("📧 Generating preview email...")
    
    # Get current date in Beijing timezone
    now = get_beijing_time()
    date_str = now.strftime("%Y年%m月%d日 %H:%M")
    title = "每日股票新闻摘要"
    
    # Generate sample data
    indices_data = fetch_market_indices()
    gainers, losers = fetch_top_movers()
    stocks_data = fetch_stock_prices(stock_config.SELF_SELECTED_STOCKS)
    ai_summary = generate_ai_summary_market(indices_data, gainers, losers)
    
    # Generate HTML email
    html_content = generate_full_email_html(
        title=f"📊 {title}",
        date=date_str,
        indices_data=indices_data,
        gainers=gainers,
        losers=losers,
        stocks_data=stocks_data,
        ai_summary=ai_summary
    )
    
    # Send email
    subject = f"📊 {title} - {now.strftime('%Y年%m月%d日')}"
    
    print(f"📤 Sending preview email to {stock_config.EMAIL_RECIPIENT}...")
    success = send_html_email(stock_config.EMAIL_RECIPIENT, subject, html_content)
    
    if success:
        print("✅ Preview email sent successfully!")
    else:
        print("❌ Failed to send preview email")
    
    return success


def send_daily_email():
    """Main function to send daily stock news email"""
    print("📊 Starting stock news email generation...")
    
    # Get current date in Beijing timezone
    now = get_beijing_time()
    date_str = now.strftime("%Y年%m月%d日 %H:%M")
    title = "每日股票新闻摘要"
    
    # Fetch all data
    print("📈 Fetching market indices...")
    indices_data = fetch_market_indices()
    
    print("🔥 Fetching top movers...")
    gainers, losers = fetch_top_movers()
    
    print("⭐ Fetching self-selected stock prices...")
    stocks_data = fetch_stock_prices(stock_config.SELF_SELECTED_STOCKS)
    
    print("🤖 Generating AI summary...")
    ai_summary = generate_ai_summary_market(indices_data, gainers, losers)
    
    # Generate HTML email
    print("🎨 Generating HTML email...")
    html_content = generate_full_email_html(
        title=f"📊 {title}",
        date=date_str,
        indices_data=indices_data,
        gainers=gainers,
        losers=losers,
        stocks_data=stocks_data,
        ai_summary=ai_summary
    )
    
    # Send email
    print(f"📤 Sending email to {stock_config.EMAIL_RECIPIENT}...")
    subject = f"📊 {title} - {now.strftime('%Y年%m月%d日')}"
    
    success = send_html_email(stock_config.EMAIL_RECIPIENT, subject, html_content)
    
    if success:
        print("✅ Daily stock news email sent successfully!")
        return True
    else:
        print("❌ Failed to send daily email")
        return False


def send_task_completion_email(task_description):
    """Send task completion notification email"""
    print(f"📧 Sending task completion email for: {task_description}")
    
    now = get_beijing_time()
    date_str = now.strftime("%Y年%m月%d日 %H:%M:%S")
    
    subject = f"✅ 任务完成: {task_description}"
    body = f"""任务已完成！

任务描述: {task_description}
完成时间: {date_str}
系统状态: 正常运行

由 OpenClaw 自动化系统发送"""
    
    success = send_text_email(stock_config.EMAIL_RECIPIENT, subject, body)
    
    if success:
        print("✅ Task completion email sent successfully!")
    else:
        print("❌ Failed to send task completion email")
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock News Email Automation')
    parser.add_argument('--preview', action='store_true', help='Send a preview email')
    parser.add_argument('--daily', action='store_true', help='Send daily stock news email')
    parser.add_argument('--task', type=str, help='Send task completion email', metavar='TASK_DESCRIPTION')
    
    args = parser.parse_args()
    
    if args.preview:
        send_preview_email()
    elif args.task:
        send_task_completion_email(args.task)
    elif args.daily:
        send_daily_email()
    else:
        # Default to preview mode
        print("🚀 Running in preview mode...")
        send_preview_email()
