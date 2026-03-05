# ClawOS

<p align="center">
  <img src="imgs/icon.jpg" width="120" alt="ClawOS" />
</p>

<p align="center">
  A browser-based Linux management panel: file management, system monitoring, web terminal, and service management.
</p>

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-blue.svg" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-green.svg" />
</p>

- One-command start: `clawos start`, then manage everything in the browser
- File management: upload/download, drag-and-drop upload, batch operations, trash, search
- System & services: processes, systemd, Docker, network, disks, GPU (optional)
- Built-in tools: Git, editor, log viewer, task queue

## Quick Start

### Requirements

- Linux with systemd user services (`systemctl --user`)
- Python 3.9+

### Install

```bash
pip install clawos
```

### Start

```bash
clawos start
```

Open in your browser:

- http://localhost:6002

Check the login password:

```bash
clawos status
clawos password
```

Stop the service:

```bash
clawos stop
```

## Screenshots

| | | |
|---|---|---|
| <img src="imgs/20260225-110434.jpg" width="320" alt="ClawOS Screenshot 1" /> | <img src="imgs/20260225-110441.jpg" width="320" alt="ClawOS Screenshot 2" /> | <img src="imgs/20260225-110446.jpg" width="320" alt="ClawOS Screenshot 3" /> |
| <img src="imgs/20260225-110451.jpg" width="320" alt="ClawOS Screenshot 4" /> | <img src="imgs/20260225-110456.jpg" width="320" alt="ClawOS Screenshot 5" /> | <img src="imgs/20260225-110500.jpg" width="320" alt="ClawOS Screenshot 6" /> |
| <img src="imgs/20260225-110505.jpg" width="320" alt="ClawOS Screenshot 7" /> | <img src="imgs/20260225-110510.jpg" width="320" alt="ClawOS Screenshot 8" /> | <img src="imgs/20260225-110514.jpg" width="320" alt="ClawOS Screenshot 9" /> |
| <img src="imgs/20260227-123006.jpg" width="320" alt="ClawOS Screenshot 10" /> |  |  |

## Documentation

- API: [docs/api.md](docs/api.md)
- Protocol: [docs/PROTOCOL.md](docs/PROTOCOL.md)

## Community

- Discord: https://discord.gg/4PW8pEazm
- QQ Group: 485345801 (scan to join)

<img src="imgs/qq_group_qr.png" width="280" alt="QQ Group QR Code" />

## Contributing

Issues and pull requests are welcome.

## Security Features

- Password-based authentication
- Session management
- Path traversal protection
- File operation permissions
- Symlink safety checks

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          ClawOS Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Browser Client                       │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │   │ File Browser │  │  Terminal   │  │ Sys Monitor  │      │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                 │
│                 HTTP / WebSocket (REST API)                     │
│                              │                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                        Flask Server                        │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │   │  Blueprints  │  │  Socket.IO  │  │    Auth     │      │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Service Controllers                   │   │
│  │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │   │
│  │   │ Files  │ │ System │ │  Git   │ │ Docker │            │   │
│  │   └────────┘ └────────┘ └────────┘ └────────┘            │   │
│  │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │   │
│  │   │  FRP   │ │ Clash  │ │OpenClaw│ │ Terminal│            │   │
│  │   └────────┘ └────────┘ └────────┘ └────────┘            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                 │
│              ┌───────────────┼───────────────┐                │
│              ▼               ▼               ▼                │
│      ┌──────────────┐  ┌───────────┐  ┌──────────────┐       │
│      │ Local FS      │  │ systemd   │  │ External Svcs │       │
│      └──────────────┘  └───────────┘  └──────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 📂 File Management

- Hierarchical navigation
- Upload/download (drag-and-drop supported)
- Create folders, rename, move, delete, clone
- Multi-select operations
- Batch operations (copy/move/delete)
- Trash and restore
- File search and filtering
- Symlink detection and handling
- Broken symlink visualization

### 📝 Multi-format Editors

- **JSON editor**: syntax highlighting, validation, tree/text/table modes
- **YAML/TOML editor**: Monaco Editor
- **Markdown preview**: live rendering
- **Code editor**: multi-language support
- **Config editors**: INI/CONF/XML support

### 🖥️ Web Terminal

- Full xterm.js terminal emulator
- Socket.IO real-time transport
- Command history navigation
- Session persistence

### 📊 System Monitoring

- CPU usage and memory statistics
- Process list (sortable)
- Disk usage
- Network interface stats
- GPU info (NVIDIA)
- Docker container management
- systemd service management

### 🤖 Service Management

#### FRP

```
┌─────────────────────────────────────┐
│  🌐 FRP Tunnel                       │
├─────────────────────────────────────┤
│  Service status: ● Running           │
│                                     │
│  Server: your-frp-server:17777      │
│                                     │
│  Proxies:                           │
│  - test-tcp (22 → 6022)             │
│  - http (80 → 6080)                 │
│  - 18789 (18789 → 18789)            │
│  - 5001 (5001 → 15001)              │
│  - 6002 (6002 → 6002)               │
│                                     │
│  [Start] [Stop] [Restart]           │
│  [Edit Config]                      │
└─────────────────────────────────────┘
```

#### Clash

```
┌─────────────────────────────────────┐
│  🌐 Clash Proxy                      │
├─────────────────────────────────────┤
│  Service status: ● Running           │
│                                     │
│  Port: 7890 (mixed port)            │
│                                     │
│  📡 Subscription                     │
│  [Enter URL] [Update]               │
│                                     │
│  🎯 Proxy Groups                     │
│  - Example Group → HK 01             │
│  - Auto Select  → HK 02              │
│                                     │
│  📡 Nodes: 12                        │
│  📊 Rules: 514                       │
└─────────────────────────────────────┘
```

#### OpenClaw Integration

- Gateway status monitoring
- Agent management
- Channel configuration
- Skills installation tracking
- Health diagnostics

### 🐙 Git Integration

- Repository browser
- Branch management
- Commit history viewer
- Diff visualization
- Status bar integration

## Installation (from source via install.sh)

### Requirements

- Linux with systemd user services (`systemctl --user`)
- `python3`, `pip3`, `git`, `openssl`

### 1) Clone to the script-default path

The installation script assumes the source directory is `~/clawos` by default.

```bash
git clone https://github.com/mrytsr/clawos.git ~/clawos
cd ~/clawos
```

### 2) Run the install script

```bash
bash install.sh
```

The script will:

- Install Python dependencies when needed (e.g. run `pip3 install -r ~/clawos/requirements.txt` if Flask is missing)
- Create the data directory: `~/.local/clawos`
- Generate a random password: `~/.local/clawos/clawos_password.json`
- Install the CLI to: `/usr/local/bin/clawos`
- Write the systemd user unit: `~/.config/systemd/user/clawos.service`
- Enable and start the service via `systemctl --user`

### 3) Access and manage

- Web UI: `http://127.0.0.1:6002/`
- Password: `clawos status` or `cat ~/.local/clawos/clawos_password.json`
- Logs: `journalctl --user -u clawos -f`

```bash
clawos start|stop|restart|status|log|enable|disable|password
```

### Notes

- If you don't have write permission to `/usr/local/bin`, change `BIN_FILE` in `install.sh` to `~/.local/bin/clawos` (ensure `~/.local/bin` is in `PATH`) and rerun the script.
- On headless servers, user services may stop after logout; enable linger if you need it:
  `loginctl enable-linger $USER`

## CLI Usage (pip install)

```bash
clawos start          # Start the service (installs systemd unit on first run)
clawos -h             # Show help
clawos status         # Show status
clawos stop           # Stop the service
clawos restart        # Restart the service
clawos log            # View logs
clawos uninstall      # Uninstall (stop + remove systemd unit, then pip uninstall)
```

## API Reference

### File Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/file/list` | GET | List directory contents |
| `/api/file/info` | GET | Get file/directory info |
| `/api/file/read` | GET | Read file content |
| `/api/file/save` | POST | Write file content |
| `/api/file/create` | POST | Create file/folder |
| `/api/file/move` | POST | Move/rename file |
| `/api/file/delete` | POST | Delete file |
| `/api/file/copy` | POST | Copy file |
| `/api/trash/list` | GET | List trash contents |
| `/api/trash/restore` | POST | Restore from trash |

### System Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process/list` | GET | List running processes |
| `/api/disk/list` | GET | List disk usage |
| `/api/network/list` | GET | List network interfaces |
| `/api/gpu/info` | GET | GPU information |
| `/api/system/exec` | POST | Execute system command |

### Service Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/systemd/list` | GET | List systemd services |
| `/api/systemd/control` | POST | Control service (start/stop/restart) |
| `/api/docker/containers` | GET | List Docker containers |
| `/api/docker/container/start` | POST | Start container |
| `/api/docker/container/stop` | POST | Stop container |

### FRP Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/frp/config` | GET | Get FRP configuration |
| `/api/frp/config` | POST | Save FRP configuration |

### Clash Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/clash/state` | GET | Get Clash status |
| `/api/clash/proxies` | GET | Get proxy list |
| `/api/clash/subscribe` | POST | Update subscription |
| `/api/clash/switch` | POST | Switch proxy node |

### Git Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/git/repos` | GET | List git repositories |
| `/api/git/status` | GET | Get repository status |
| `/api/git/log` | GET | Get commit history |
| `/api/git/diff` | GET | Get diff output |

## Project Structure

```
clawos/
├── app.py                    # Flask application entry point
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── package.json              # Node.js dependencies
│
├── ctrl/                     # Flask blueprints (controllers)
│   ├── api_ctrl.py           # Generic API utilities
│   ├── auth_ctrl.py          # Authentication
│   ├── batch_ctrl.py         # Batch operations
│   ├── browser_ctrl.py       # File browser API
│   ├── clash_ctrl.py         # Clash proxy management
│   ├── edit_ctrl.py          # File editing
│   ├── file_ctrl.py          # File operations
│   ├── frp_ctrl.py           # FRP management
│   ├── git_ctrl.py           # Git integration
│   ├── openclaw_ctrl.py      # OpenClaw integration
│   ├── system_ctrl.py        # System monitoring
│   ├── task_ctrl.py          # Task management
│   └── term.py               # Terminal socket handler
│
├── lib/                      # Utility modules
│   ├── ai_client.py          # AI assistant client
│   ├── disk_utils.py         # Disk utilities
│   ├── docker_utils.py       # Docker utilities
│   ├── email_utils.py        # Email utilities
│   ├── file_utils.py         # File utilities
│   ├── git_utils.py          # Git utilities
│   ├── json_utils.py         # JSON utilities
│   ├── network_utils.py      # Network utilities
│   ├── packages_utils.py     # Package management
│   ├── path_utils.py         # Path utilities
│   ├── process_utils.py      # Process utilities
│   └── systemd_utils.py      # systemd utilities
│
├── static/                   # Static assets
│   ├── js/
│   │   ├── bot.js            # AI assistant
│   │   ├── file_browser.js   # File browser
│   │   ├── file_clipboard.js # Clipboard operations
│   │   ├── globals.js        # Global utilities
│   │   ├── git.js            # Git integration
│   │   ├── preview.js        # File preview
│   │   ├── system_monitor.js # System monitoring
│   │   ├── task_actions.js   # Task actions
│   │   ├── task_poller.js    # Task polling
│   │   └── terminal.js       # Terminal
│   └── css/                  # Stylesheets
│
├── templates/                # HTML templates
│   ├── index.html            # Main application
│   ├── login.html            # Login page
│   ├── trash.html            # Trash management
│   ├── json_editor.html      # JSON editor
│   ├── yaml_editor.html      # YAML/TOML editor
│   ├── markdown.html         # Markdown preview
│   ├── code_editor.html      # Code editor
│   ├── git_commit.html       # Git commit viewer
│   └── ...
│
├── data/                     # Runtime data
│   ├── conversations.json    # Chat history
│   └── trash/                # Trash directory
│
└── README.md                 # This file
```

## Security

⚠️ **Important security notes**

1. **Default credentials**: Change the password immediately after installation
2. **Network exposure**: Do not expose ClawOS directly to the public internet
3. **Use HTTPS**: Put it behind a reverse proxy with HTTPS (Nginx/Caddy)
4. **Terminal access**: The web terminal can execute arbitrary commands; grant access carefully
5. **File operations**: All file operations are logged

### Recommended deployment

```
                    ┌─────────────────┐
                    │   Nginx/Caddy   │
                    │  (HTTPS + Auth) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  ClawOS (LAN)   │
                    │  http://:6002   │
                    └─────────────────┘
```

## License

MIT License - see LICENSE for details.
