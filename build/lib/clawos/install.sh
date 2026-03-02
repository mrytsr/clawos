#!/bin/bash
# ClawOS 安装脚本

set -e

CLAWOS_DIR="$HOME/clawos"
DATA_DIR="$HOME/.local/clawos"
BIN_FILE="/usr/local/bin/clawos"
LOG_FILE="/tmp/clawos.log"

echo "=== ClawOS 安装 ==="

# 1. 检查源码目录
if [ ! -d "$CLAWOS_DIR" ]; then
    echo "错误: 源码目录不存在: $CLAWOS_DIR"
    echo "请先 clone 项目到 $CLAWOS_DIR"
    exit 1
fi

# 2. 检查并安装 Python 依赖
if ! python3 -c "import flask" 2>/dev/null; then
    echo "正在安装 Python 依赖..."
    pip3 install -r "$CLAWOS_DIR/requirements.txt" -q
fi

# 3. 创建数据目录
mkdir -p "$DATA_DIR"

# 4. 生成随机密码
PASSWORD=$(openssl rand -hex 8)
echo "{\"password\": \"$PASSWORD\"}" > "$DATA_DIR/clawos_password.json"

# 加载密码的函数
load_password() {
    if [ -f "$DATA_DIR/clawos_password.json" ]; then
        python3 -c "import json; print(json.load(open('$DATA_DIR/clawos_password.json'))['password'])"
    fi
}

# 5. 安装 CLI（使用 systemd 管理）
cat > "$BIN_FILE" << 'CLAWOS_EOF'
#!/bin/bash
# ClawOS CLI - 使用 systemd 管理

APP_DIR="$HOME/clawos"
DATA_DIR="$HOME/.local/clawos"
LOG_FILE="/tmp/clawos.log"

load_password() {
    if [ -f "$DATA_DIR/clawos_password.json" ]; then
        python3 -c "import json; print(json.load(open('$DATA_DIR/clawos_password.json'))['password'])"
    fi
}

case "$1" in
    start)
        systemctl --user start clawos
        sleep 1
        if systemctl --user is-active --quiet clawos; then
            echo "启动成功"
            echo "访问地址: http://localhost:6002"
        else
            echo "启动失败，请检查日志: journalctl --user -u clawos -e"
            exit 1
        fi
        ;;
    stop)
        systemctl --user stop clawos
        echo "已停止"
        ;;
    restart)
        systemctl --user restart clawos
        echo "已重启"
        ;;
    status)
        echo "=== ClawOS 状态 ==="
        echo "安装位置: $APP_DIR"
        echo "配置目录: $DATA_DIR"
        echo "日志命令: journalctl --user -u clawos -f"
        echo "CLI 位置: $0"
        echo "访问端口: 6002"
        echo ""
        if systemctl --user is-active --quiet clawos; then
            echo "运行状态: 运行中"
            echo "访问地址: http://localhost:6002"
        else
            echo "运行状态: 未运行"
        fi
        echo ""
        echo "登录密码: $(load_password)"
        ;;
    log)
        journalctl --user -u clawos -f
        ;;
    enable)
        systemctl --user enable clawos
        echo "已启用开机自启"
        ;;
    disable)
        systemctl --user disable clawos
        echo "已禁用开机自启"
        ;;
    password)
        cat "$DATA_DIR/clawos_password.json"
        ;;
    *)
        echo "用法: clawos {start|stop|restart|status|log|enable|disable|password}"
        exit 1
        ;;
esac
CLAWOS_EOF
chmod +x "$BIN_FILE"

# 6. 安装 systemd 服务
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/clawos.service" << EOF
[Unit]
Description=ClawOS Web Panel
After=network.target

[Service]
Type=simple
WorkingDirectory=$CLAWOS_DIR
ExecStart=/usr/bin/python3 $CLAWOS_DIR/app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# 7. 重新加载并启用服务
systemctl --user daemon-reload
systemctl --user enable clawos.service

# 8. 启动服务
systemctl --user start clawos

echo ""
echo "=== 安装完成 ==="
echo ""

# 9. 显示状态（包含密码）
clawos status
