import subprocess


def get_network_speed():
    """获取网络上下行速度（字节/秒）"""
    try:
        result = subprocess.run(['cat', '/proc/net/dev'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        
        # 跳过前两行（头部）
        # 格式: Inter-|   Receive                                                |  Transmit
        #      face: bytes    packets errs drop fifo frame compressed multicast | bytes    packets errs drop fifo colls carrier compressed
        rx_bytes, tx_bytes = 0, 0
        
        for line in lines[2:]:  # 跳过前两行
            if ':' in line:
                parts = line.split(':')[1].split()
                if len(parts) >= 8:
                    rx = int(parts[0])  # receive bytes
                    tx = int(parts[8])  # transmit bytes
                    rx_bytes += rx
                    tx_bytes += tx
        
        # 返回字节数和对应的时间戳（秒）
        return {'success': True, 'rx': rx_bytes, 'tx': tx_bytes}
    except Exception as e:
        return {'success': False, 'message': str(e), 'rx': 0, 'tx': 0}


def list_network():
    """获取网络接口信息"""
    try:
        result = subprocess.run(['ifconfig'], capture_output=True, text=True)
        interfaces = []
        current_iface = None

        for line in result.stdout.strip().split('\n'):
            if line and not line.startswith('\t') and not line.startswith(' '):
                if ':' in line:
                    parts = line.split(':')
                    name = parts[0].strip()
                    flags = parts[1] if len(parts) > 1 else ''
                    current_iface = {
                        'name': name,
                        'state': 'UP' if 'UP' in flags else 'DOWN',
                        'ipv4': '',
                        'ipv6': '',
                        'mac': '',
                        'mtu': '',
                        'broadcast': ''
                    }
                    if 'mtu' in flags:
                        mtu_parts = flags.split('mtu')
                        if len(mtu_parts) > 1:
                            mtu = mtu_parts[1].split()[0].strip()
                            current_iface['mtu'] = mtu
                    interfaces.append(current_iface)
            elif current_iface and line.strip():
                parts = line.strip().split()
                if 'inet ' in line:
                    current_iface['ipv4'] = parts[1] if len(parts) > 1 else ''
                elif 'inet6' in line:
                    current_iface['ipv6'] = parts[1] if len(parts) > 1 else ''
                elif 'ether' in line or 'hwaddr' in line:
                    current_iface['mac'] = parts[1] if len(parts) > 1 else ''
                elif 'broadcast' in line:
                    current_iface['broadcast'] = parts[1] if len(parts) > 1 else ''

        return {'success': True, 'interfaces': interfaces}
    except Exception as e:
        return {'success': False, 'message': str(e)}
