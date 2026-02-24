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

# 2. 检查 Python 依赖
if ! python3 -c "import flask" 2>/dev/null; then
    echo "正在安装 Python 依赖..."
    pip3 install flask flask-socketio werkzeug -q
fi

# 3. 创建数据目录
mkdir -p "$DATA_DIR"

# 4. 生成随机密码
PASSWORD=$(openssl rand -hex 8)
echo "{\"password\": \"$PASSWORD\"}" > "$DATA_DIR/clawos_password.json"

# 加载密码的函数（install.sh 和 CLI 共用）
load_password() {
    if [ -f "$DATA_DIR/clawos_password.json" ]; then
        python3 -c "import json; print(json.load(open('$DATA_DIR/clawos_password.json'))['password'])"
    fi
}

# 5. 安装 CLI
cat > "$BIN_FILE" << 'CLAWOS_EOF'
#!/bin/bash
# ClawOS CLI

APP_DIR="$HOME/clawos"
DATA_DIR="$HOME/.local/clawos"
PID_FILE="$DATA_DIR/clawos.pid"
LOG_FILE="/tmp/clawos.log"

load_password() {
    if [ -f "$DATA_DIR/clawos_password.json" ]; then
        python3 -c "import json; print(json.load(open('$DATA_DIR/clawos_password.json'))['password'])"
    fi
}

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "已在运行 (PID: $(cat $PID_FILE))"
            exit 0
        fi
        export AUTH_PASSWORD=$(load_password)
        cd "$APP_DIR" && nohup python3 app.py >> "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 1
        if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "启动成功 (PID: $(cat $PID_FILE))"
        else
            echo "启动失败，请检查日志: tail $LOG_FILE"
            rm -f "$PID_FILE"
            exit 1
        fi
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            kill $(cat "$PID_FILE") 2>/dev/null || true
            rm -f "$PID_FILE"
            echo "已停止"
        else
            echo "未运行"
        fi
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    status)
        echo "=== ClawOS 状态 ==="
        echo "安装位置: $APP_DIR"
        echo "配置目录: $DATA_DIR"
        echo "日志路径: $LOG_FILE"
        echo "CLI 位置: $0"
        echo "访问端口: 6002"
        echo ""
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "运行状态: 运行中 (PID: $(cat $PID_FILE))"
            echo "访问地址: http://localhost:6002"
        else
            echo "运行状态: 未运行"
        fi
        echo ""
        echo "登录密码: $(load_password)"
        ;;
    log)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "日志文件不存在: $LOG_FILE"
        fi
        ;;
    password)
        cat "$DATA_DIR/clawos_password.json"
        ;;
    *)
        echo "用法: clawos {start|stop|restart|status|log|password}"
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
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

[Install]
WantedBy=default.target
EOF

# 7. 启用服务
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable clawos.service 2>/dev/null || true

echo ""
echo "=== 安装完成 ==="
echo ""

# 8. 显示状态（包含密码）
clawos status
