#!/bin/bash
#
# Xiaomi Device Extractor - Run Once
# 运行一次自动完成登录并保存设备列表
#
# 使用方法:
#   cd /home/tjx/.openclaw/workspace/xiandan/xiaomi_home
#   bash run_once.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="/home/tjx/.openclaw/workspace/mijia/devices.json"
LOG_FILE="/home/tjx/.openclaw/workspace/mijia/extract.log"

echo "========================================"
echo "Xiaomi Device Extractor"
echo "========================================"
echo ""

# 读取账号
if [ -f /home/tjx/.openclaw/workspace/mijia/account.md ]; then
    USERNAME=$(grep "^user " /home/tjx/.openclaw/workspace/mijia/account.md | cut -d' ' -f2-)
    PASSWORD=$(grep "^pass " /home/tjx/.openclaw/workspace/mijia/account.md | cut -d' ' -f2-)
    
    if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
        echo "❌ 无法读取账号信息"
        exit 1
    fi
else
    echo "❌ 找不到账号文件: /home/tjx/.openclaw/workspace/mijia/account.md"
    exit 1
fi

echo "📱 账号: $USERNAME"
echo ""

# 使用expect自动处理交互
expect << EOF > "$LOG_FILE" 2>&1
set timeout 300

spawn python3 scripts/token_extractor.py -u "$USERNAME" -p "$PASSWORD" -s "cn" -o "$OUTPUT_FILE"

expect {
    "p/q:" {
        send "p\r"
        exp_continue
    }
    "验证码" {
        send "$PASSWORD\r"
        exp_continue
    }
    timeout {
        puts "超时"
        exit 1
    }
    eof {
        puts "完成"
    }
}

expect eof
EOF

RESULT=$?

if [ $RESULT -eq 0 ]; then
    if [ -f "$OUTPUT_FILE" ]; then
        COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_FILE'))))" 2>/dev/null || echo "0")
        echo ""
        echo "========================================"
        echo "✅ 完成!"
        echo "📁 输出文件: $OUTPUT_FILE"
        echo "📊 设备数量: $COUNT 台"
        echo "========================================"
    else
        echo ""
        echo "⚠️ 脚本运行完成，但输出文件未生成"
    fi
else
    echo ""
    echo "❌ 运行失败，请查看日志: $LOG_FILE"
fi
