# Stock News Email Configuration - Global Top 20 Companies
# /home/tjx/.openclaw/workspace/clawos/config/stock_config.py

# Global Top 20 Companies by Market Capitalization (as of early 2025)
TOP20_MARKET_CAP = [
    {"code": "AAPL", "name": "苹果", "market": "US", "exchange": "NASDAQ"},
    {"code": "MSFT", "name": "微软", "market": "US", "exchange": "NASDAQ"},
    {"code": "NVDA", "name": "英伟达", "market": "US", "exchange": "NASDAQ"},
    {"code": "GOOGL", "name": "谷歌A", "market": "US", "exchange": "NASDAQ"},
    {"code": "GOOG", "name": "谷歌C", "market": "US", "exchange": "NASDAQ"},
    {"code": "AMZN", "name": "亚马逊", "market": "US", "exchange": "NASDAQ"},
    {"code": "META", "name": "Meta", "market": "US", "exchange": "NASDAQ"},
    {"code": "TSLA", "name": "特斯拉", "market": "US", "exchange": "NASDAQ"},
    {"code": "BRK.B", "name": "伯克希尔B", "market": "US", "exchange": "NYSE"},
    {"code": "LLY", "name": "礼来", "market": "US", "exchange": "NYSE"},
    {"code": "AVGO", "name": "博通", "market": "US", "exchange": "NASDAQ"},
    {"code": "V", "name": "Visa", "market": "US", "exchange": "NYSE"},
    {"code": "JPM", "name": "摩根大通", "market": "US", "exchange": "NYSE"},
    {"code": "WMT", "name": "沃尔玛", "market": "US", "exchange": "NYSE"},
    {"code": "XOM", "name": "埃克森美孚", "market": "US", "exchange": "NYSE"},
    {"code": "MA", "name": "万事达", "market": "US", "exchange": "NYSE"},
    {"code": "JNJ", "name": "强生", "market": "US", "exchange": "NYSE"},
    {"code": "UNH", "name": "联合健康", "market": "US", "exchange": "NYSE"},
    {"code": "PG", "name": "宝洁", "market": "US", "exchange": "NYSE"},
    {"code": "HD", "name": "家得宝", "market": "US", "exchange": "NYSE"},
]

# Email settings
EMAIL_RECIPIENT = "mrytsr@qq.com"

# AI Summary settings
ENABLE_AI_SUMMARY = True
AI_MODEL = "opencode/minimax-m2.1-free"

# Market indices to track (US, Hong Kong, China)
MARKET_INDICES = {
    "道琼斯": "us030114",
    "纳斯达克": "us030115",
    "标普500": "us030113",
    "恒生指数": "hs300759",
    "上证指数": "sh000001",
    "深证成指": "sz399001",
}

# Email settings
EMAIL_SUBJECT_PREFIX = "📊 全球市值前20"
SEND_TIME = "08:00"

# Web scraping settings
# Use Yahoo Finance for US stocks, Eastmoney for HK/China stocks