import subprocess


def list_disks():
    """获取磁盘分区和挂载信息"""
    df_result = subprocess.run(['df', '-h'], capture_output=True, text=True)
    disks = []

    for line in df_result.stdout.strip().split('\n'):
        if line and not line.startswith('Filesystem'):
            parts = line.split()
            if len(parts) >= 6:
                disks.append({
                    'device': parts[0],
                    'total': parts[1],
                    'used': parts[2],
                    'available': parts[3],
                    'use_percent': parts[4].replace('%', ''),
                    'mountpoint': parts[5]
                })

    mount_result = subprocess.run(['mount'], capture_output=True, text=True)
    mount_info = {}
    for line in mount_result.stdout.strip().split('\n'):
        if line:
            parts = line.split()
            if len(parts) >= 4:
                device = parts[0]
                fstype = parts[4] if len(parts) > 4 else ''
                options = parts[5] if len(parts) > 5 else ''
                mount_info[device] = {'fstype': fstype, 'options': options}

    for disk in disks:
        mount_data = mount_info.get(disk['device'], {})
        disk['fstype'] = mount_data.get('fstype', '')
        disk['options'] = mount_data.get('options', '')

    return {'success': True, 'disks': disks}
