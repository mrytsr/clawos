import socket

try:
    import psutil
except Exception:
    psutil = None


def get_network_speed():
    """获取网络上下行速度（字节/秒）"""
    if psutil is None:
        return {'success': False, 'message': 'psutil 未安装', 'rx': 0, 'tx': 0}
    try:
        net = psutil.net_io_counters()
        rx_bytes = int(getattr(net, 'bytes_recv', 0) or 0)
        tx_bytes = int(getattr(net, 'bytes_sent', 0) or 0)
        return {'success': True, 'rx': rx_bytes, 'tx': tx_bytes}
    except Exception as e:
        return {'success': False, 'message': str(e), 'rx': 0, 'tx': 0}


def list_network():
    """获取网络接口信息"""
    if psutil is None:
        return {'success': False, 'message': 'psutil 未安装'}
    try:
        interfaces = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_map = psutil.net_io_counters(pernic=True)
        link_family = getattr(psutil, 'AF_LINK', None)

        for name, addr_list in addrs.items():
            info = {
                'name': name,
                'state': 'UP' if getattr(stats.get(name), 'isup', False) else 'DOWN',
                'ipv4': '',
                'ipv6': '',
                'mac': '',
                'mtu': str(getattr(stats.get(name), 'mtu', '') or ''),
                'broadcast': '',
                'bytes_sent': int(getattr(io_map.get(name), 'bytes_sent', 0) or 0),
                'bytes_recv': int(getattr(io_map.get(name), 'bytes_recv', 0) or 0),
            }
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    info['ipv4'] = addr.address or ''
                    info['broadcast'] = addr.broadcast or info['broadcast']
                elif addr.family == socket.AF_INET6:
                    info['ipv6'] = (addr.address or '').split('%')[0]
                elif link_family is not None and addr.family == link_family:
                    info['mac'] = addr.address or ''
            interfaces.append(info)
        return {'success': True, 'interfaces': interfaces}
    except Exception as e:
        return {'success': False, 'message': str(e)}
