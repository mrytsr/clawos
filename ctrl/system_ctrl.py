import json
import os
import re
import subprocess
from flask import Blueprint, request, jsonify

import config

try:
    import psutil
except ImportError:
    psutil = None

from ctrl import api_error, api_ok

from ctrl.task_ctrl import create_task
from lib import (
    disk_utils,
    docker_utils,
    network_utils,
    packages_utils,
    process_utils,
    systemd_utils,
)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')


system_bp = Blueprint('system', __name__)


def _wrap(result, fail_status=400):
    if isinstance(result, dict) and result.get('success'):
        data = dict(result)
        data.pop('success', None)
        return api_ok(data)
    message = None
    if isinstance(result, dict):
        message = result.get('message')
    return api_error(message or 'Error', status=fail_status)


@system_bp.route('/api/process/list')
def api_process_list():
    """获取进程列表（适合手机展示）"""
    try:
        # 使用 ps 命令获取进程信息
        result = subprocess.run(
            ['ps', 'aux', '--sort=-%cpu'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        lines = result.stdout.strip().split('\n')[1:]  # 跳过表头
        processes = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 11:
                try:
                    # ps aux 输出格式: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                    proc = {
                        'pid': int(parts[1]),
                        'user': parts[0],
                        'cpu_percent': float(parts[2]),
                        'memory_percent': float(parts[3]),
                        'memory_rss': int(parts[5]) * 1024,  # KB -> Bytes
                        'elapsed': parts[9],
                        'command': parts[10] if len(parts) > 10 else parts[10],
                        'full_command': ' '.join(parts[10:]) if len(parts) > 10 else parts[10],
                    }
                    processes.append(proc)
                except (ValueError, IndexError):
                    continue
        
        # 计算内存总量和进程数
        memory_total = 0
        try:
            if psutil is None:
                raise ImportError()
            vm = psutil.virtual_memory()
            memory_total = vm.total
        except ImportError:
            # 估算：所有进程 RSS 之和 * 2
            total_rss = sum(p['memory_rss'] for p in processes)
            memory_total = total_rss * 2
        
        memory_used = sum(p['memory_rss'] for p in processes)
        memory_percent = round(memory_used / memory_total * 100, 1) if memory_total > 0 else 0
        
        # 获取 CPU 使用率
        cpu_percent = 0
        try:
            if psutil is None:
                raise ImportError()
            cpu_percent = psutil.cpu_percent()
        except ImportError:
            cpu_percent = sum(p['cpu_percent'] for p in processes[:20])
        
        stats = {
            'cpu_percent': cpu_percent,
            'memory_used': memory_used,
            'memory_total': memory_total,
            'memory_percent': memory_percent,
            'process_count': len(processes),
        }
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'processes': processes[:50]  # 限制50个
            }
        })
    except subprocess.TimeoutExpired:
        return api_error('获取进程信息超时', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/process/kill/<int:pid>', methods=['POST'])
def api_process_kill(pid):
    result = process_utils.kill_process(pid)
    return _wrap(result)


@system_bp.route('/api/process/ports/<int:pid>')
def api_process_ports(pid):
    result = process_utils.get_process_ports_detail(pid)
    return _wrap(result)


@system_bp.route('/api/system-packages/list')
def api_system_packages():
    result = packages_utils.list_system_packages()
    return _wrap(result)


@system_bp.route('/api/system-packages/uninstall', methods=['POST'])
def api_system_packages_uninstall():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.uninstall_system_package(
        data.get('name'),
        data.get('manager'),
    )
    return _wrap(result)


@system_bp.route('/api/pip/list')
def api_pip_list():
    result = packages_utils.list_pip_packages()
    return _wrap(result)


@system_bp.route('/api/pip/install', methods=['POST'])
def api_pip_install():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.install_pip_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/pip/uninstall', methods=['POST'])
def api_pip_uninstall():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.uninstall_pip_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/npm/list')
def api_npm_list():
    result = packages_utils.list_npm_packages()
    return _wrap(result)


@system_bp.route('/api/npm/install', methods=['POST'])
def api_npm_install():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.install_npm_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/npm/uninstall', methods=['POST'])
def api_npm_uninstall():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.uninstall_npm_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/docker/images')
def api_docker_images():
    result = docker_utils.list_docker_images()
    return _wrap(result)


@system_bp.route('/api/docker/containers')
def api_docker_containers():
    result = docker_utils.list_docker_containers()
    return _wrap(result)


@system_bp.route('/api/docker/image/rm', methods=['POST'])
def api_docker_image_rm():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.remove_docker_image(data.get('id'))
    return _wrap(result)


@system_bp.route('/api/docker/container/rm', methods=['POST'])
def api_docker_container_rm():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.remove_docker_container(
        data.get('id'),
        data.get('force', False),
    )
    return _wrap(result)


@system_bp.route('/api/docker/container/stop', methods=['POST'])
def api_docker_container_stop():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.stop_docker_container(data.get('id'))
    return _wrap(result)


@system_bp.route('/api/docker/container/start', methods=['POST'])
def api_docker_container_start():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.start_docker_container(data.get('id'))
    return _wrap(result)


@system_bp.route('/api/systemd/list')
def api_systemd_list():
    result = systemd_utils.list_systemd_services()
    return _wrap(result)


@system_bp.route('/api/systemd/control', methods=['POST'])
def api_systemd_control():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    service = data.get('service')
    action = data.get('action')

    def _run():
        result = systemd_utils.control_systemd_service(service, action)
        if isinstance(result, dict) and result.get('success'):
            return
        message = None
        if isinstance(result, dict):
            message = result.get('message')
        raise RuntimeError(message or 'Error')

    task_id = create_task(_run, name=f'systemd:{action}:{service}')
    return api_ok({'taskId': task_id})


@system_bp.route('/api/disk/list')
def api_disk_list():
    result = disk_utils.list_disks()
    return _wrap(result)


@system_bp.route('/api/network/list')
def api_network_list():
    result = network_utils.list_network()
    return _wrap(result)


@system_bp.route('/api/gpu/info')
def api_gpu_info():
    """获取NVIDIA GPU信息"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        output = result.stdout or result.stderr
        # 解析关键信息
        gpu_info = {}
        lines = output.split('\n')
        
        # 提取GPU名称
        for line in lines:
            if 'GeForce' in line or 'RTX' in line or 'NVIDIA' in line:
                gpu_info['name'] = line.strip()
                break
        
        # 提取显存、温度、功耗
        for line in lines:
            if 'MiB /' in line:
                # 提取显存使用情况
                match = re.search(r'(\d+)MiB / (\d+)MiB', line)
                if match:
                    used = int(match.group(1))
                    total = int(match.group(2))
                    gpu_info['memory_used'] = used
                    gpu_info['memory_total'] = total
                    gpu_info['memory_percent'] = round(used / total * 100, 1)
                break
        
        for line in lines:
            if 'W / ' in line:
                match = re.search(r'(\d+)W / (\d+)W', line)
                if match:
                    gpu_info['power_used'] = int(match.group(1))
                    gpu_info['power_total'] = int(match.group(2))
                break
        
        for line in lines:
            temp = line.strip()
            if temp and 'C' in temp:
                match = re.search(r'(\d+)C', temp)
                if match:
                    gpu_info['temperature'] = int(match.group(1))
                break
        
        for line in lines:
            if '%' in line and 'Default' in line:
                match = re.search(r'(\d+)%', line)
                if match:
                    gpu_info['utilization'] = int(match.group(1))
                break
        
        # 驱动版本
        for line in lines:
            if 'Driver Version' in line:
                match = re.search(r'Driver Version: ([\d.]+)', line)
                if match:
                    gpu_info['driver'] = match.group(1)
                break
        
        # CUDA版本
        for line in lines:
            if 'CUDA Version' in line:
                match = re.search(r'CUDA Version: ([\d.]+)', line)
                if match:
                    gpu_info['cuda'] = match.group(1)
                break
        
        return api_ok({'raw': output, 'parsed': gpu_info})
    except subprocess.TimeoutExpired:
        return api_error('nvidia-smi超时', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/ollama/models')
def api_ollama_models():
    """获取Ollama模型列表"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            # 尝试ollama list命令
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                models = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            size = parts[1] if len(parts) > 1 else '?'
                            models.append({
                                'name': model_name,
                                'size': size
                            })
                return api_ok({'models': models})
            return api_error('无法获取模型列表')
        
        data = json.loads(result.stdout)
        models = []
        for m in data.get('models', []):
            models.append({
                'name': m.get('name', ''),
                'size': m.get('size', 0),
                'modified': m.get('modified', '')
            })
        return api_ok({'models': models})
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/openclaw/config')
def api_openclaw_config():
    """获取OpenClaw配置"""
    try:
        if not os.path.exists(OPENCLAW_CONFIG_PATH):
            return api_error('配置文件不存在')
        
        with open(OPENCLAW_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # 提取关键配置信息
        simplified = {
            'version': config.get('meta', {}).get('lastTouchedVersion', 'Unknown'),
            'models': {
                'count': 0,
                'list': []
            },
            'channels': {},
            'gateway': {},
            'auth': {}
        }
        
        # 模型列表
        providers = config.get('models', {}).get('providers', {})
        for provider_name, provider_data in providers.items():
            models = provider_data.get('models', [])
            for m in models:
                simplified['models']['list'].append({
                    'id': m.get('id', ''),
                    'name': m.get('name', m.get('id', '')),
                    'reasoning': m.get('reasoning', False)
                })
        simplified['models']['count'] = len(simplified['models']['list'])
        
        # 渠道
        channels = config.get('channels', {})
        for ch_name, ch_data in channels.items():
            simplified['channels'][ch_name] = {
                'enabled': ch_data.get('enabled', False)
            }
        
        # 网关
        gateway = config.get('gateway', {})
        simplified['gateway'] = {
            'port': gateway.get('port', 18789),
            'bind': gateway.get('bind', 'lan'),
            'tailscale': gateway.get('tailscale', {}).get('mode', 'off')
        }
        
        # 认证
        auth = config.get('auth', {}).get('profiles', {})
        simplified['auth'] = {
            'profiles': list(auth.keys())
        }
        
        return api_ok(simplified)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)
    except Exception as e:
        return api_error(str(e), status=500)
