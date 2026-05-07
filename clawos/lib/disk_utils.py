try:
    import psutil
except Exception:
    psutil = None


def list_disks():
    """获取磁盘分区和挂载信息"""
    if psutil is None:
        return {'success': False, 'message': 'psutil 未安装'}

    disks = []
    seen = set()
    try:
        for part in psutil.disk_partitions(all=True):
            key = (part.device, part.mountpoint)
            if key in seen:
                continue
            seen.add(key)
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except Exception:
                continue
            disks.append({
                'device': part.device or part.mountpoint,
                'total': str(usage.total),
                'used': str(usage.used),
                'available': str(usage.free),
                'use_percent': str(int(round(usage.percent))),
                'mountpoint': part.mountpoint,
                'fstype': part.fstype or '',
                'options': part.opts or '',
            })
        return {'success': True, 'disks': disks}
    except Exception as e:
        return {'success': False, 'message': str(e)}
