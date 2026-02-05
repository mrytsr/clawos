# 🖥️ ClawOS / PyWebDeck

一个基于 Flask + SocketIO 的 Web 管理面板，主要用于在浏览器里进行文件管理、批量操作、预览与 Web 终端操作。支持 Windows/Linux。

A Flask + SocketIO based web management panel for file management, batch operations, preview, and a web terminal. Works on both Windows and Linux.

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-green.svg)

---

## ✨ 功能概览（中文）

- 📂 文件管理：浏览、上传、下载、重命名、移动、删除、克隆
- ✅ 批量操作：多选、批量删除、批量复制/剪切（通过悬浮剪贴板条粘贴到当前目录）
- 📌 悬浮剪贴板条：复制/剪切后底部提示“在此粘贴…”，支持粘贴/取消，支持多文件列表
- 🔍 搜索：文件搜索抽屉
- 👁️ 预览：图片缩略图、文本/Markdown 预览（根据模板页面）
- 🖥️ Web 终端：基于 xterm.js + SocketIO 的交互终端
- 🤖 AI 助手：内置对话抽屉（可配置 Token，具体取决于你的网关服务）
- 📱 移动端适配：抽屉式交互与响应式样式

## 🚀 安装与运行（中文）

### 1) 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2) 启动服务

```bash
python app.py
```

默认监听端口：`6002`。浏览器打开：

```
http://127.0.0.1:6002/
```

### 3) （可选）配置环境变量

本项目通过环境变量控制根目录和端口：

- `ROOT_DIR`：管理的根目录（默认是项目目录的上一级目录）
- `SERVER_PORT`：服务端口（默认 `6002`）

Linux/macOS:

```bash
export ROOT_DIR=/your/path
export SERVER_PORT=6002
python app.py
```

Windows PowerShell:

```powershell
$env:ROOT_DIR="C:\\your\\path"
$env:SERVER_PORT="6002"
python app.py
```

### 4) 登录

默认账号（建议启动后立即修改认证逻辑或加反向代理鉴权）：

- 用户名：`admin`
- 密码：`admin`

---

## 🧪 测试与代码质量（可选）

项目提供了前端 JS 的 lint / unit / e2e 测试脚本（需要安装 Node.js）。

```bash
npm install
npm run lint
npm test
npm run test:e2e
```

Playwright e2e 初次运行可能需要安装浏览器：

```bash
npx playwright install
```

---

## 🔒 安全提示（中文）

- 请勿把服务直接暴露到公网（默认账号密码为 `admin/admin`）。
- 推荐只在可信内网使用，或在反向代理（Nginx/Caddy）后加 HTTPS 与强认证。
- Web 终端具备执行命令能力，请谨慎授权与隔离运行环境。

---

## ✨ Features (English)

- 📂 File management: browse, upload, download, rename, move, delete, clone
- ✅ Batch operations: multi-select, batch delete, batch copy/cut (paste via a floating clipboard bar)
- 📌 Floating clipboard bar: shows “Paste here …” after copy/cut, supports paste/cancel, supports multiple paths
- 🔍 Search: drawer-based search UI
- 👁️ Preview: thumbnails and viewers (image / text / markdown depending on templates)
- 🖥️ Web terminal: xterm.js + SocketIO interactive terminal
- 🤖 AI assistant: built-in chat drawer (depends on your gateway/token setup)
- 📱 Mobile friendly: drawer-based interactions and responsive layout

## 🚀 Install & Run (English)

### 1) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2) Run the server

```bash
python app.py
```

Open:

```
http://127.0.0.1:6002/
```

### 3) (Optional) Environment variables

- `ROOT_DIR`: root directory to manage (defaults to the parent directory of this project)
- `SERVER_PORT`: server port (default `6002`)

Linux/macOS:

```bash
export ROOT_DIR=/your/path
export SERVER_PORT=6002
python app.py
```

Windows PowerShell:

```powershell
$env:ROOT_DIR="C:\\your\\path"
$env:SERVER_PORT="6002"
python app.py
```

### 4) Login

Default credentials:

- Username: `admin`
- Password: `admin`

---

## 📄 License

MIT
