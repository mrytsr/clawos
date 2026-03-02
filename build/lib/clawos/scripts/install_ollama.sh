#!/bin/bash

# Ollama 安装脚本 - 带进度显示

set -e

echo "=========================================="
echo "       Ollama 安装脚本"
echo "=========================================="
echo ""

# 检查是否已安装
if command -v ollama &> /dev/null; then
    echo "✅ Ollama 已安装: $(ollama --version)"
    exit 0
fi

# 检测架构
ARCH=$(uname -m)
echo "📋 检测到架构: $ARCH"

case $ARCH in
    x86_64)
        OLLAMA_ARCH="amd64"
        ;;
    aarch64|arm64)
        OLLAMA_ARCH="arm64"
        ;;
    *)
        echo "❌ 不支持的架构: $ARCH"
        exit 1
        ;;
esac

# 下载链接
OLLAMA_VERSION="0.5.6"
DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-${OLLAMA_ARCH}"

echo ""
echo "📥 开始下载 Ollama v${OLLAMA_VERSION}..."
echo "   URL: $DOWNLOAD_URL"
echo ""

# 下载并显示进度
curl -L --progress-bar -o /tmp/ollama "$DOWNLOAD_URL"

echo ""
echo "📦 下载完成，正在安装..."

# 安装
chmod +x /tmp/ollama
sudo mv /tmp/ollama /usr/local/bin/ollama

# 创建用户组（如果需要）
echo ""
echo "⚙️ 配置 Ollama..."

# 创建 ollama 用户组（如果不存在）
sudo groupadd -f ollama 2>/dev/null || true

# 配置环境变量
OLLAMA_DIR="$HOME/.ollama"
mkdir -p "$OLLAMA_DIR"

# 创建环境变量配置
cat > /tmp/ollama.env << 'EOF'
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS=/root/.ollama/models
OLLAMA_KEEP_ALIVE=24h
EOF

sudo mv /tmp/ollama.env /etc/ollama.env 2>/dev/null || \
    mv /tmp/ollama.env "$OLLAMA_DIR/ollama.env"

echo ""
echo "🔧 配置 systemd 服务..."

# 创建 systemd 服务文件
sudo tee /etc/systemd/system/ollama.service > /dev/null << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/local/bin/ollama serve
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用并启动服务
echo ""
echo "🚀 启动 Ollama 服务..."
sudo systemctl enable ollama
sudo systemctl start ollama

# 等待服务启动
sleep 2

# 验证安装
echo ""
echo "=========================================="
echo "✅ 安装完成！"
echo "=========================================="
echo ""
echo "📋 服务状态:"
systemctl status ollama --no-pager | head -5
echo ""
echo "📝 使用方法:"
echo "   启动服务: sudo systemctl start ollama"
echo "   停止服务: sudo systemctl stop ollama"
echo "   查看状态: sudo systemctl status ollama"
echo "   查看日志: sudo journalctl -u ollama -f"
echo ""
echo "🔗 默认地址: http://localhost:11434"
echo ""
echo "📦 模型存放位置: ~/.ollama/models"
echo ""
