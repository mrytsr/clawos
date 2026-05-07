import socket
import subprocess
import time

try:
    import psutil
except Exception:
    psutil = None


def get_process_ports():
    """获取所有进程的端口映射"""
    port_map = {}
    if psutil is not None:
        try:
            for conn in psutil.net_connections(kind='inet'):
                pid = getattr(conn, 'pid', None)
                if not pid:
                    continue
                local_addr = getattr(conn, 'laddr', None)
                port = getattr(local_addr, 'port', None) if local_addr else None
                if port is None and isinstance(local_addr, tuple) and len(local_addr) >= 2:
                    port = local_addr[1]
                if port is None:
                    continue
                status = (getattr(conn, 'status', '') or '').upper()
                protocol = 'UDP' if getattr(conn, 'type', None) == socket.SOCK_DGRAM else 'TCP'
                if protocol == 'TCP' and status and status != 'LISTEN':
                    continue
                port_map.setdefault(pid, []).append(str(port))
        except Exception:
            port_map = {}
        else:
            for pid, ports in list(port_map.items()):
                port_map[pid] = sorted(
                    set(ports),
                    key=lambda value: int(value) if str(value).isdigit() else str(value),
                )
            return port_map
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


def list_processes(limit=50):
    """获取进程列表"""
    if psutil is None:
        return {'success': False, 'message': 'psutil 未安装'}

    port_map = get_process_ports()
    processes = []

    for proc in psutil.process_iter([
        'pid',
        'name',
        'username',
        'cmdline',
        'cpu_percent',
        'memory_percent',
        'memory_info',
        'create_time',
        'status',
    ]):
        try:
            info = proc.info
            cmdline = info.get('cmdline')
            full_cmd = ' '.join(str(part) for part in (cmdline or []) if part) if cmdline else (info.get('name') or '')
            cmd = full_cmd[:100] + '...' if len(full_cmd) > 103 else full_cmd
            memory_info = info.get('memory_info')

            uptime = get_process_uptime(info.get('create_time'))
            pid = info['pid']
            ports = port_map.get(pid, [])

            processes.append({
                'pid': pid,
                'name': info.get('name', '?'),
                'user': info.get('username') or '-',
                'command': cmd or info.get('name', '?'),
                'full_command': full_cmd or info.get('name', '?'),
                'cmd': cmd or info.get('name', '?'),
                'cpu': round(info.get('cpu_percent', 0), 1),
                'cpu_percent': round(info.get('cpu_percent', 0), 1),
                'memory': round(info.get('memory_percent', 0), 2),
                'memory_percent': round(info.get('memory_percent', 0), 2),
                'memory_rss': int(getattr(memory_info, 'rss', 0) or 0),
                'uptime': uptime,
                'elapsed': uptime,
                'status': info.get('status', 'unknown'),
                'ports': ports,
                'has_ports': len(ports) > 0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    processes.sort(key=lambda x: (not x['has_ports'], -x['cpu_percent'], -x['memory_percent'], x['pid']))

    vm = psutil.virtual_memory()
    stats = {
        'cpu_percent': round(psutil.cpu_percent(interval=0.0), 1),
        'memory_used': int(vm.used),
        'memory_total': int(vm.total),
        'memory_percent': round(float(vm.percent), 1),
        'process_count': len(processes),
    }
    if isinstance(limit, int) and limit > 0:
        processes = processes[:limit]
    return {'success': True, 'stats': stats, 'processes': processes}


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
    if psutil is not None:
        try:
            proc = psutil.Process(pid)
            program = proc.name() or ''
            try:
                conns = proc.net_connections(kind='inet')
            except AttributeError:
                conns = proc.connections(kind='inet')
            for conn in conns:
                local_addr = getattr(conn, 'laddr', None)
                port = getattr(local_addr, 'port', None) if local_addr else None
                if port is None and isinstance(local_addr, tuple) and len(local_addr) >= 2:
                    port = local_addr[1]
                if port is None:
                    continue
                protocol = 'UDP' if getattr(conn, 'type', None) == socket.SOCK_DGRAM else 'TCP'
                status = (getattr(conn, 'status', '') or '').upper()
                ports.append({
                    'protocol': protocol,
                    'port': str(port),
                    'state': status or ('LISTEN' if protocol == 'UDP' else ''),
                    'program': program,
                })
            ports.sort(key=lambda item: (item['protocol'], int(item['port']) if item['port'].isdigit() else item['port']))
            return {'success': True, 'pid': pid, 'ports': ports}
        except psutil.NoSuchProcess:
            return {'success': False, 'message': f'进程 {pid} 不存在'}
        except psutil.AccessDenied:
            return {'success': False, 'message': f'权限不足，无法读取进程 {pid} 的端口信息'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
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
