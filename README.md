# 🖥️ PyWebDeck
# 🖥️ PyWebDeck
一个基于 Flask + SocketIO 的单文件 Linux 网页管理器。支持文件管理、Web 终端、代码编辑和 AI 助手集成。
A single-file Linux web manager based on Flask + SocketIO. Features file management, web terminal, code editing, and AI assistant integration.
![License](https://img.shields.io/badge/License-MIT-blue.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-green.svg)
![Python](https://img.shields.io/badge/Python-3.8+-green.svg)
## ✨ 特性
## ✨ Features
- 📂 **全功能文件管理**：浏览、上传、下载、重命名、移动、删除、克隆
- 📂 **Full-featured File Management**: Browse, upload, download, rename, move, delete, clone
- 🖥️ **Web 终端**：基于 xterm.js 的完整 Shell 体验，支持颜色和快捷键
- 🖥️ **Web Terminal**: Complete Shell experience based on xterm.js with color and shortcut support
- 🤖 **AI 助手集成**：内置悬浮聊天机器人，支持上下文对话
- 🤖 **AI Assistant Integration**: Built-in floating chat bot with context-aware conversation
- 📱 **移动端优化**：针对手机触屏优化的交互设计
- 📱 **Mobile Optimized**: Touch-friendly interaction design for mobile devices
- ⚡ **单文件部署**：所有代码和模板集成在一个 `.py` 文件中，即拷即用
- ⚡ **Single-file Deployment**: All code and templates integrated in one `.py` file
## 🚀 快速开始
## 🚀 Quick Start
### 环境准备
### Prerequisites
```bash
# 安装依赖 / Install dependencies
pip install -r requirements.txt
```
### 运行
### Run
```bash
# 设置管理目录（可选，默认为当前目录或 /root/clawd） / Set root directory (optional, defaults to current directory or /root/clawd)
export ROOT_DIR=/your/path
# 启动服务 / Start the service
python3 app.py
```
访问 `http://your-server:6002`，使用默认账号登录：
Visit `http://your-server:6002` and login with default credentials:
- **用户名**：`admin`
- **Username**: `admin`
- **密码**：`admin`
- **Password**: `admin`
### Docker 部署
### Docker Deployment
```bash
docker run -d -p 6002:6002 -v /:/data --name pywebdeck pywebdeck-image
```
## 📖 功能说明
## 📖 Features
### 文件管理
### File Management
- 双击/点击进入目录
- Click to enter directories
- 点击行号复制文件路径
- Click line numbers to copy file paths
- 点击右侧菜单进行重命名、移动、删除等操作
- Use the right-side menu for rename, move, delete, etc.
- 支持图片缩略图预览
- Thumbnail preview for images
### Web 终端
### Web Terminal
- 点击文件右侧菜单 → **在终端打开**
- Click file menu → **Open in Terminal**
- 支持常用命令：`ls`, `cd`, `vim`, `git` 等
- Supports common commands: `ls`, `cd`, `vim`, `git`, etc.
- 支持复制粘贴（Ctrl+C/V）
- Copy/Paste support (Ctrl+C/V)
### AI 助手
### AI Assistant
- 点击右下角 🤖 图标打开对话窗口
- Click 🤖 icon to open chat window
- 可配置 Gateway Token 连接外部 AI 服务
- Configure Gateway Token to connect external AI service
- 支持上下文对话
- Context-aware conversation support
## ⚙️ 配置项
## ⚙️ Configuration
- 环境变量：`ROOT_DIR` — 管理的根目录（默认 `/root/clawd`）
- Environment variable: `ROOT_DIR` — Root directory to manage (default `/root/clawd`)
## 🔒 安全提示
## 🔒 Security Notes
- **务必修改默认密码！**
- **Change the default password!**
- 仅在可信网络环境使用，或配置 VPN/防火墙限制访问
- Use only in trusted network environments or with VPN/firewall protection
- 终端拥有 Root 权限，请谨慎操作
- Terminal has Root permissions, please operate with caution
## ⚠️ 免责声明
## ⚠️ Disclaimer
本软件按“原样”提供，不提供任何明示或暗示的保证，包括但不限于对适销性、特定用途适用性或非侵权性的暗示保证。
This software is provided "as is" without any warranty, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.
使用本软件对服务器进行的所有操作（包括但不限于文件管理、终端执行命令等）由使用者自行承担风险。对于因使用本软件而导致的任何数据丢失、系统损坏或其他任何损失，作者不承担任何责任。
All operations performed on the server using this software (including but not limited to file management and terminal command execution) are at the user's own risk. The author is not responsible for any data loss, system damage, or other losses resulting from the use of this software.
**请勿在生产环境或公网环境直接暴露本服务**，建议配置防火墙、强密码认证和 HTTPS 加密。
**Do not expose this service directly in production environments or on the public internet.** It is recommended to configure firewall, strong password authentication, and HTTPS encryption.
## 📂 项目结构
## 📂 Project Structure
```text
6002_file_manager/
├── app.py              # 主程序（单文件应用） / Main program (single-file application)
├── README.md           # 本文档（中英合并） / This document (Chinese + English)
├── requirements.txt    # Python 依赖 / Python dependencies
└── ...
```
## 📝 更新日志
## 📝 Changelog
**v1.0** (2026-02-01)
**v1.0** (2026-02-01)
- 初始版本发布
- Initial release
- 支持文件管理、Web 终端、AI 助手
- File management, web terminal, AI assistant support
- 移动端适配优化
- Mobile optimization
## 📄 License
## 📄 License
MIT License
MIT License
