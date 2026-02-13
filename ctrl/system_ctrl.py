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
    scope = request.args.get('scope', 'user')
    result = systemd_utils.list_systemd_services(scope)
    return _wrap(result)


@system_bp.route('/api/systemd/control', methods=['POST'])
def api_systemd_control():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    service = data.get('service')
    action = data.get('action')
    scope = data.get('scope', 'user')

    def _run():
        result = systemd_utils.control_systemd_service(service, action, scope)
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
        gpu_info = {
            'name': 'Unknown GPU',
            'driver': 'Unknown',
            'cuda': 'Unknown',
            'temperature': 0,
            'fan_percent': 0,
            'power_used': 0,
            'power_total': 0,
            'memory_used': 0,
            'memory_total': 1,
            'utilization': 0
        }
        processes = []
        lines = output.split('\n')
        
        # 提取GPU名称
        for line in lines:
            if 'GeForce' in line or 'RTX' in line:
                # 提取型号，格式如 "  0  NVIDIA GeForce RTX 2080 Ti     Off"
                match = re.search(r'(\d+)\s+(NVIDIA\s+GeForce\s+RTX[\s\d]+)', line)
                if match:
                    gpu_info['name'] = match.group(2).strip()
                else:
                    # 备选方案：取最后一段
                    parts = line.split('|')
                    for p in reversed(parts):
                        if 'GeForce' in p or 'RTX' in p:
                            gpu_info['name'] = p.replace('Off', '').strip()
                            break
                break
        
        # 提取显存、温度、功耗
        for line in lines:
            if 'MiB /' in line:
                match = re.search(r'(\d+)MiB /  (\d+)MiB', line)
                if match:
                    gpu_info['memory_used'] = int(match.group(1))
                    gpu_info['memory_total'] = int(match.group(2))
                break
        
        for line in lines:
            if 'W / ' in line:
                match = re.search(r'(\d+)W /  (\d+)W', line)
                if match:
                    gpu_info['power_used'] = int(match.group(1))
                    gpu_info['power_total'] = int(match.group(2))
                break
        
        for line in lines:
            if 'C' in line and '%' in line:
                # 找温度
                temp_match = re.search(r'(\d+)C', line)
                if temp_match:
                    gpu_info['temperature'] = int(temp_match.group(1))
                # 找利用率
                util_match = re.search(r'\|\s+(\d+)%\s+Default', line)
                if util_match:
                    gpu_info['utilization'] = int(util_match.group(1))
                # 找风扇
                fan_match = re.search(r'^\|\s*(\d+)%', line)
                if fan_match:
                    gpu_info['fan_percent'] = int(fan_match.group(1))
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
        
        # 提取进程列表
        in_processes = False
        for line in lines:
            if 'Processes:' in line:
                in_processes = True
                continue
            if in_processes:
                if line.startswith('+') or not line.strip() or 'GPU   GI' in line:
                    continue
                # 格式: |    0   N/A  N/A            1426      G   /usr/lib/xorg/Xorg                       12MiB |
                match = re.search(r'\|\s*\d+\s+N/A\s+N/A\s+(\d+)\s+(\w)\s+([^\|]+?)\s+(\d+)MiB\s*\|', line)
                if match:
                    processes.append({
                        'pid': match.group(1),
                        'type': match.group(2),
                        'name': match.group(3).strip(),
                        'memory': int(match.group(4))
                    })
                elif line.startswith('+---'):
                    break
        
        return api_ok({'gpu': gpu_info, 'processes': processes})
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


@system_bp.route('/api/system/exec', methods=['POST'])
def api_system_exec():
    """执行系统命令（仅限用户态服务管理）"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        timeout = data.get('timeout', 30)
        
        # 安全检查：只允许特定的 systemctl --user 命令
        allowed_patterns = [
            r'^systemctl --user (start|stop|restart|reload|enable|disable|status) [a-zA-Z0-9_\-\.]+(\.service)?( --no-pager)?$',
        ]
        
        import re
        if not any(re.match(p, command) for p in allowed_patterns):
            return api_error('命令不允许', status=403)
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return api_ok({
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except subprocess.TimeoutExpired:
        return api_error('命令执行超时', status=408)
    except Exception as e:
        return api_error(str(e), status=500)


# ========== 性能监控 ==========
@system_bp.route('/api/performance/realtime')
def api_performance_realtime():
    """获取实时性能数据"""
    import psutil
    
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_counts = psutil.cpu_count()
        
        # 内存
        mem = psutil.virtual_memory()
        
        # 磁盘 IO
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # 网络 IO
        net_io = psutil.net_io_counters()
        
        # GPU 信息
        gpu_info = {'available': False}
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,fan.speed', '--format=csv,noheader,nounits'],
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(',')]
                if len(parts) >= 6:
                    gpu_info = {
                        'available': True,
                        'name': parts[0],
                        'utilization': int(parts[1]) if parts[1] else 0,
                        'memory_used': int(parts[2]) if parts[2] else 0,
                        'memory_total': int(parts[3]) if parts[3] else 0,
                        'temperature': int(parts[4]) if parts[4] else 0,
                        'fan_speed': int(parts[5]) if parts[5] else 0,
                    }
        except:
            pass
        
        return api_ok({
            'cpu': {'percent': cpu_percent, 'count': cpu_counts},
            'memory': {'percent': mem.percent, 'used': mem.used, 'total': mem.total, 'available': mem.available},
            'disk': {'percent': disk.percent, 'used': disk.used, 'total': disk.total, 
                     'read_bytes': disk_io.read_bytes if disk_io else 0, 'write_bytes': disk_io.write_bytes if disk_io else 0},
            'network': {'bytes_sent': net_io.bytes_sent, 'bytes_recv': net_io.bytes_recv,
                       'packets_sent': net_io.packets_sent, 'packets_recv': net_io.packets_recv},
            'gpu': gpu_info,
            'timestamp': __import__('time').time()
        })
    except Exception as e:
        return api_error(str(e), status=500)


# ========== 网络管理 ==========
@system_bp.route('/api/network/interfaces')
def api_network_interfaces():
    """获取网络接口详情"""
    import psutil
    
    try:
        interfaces = []
        net_io = psutil.net_io_counters(pernic=True)
        
        for name, stats in net_io.items():
            addrs = psutil.net_if_addrs()
            if name in addrs:
                for addr in addrs[name]:
                    if addr.family == 2:  # AF_INET
                        interfaces.append({
                            'name': name,
                            'ip': addr.address,
                            'netmask': addr.netmask or '',
                            'bytes_sent': stats.bytes_sent,
                            'bytes_recv': stats.bytes_recv,
                            'is_up': True
                        })
                        break
        
        return api_ok({'interfaces': interfaces})
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/network/connections')
def api_network_connections():
    """获取网络连接"""
    try:
        connections = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status:
                connections.append({
                    'local_addr': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else '-',
                    'remote_addr': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else '-',
                    'status': conn.status,
                    'pid': conn.pid or '-'
                })
        return api_ok({'connections': connections[:100]})
    except Exception as e:
        return api_error(str(e), status=500)


# ========== 用户管理 ==========
@system_bp.route('/api/users/list')
def api_users_list():
    """获取用户列表"""
    try:
        import pwd
        users = []
        for entry in pwd.getpwall():
            users.append({
                'name': entry.pw_name,
                'uid': entry.pw_uid,
                'gid': entry.pw_gid,
                'home': entry.pw_dir,
                'shell': entry.pw_shell
            })
        return api_ok({'users': users})
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/users/groups')
def api_users_groups():
    """获取用户组列表"""
    try:
        import grp
        groups = []
        for entry in grp.getgrall():
            members = list(entry.gr_mem) if entry.gr_mem else []
            groups.append({'name': entry.gr_name, 'gid': entry.gr_gid, 'members': members})
        return api_ok({'groups': groups})
    except Exception as e:
        return api_error(str(e), status=500)


# ========== 统一系统状态 API ==========

@system_bp.route('/api/system/status')
def api_system_status():
    """获取统一系统状态（CPU/内存/磁盘/GPU/网络）"""
    import time
    import socket
    from lib import disk_utils, network_utils
    
    status = {
        'hostname': socket.gethostname(),
        'cpu': 0,
        'memory_percent': 0,
        'disk_percent': 0,
        'gpu_utilization': 0,
        'gpu_memory_percent': 0,
        'gpu_power': 0,
        'network_rx': 0,
        'network_tx': 0
    }
    
    # CPU 和 内存
    if psutil:
        try:
            status['cpu'] = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            status['memory_percent'] = mem.percent
        except Exception:
            pass
    
    # 磁盘
    try:
        disks = disk_utils.list_disks().get('disks', [])
        for disk in disks:
            if disk.get('mountpoint') == '/':
                status['disk_percent'] = float(disk.get('use_percent', 0))
                break
    except Exception:
        pass
    
    # GPU
    try:
        gpu_result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        output = gpu_result.stdout or gpu_result.stderr
        
        # 解析显存使用率
        mem_match = re.search(r'(\d+)\s+MiB\s+/\s+(\d+)\s+MiB', output)
        if mem_match:
            mem_used = int(mem_match.group(1))
            mem_total = int(mem_match.group(2))
            status['gpu_memory_percent'] = round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0
        
        # 解析利用率
        util_match = re.search(r'(\d+)%\s+Default', output)
        if util_match:
            status['gpu_utilization'] = int(util_match.group(1))
        
        # 解析功耗
        power_match = re.search(r'(\d+)\s+W\s+/\s+(\d+)\s+W', output)
        if power_match:
            status['gpu_power'] = int(power_match.group(1))
    except Exception:
        pass
    
    # 网络
    try:
        net1 = network_utils.get_network_speed()
        time.sleep(0.5)
        net2 = network_utils.get_network_speed()
        
        if net1.get('success') and net2.get('success'):
            rx_diff = max(0, net2['rx'] - net1['rx'])
            tx_diff = max(0, net2['tx'] - net1['tx'])
            # 转换为 KB/s
            status['network_rx'] = round(rx_diff / 1024, 1)
            status['network_tx'] = round(tx_diff / 1024, 1)
    except Exception:
        pass
    
    return api_ok(status)


# ========== 当前用户 ==========
@system_bp.route('/api/users/me')
def api_users_me():
    """获取当前用户信息"""
    try:
        import pwd
        uid = os.getuid()
        entry = pwd.getpwuid(uid)
        return api_ok({
            'name': entry.pw_name,
            'uid': entry.pw_uid,
            'gid': entry.pw_gid,
            'home': entry.pw_dir,
            'shell': entry.pw_shell
        })
    except Exception as e:
        return api_error(str(e), status=500)
