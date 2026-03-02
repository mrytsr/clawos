import json
import os
import shutil
import subprocess
import threading
import time

from flask import Blueprint

from ctrl import api_error, api_ok
from ctrl.task_ctrl import create_task, update_task


ollama_bp = Blueprint('ollama', __name__)


def _has_ollama():
    return bool(shutil.which('ollama'))


def _run_shell(task_id, cmd: str, timeout=None):
    update_task(task_id, status='running', message=cmd)
    result = subprocess.run(
        ['bash', '-lc', cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or '').strip()
        raise RuntimeError(err or ('command failed: ' + cmd))
    return result.stdout


@ollama_bp.route('/api/ollama/install_state')
def api_ollama_install_state():
    return api_ok({'installed': _has_ollama()})


@ollama_bp.route('/api/ollama/install', methods=['POST'])
def api_ollama_install():
    if os.name == 'nt':
        return api_error('Windows 环境不支持该操作', status=400)

    def _do_install(task_id):
        if _has_ollama():
            update_task(task_id, status='completed', message='Ollama 已安装', progress=100)
            return
        
        # 检查架构
        arch = os.uname().m
        if arch not in ['x86_64', 'aarch64', 'arm64']:
            raise RuntimeError(f'不支持的架构: {arch}')
        
        arch_map = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}
        ollama_arch = arch_map.get(arch, 'amd64')
        
        update_task(task_id, message='检测系统环境...', progress=5)
        
        # Ollama 版本
        ollama_version = "0.5.6"
        
        # 尝试多个下载源
        download_urls = [
            f"https://github.com/ollama/ollama/releases/download/v{ollama_version}/ollama-linux-{ollama_arch}",
            # 可以添加国内镜像
        ]
        
        update_task(task_id, message=f'下载 Ollama v{ollama_version}...', progress=10)
        
        downloaded = False
        last_error = None
        
        for download_url in download_urls:
            try:
                update_task(task_id, message=f'尝试从 GitHub 下载...')
                
                # 使用 curl 下载，设置超时
                result = subprocess.run(
                    ['curl', '-L', '--connect-timeout', '30', '--max-time', '300', '-o', '/tmp/ollama', download_url],
                    capture_output=True,
                    text=True,
                    timeout=320,
                )
                
                if result.returncode == 0 and os.path.exists('/tmp/ollama') and os.path.getsize('/tmp/ollama') > 1000000:
                    downloaded = True
                    break
                else:
                    last_error = result.stderr or '下载失败'
                    
            except subprocess.TimeoutExpired:
                last_error = '下载超时'
            except Exception as e:
                last_error = str(e)
        
        if not downloaded:
            # 尝试使用安装脚本（可能有更好的网络处理）
            update_task(task_id, message='尝试使用安装脚本...', progress=15)
            try:
                # 先下载安装脚本看看
                script_result = subprocess.run(
                    ['curl', '-fsSL', '--connect-timeout', '30', '-o', '/tmp/ollama-install.sh', 'https://ollama.com/install.sh'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                
                if script_result.returncode == 0:
                    # 检查脚本内容
                    with open('/tmp/ollama-install.sh', 'r') as f:
                        script_content = f.read()
                    
                    # 尝试直接运行安装脚本
                    update_task(task_id, message='运行安装脚本（可能需要较长时间）...', progress=30)
                    
                    # 使用 bash -c 并设置环境变量可能有助于绕过某些网络问题
                    env = os.environ.copy()
                    env['OLLAMA_VERSION'] = ollama_version
                    
                    result = subprocess.run(
                        ['bash', '/tmp/ollama-install.sh'],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        env=env,
                    )
                    
                    if result.returncode == 0 and _has_ollama():
                        downloaded = True
                    else:
                        last_error = result.stderr or '安装脚本失败'
                        
            except Exception as e:
                last_error = str(e)
        
        if not downloaded:
            raise RuntimeError(f'下载失败: {last_error}\n\n请尝试手动下载：\n1. 访问 https://github.com/ollama/ollama/releases\n2. 下载 ollama-linux-{ollama_arch}\n3. 上传到服务器并运行: sudo mv ollama /usr/local/bin/ && sudo chmod +x /usr/local/bin/ollama')
        
        update_task(task_id, message='安装 Ollama 二进制文件...', progress=60)
        
        # 安装二进制
        os.chmod('/tmp/ollama', 0o755)
        shutil.move('/tmp/ollama', '/usr/local/bin/ollama')
        
        # 验证安装
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError('安装验证失败')
        
        update_task(task_id, message='配置 systemd 服务...', progress=80)
        
        # 配置 systemd --user 服务
        systemd_dir = os.path.expanduser('~/.config/systemd/user')
        os.makedirs(systemd_dir, exist_ok=True)
        
        service_content = """[Unit]
Description=Ollama Service
After=default.target

[Service]
Type=simple
ExecStart=/usr/local/bin/ollama serve
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
        
        service_path = os.path.join(systemd_dir, 'ollama.service')
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        update_task(task_id, message='启动 Ollama 服务...', progress=90)
        
        # 启用并启动服务
        try:
            subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True, timeout=10)
            subprocess.run(['systemctl', '--user', 'enable', 'ollama'], capture_output=True, timeout=10)
            subprocess.run(['systemctl', '--user', 'start', 'ollama'], capture_output=True, timeout=10)
        except Exception as e:
            # 如果 systemctl 失败，尝试直接启动
            try:
                subprocess.Popen(['nohup', 'ollama', 'serve', '>', '/tmp/ollama.log', '2>&1', '&'])
            except:
                pass
        
        update_task(task_id, status='completed', message='安装完成！Ollama 服务已启动', progress=100)

    task_id = create_task(_do_install, name='ollama install')
    return api_ok({'taskId': task_id})


@ollama_bp.route('/api/ollama/reinstall', methods=['POST'])
def api_ollama_reinstall():
    if os.name == 'nt':
        return api_error('Windows 环境不支持该操作', status=400)

    def _do(task_id):
        _do_uninstall(task_id)
        _do_install(task_id)

    task_id = create_task(_do, name='ollama reinstall')
    return api_ok({'taskId': task_id})


@ollama_bp.route('/api/ollama/uninstall', methods=['POST'])
def api_ollama_uninstall():
    if os.name == 'nt':
        return api_error('Windows 环境不支持该操作', status=400)

    def _do(task_id):
        _do_uninstall(task_id)

    task_id = create_task(_do, name='ollama uninstall')
    return api_ok({'taskId': task_id})


def _do_uninstall(task_id):
    path = shutil.which('ollama')
    cmds = [
        'systemctl stop ollama 2>/dev/null || true',
        'systemctl disable ollama 2>/dev/null || true',
        'systemctl --user stop ollama 2>/dev/null || true',
        'systemctl --user disable ollama 2>/dev/null || true',
    ]
    for cmd in cmds:
        try:
            _run_shell(task_id, cmd, timeout=30)
        except Exception:
            pass

    if path and os.path.isabs(path):
        try:
            os.remove(path)
        except Exception:
            pass

    for p in [
        '/etc/systemd/system/ollama.service',
        '/usr/lib/systemd/system/ollama.service',
        '/usr/local/lib/systemd/system/ollama.service',
        os.path.expanduser('~/.config/systemd/user/ollama.service'),
        '/usr/local/bin/ollama',
        '/usr/bin/ollama',
    ]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    for d in [
        os.path.expanduser('~/.ollama'),
        '/usr/share/ollama',
        '/var/lib/ollama',
    ]:
        try:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass

    try:
        _run_shell(task_id, 'systemctl daemon-reload 2>/dev/null || true', timeout=15)
        _run_shell(task_id, 'systemctl --user daemon-reload 2>/dev/null || true', timeout=15)
    except Exception:
        pass


@ollama_bp.route('/api/ollama/models')
def api_ollama_models():
    try:
        models = []

        try:
            import requests

            r = requests.get('http://localhost:11434/api/tags', timeout=3)
            if r.status_code == 200:
                data = r.json() or {}
                for m in data.get('models', []) or []:
                    models.append({
                        'name': m.get('name', ''),
                        'size': m.get('size', 0),
                        'modified': m.get('modified', ''),
                    })
                return api_ok({'models': models})
        except Exception:
            pass

        if _has_ollama():
            try:
                result = subprocess.run(
                    ['ollama', 'list'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    for line in (result.stdout or '').strip().split('\n'):
                        if not line:
                            continue
                        parts = line.split()
                        if not parts:
                            continue
                        model_name = parts[0]
                        size = parts[1] if len(parts) > 1 else '?'
                        models.append({'name': model_name, 'size': size})
            except Exception:
                pass

        return api_ok({'models': models})
    except Exception as e:
        return api_error(str(e), status=500)
