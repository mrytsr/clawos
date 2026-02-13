#!/bin/bash
#
# Xiaomi Device Extractor - Semi-Auto
# 半自动版本：用户输入验证码后自动完成
#
# 使用方法:
#   cd /home/tjx/.openclaw/workspace/xiandan/xiaomi_home
#   bash run.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="/home/tjx/.openclaw/workspace/mijia/devices.json"
ACCOUNT_FILE="/home/tjx/.openclaw/workspace/mijia/account.md"

echo "========================================"
echo "Xiaomi Device Extractor"
echo "========================================"
echo ""

# 检查expect
if ! command -v expect &> /dev/null; then
    echo "ℹ️  未安装expect，使用半自动模式"
    echo ""
    echo "使用方法:"
    echo "  1. 运行: python3 scripts/token_extractor.py"
    echo "  2. 选择登录方式 (p 或 q)"
    echo "  3. 输入验证码"
    echo "  4. 完成后告诉我"
    echo ""
    echo "或者直接运行:"
    echo "  python3 scripts/token_extractor.py -u \"\$账号\" -p \"\$密码\" -s cn -o $OUTPUT_FILE"
    echo ""
    exit 0
fi

# 读取账号
if [ -f "$ACCOUNT_FILE" ]; then
    USERNAME=$(grep "^user " "$ACCOUNT_FILE" | sed 's/user //' | tr -d '\r')
    PASSWORD=$(grep "^pass " "$ACCOUNT_FILE" | sed 's/pass //' | tr -d '\r')
else
    echo "❌ 找不到账号文件"
    exit 1
fi

echo "📱 账号: $USERNAME"
echo ""
echo "⏳ 启动登录流程..."
echo ""

# 使用expect自动处理
expect << EOF > /tmp/expect.log 2>&1
set timeout 300

spawn python3 scripts/token_extractor.py -u "$USERNAME" -p "$PASSWORD" -s "cn" -o "$OUTPUT_FILE"

expect {
    "p/q:" {
        send "p\r"
        exp_continue
    }
    "Username*" {
        send "$USERNAME\r"
        exp_continue
    }
    "Password*" {
        send "$PASSWORD\r"
        exp_continue
    }
    "Captcha*" {
        puts "\n需要验证码，请查看邮箱后输入\n"
    }
    "code:" {
        puts "\n请输入验证码:\n"
    }
    timeout {
        puts "\n超时"
        exit 1
    }
    eof {
        puts "\n登录流程完成"
    }
}

expect {
    timeout 120 { puts "\n等待验证码输入超时\n"; exit 1 }
    "Press ENTER*" {
        send "\r"
    }
    eof {
        puts "\n脚本退出"
    }
}

expect eof
catch wait status
exit [lindex \$status 3]
EOF

RESULT=$?

echo ""
echo "日志: /tmp/expect.log"

if [ -f "$OUTPUT_FILE" ]; then
    echo ""
    echo "========================================"
    echo "✅ 完成!"
    echo "📁 输出: $OUTPUT_FILE"
    echo "========================================"
else
    echo ""
    echo "⚠️ 输出文件未生成"
    echo "   请查看日志: /tmp/expect.log"
fi
