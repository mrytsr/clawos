import subprocess
import time

try:
    import psutil
except Exception:
    psutil = None


def get_process_ports():
    """获取所有进程的端口映射"""
    port_map = {}
    try:
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if line and not line.startswith('Active') and not line.startswith('Proto'):
                parts = line.split()
                if len(parts) >= 7:
                    local_addr = parts[3]
                    prog_info = parts[6] if len(parts) > 6 else ''
                    if '/' in prog_info:
                        try:
                            prog_pid = int(prog_info.split('/')[0])
                            if ':' in local_addr:
                                port = local_addr.split(':')[1]
                                if prog_pid not in port_map:
                                    port_map[prog_pid] = []
                                port_map[prog_pid].append(port)
                        except (ValueError, IndexError):
                            pass
    except Exception:
        pass
    return port_map


def get_process_uptime(create_time):
    """计算进程运行时间"""
    if create_time:
        now = time.time()
        uptime_seconds = now - create_time
        if uptime_seconds < 60:
            return f"{int(uptime_seconds)}秒"
        elif uptime_seconds < 3600:
            return f"{int(uptime_seconds/60)}分钟"
        elif uptime_seconds < 86400:
            return f"{int(uptime_seconds/3600)}小时"
        else:
            return f"{int(uptime_seconds/86400)}天"
    return '-'


def list_processes():
    """获取进程列表"""
    if psutil is None:
        return {'success': False, 'message': 'psutil 未安装'}

    port_map = get_process_ports()
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'create_time', 'status']):
        try:
            info = proc.info
            cmdline = info.get('cmdline')
            cmd = ' '.join(cmdline) if cmdline else info.get('name', '')

            uptime = get_process_uptime(info.get('create_time'))
            pid = info['pid']
            ports = port_map.get(pid, [])

            processes.append({
                'pid': pid,
                'name': info.get('name', '?'),
                'cmd': cmd[:100] if len(cmd) > 100 else cmd,
                'cpu': round(info.get('cpu_percent', 0), 1),
                'memory': round(info.get('memory_percent', 0), 2),
                'uptime': uptime,
                'status': info.get('status', 'unknown'),
                'ports': ports,
                'has_ports': len(ports) > 0
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    processes.sort(key=lambda x: (not x['has_ports'], x['pid']))
    return {'success': True, 'processes': processes}


def kill_process(pid):
    """结束进程"""
    if psutil is None:
        return {'success': False, 'message': 'psutil 未安装'}

    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
        return {'success': True, 'message': f'进程 {pid} 已终止'}
    except psutil.NoSuchProcess:
        return {'success': False, 'message': f'进程 {pid} 不存在'}
    except psutil.AccessDenied:
        return {'success': False, 'message': f'权限不足，无法终止进程 {pid}'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def get_process_ports_detail(pid):
    """获取进程占用的端口详情"""
    ports = []
    try:
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if line and not line.startswith('Active') and not line.startswith('Proto'):
                parts = line.split()
                if len(parts) >= 7:
                    local_addr = parts[3]
                    prog_info = parts[6] if len(parts) > 6 else ''
                    if '/' in prog_info:
                        try:
                            prog_pid = int(prog_info.split('/')[0])
                            if prog_pid == pid and ':' in local_addr:
                                port = local_addr.split(':')[1]
                                proto = parts[0].lower()
                                state = parts[5] if len(parts) > 5 else ''
                                prog_name = prog_info.split('/')[1] if len(prog_info.split('/')) > 1 else ''
                                ports.append({
                                    'protocol': proto.upper(),
                                    'port': port,
                                    'state': state,
                                    'program': prog_name
                                })
                        except (ValueError, IndexError):
                            pass
        return {'success': True, 'pid': pid, 'ports': ports}
    except Exception as e:
        return {'success': False, 'message': str(e)}
