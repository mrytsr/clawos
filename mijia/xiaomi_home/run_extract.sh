#!/bin/bash
#
# Xiaomi Device Extractor - 输入验证码后自动完成
#
# 使用方法:
#   cd /home/tjx/.openclaw/workspace/xiandan/xiaomi_home
#   bash run_extract.sh
#
# 流程:
#   1. 自动开始登录
#   2. 等待你输入验证码
#   3. 自动完成并保存到 /home/tjx/.openclaw/workspace/mijia/devices.json
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="/home/tjx/.openclaw/workspace/mijia/devices.json"
LOG_FILE="/home/tjx/.openclaw/workspace/mijia/extract.log"

echo "========================================"
echo "Xiaomi Device Extractor"
echo "========================================"
echo ""

# 读取账号
if [ -f /home/tjx/.openclaw/workspace/mijia/account.md ]; then
    USERNAME=$(grep "^user " /home/tjx/.openclaw/workspace/mijia/account.md | sed 's/user //' | tr -d '\n\r')
    PASSWORD=$(grep "^pass " /home/tjx/.openclaw/workspace/mijia/account.md | sed 's/pass //' | tr -d '\n\r')
    echo "📱 账号: $USERNAME"
else
    echo "❌ 找不到 /home/tjx/.openclaw/workspace/mijia/account.md"
    exit 1
fi

echo ""
echo "⏳ 启动登录..."
echo ""

# 运行提取脚本
python3 "$SCRIPT_DIR/scripts/token_extractor.py" \
    -u "$USERNAME" \
    -p "$PASSWORD" \
    -s "cn" \
    -o "$OUTPUT_FILE" 2>&1 | tee "$LOG_FILE"

echo ""
echo "========================================"

# 检查结果
if [ -f "$OUTPUT_FILE" ]; then
    COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_FILE'))['devices']))" 2>/dev/null || echo "?")
    echo "✅ 完成!"
    echo "📁 文件: $OUTPUT_FILE"
    echo "📊 设备: $COUNT 台"
else
    echo "⚠️ 未生成输出文件"
    echo "📄 日志: $LOG_FILE"
fi

echo "========================================"
