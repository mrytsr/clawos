import re
import subprocess
from datetime import datetime


def list_systemd_services():
    """获取systemd服务列表（用户级）"""
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'list-units', '--type=service', '--all', '--no-pager', '--plain'],
            capture_output=True, text=True
        )
        services = []

        lines = result.stdout.strip().split('\n')
        for line in lines:
            if not line or line.startswith('UNIT ') or line.startswith('LOAD '):
                continue
            if line.startswith('●'):
                continue

            match = re.match(r'^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)$', line)
            if match:
                unit, load_state, active_state, sub_state, description = match.groups()

                if unit in ['UNIT', 'LOAD', 'ACTIVE', 'SUB']:
                    continue

                if load_state in ['not-found', 'masked']:
                    continue

                try:
                    enabled_result = subprocess.run(
                        ['systemctl', '--user', 'is-enabled', unit],
                        capture_output=True, text=True, timeout=2
                    )
                    enabled = 'enabled' in enabled_result.stdout.lower()
                except Exception:
                    enabled = False

                active_since = None
                try:
                    status_result = subprocess.run(
                        ['systemctl', '--user', 'status', unit],
                        capture_output=True, text=True, timeout=2
                    )
                    for status_line in status_result.stdout.split('\n'):
                        if 'Active:' in status_line and 'since' in status_line:
                            time_part = status_line.split('since ')[1].split(';')[0].strip()
                            try:
                                time_clean = time_part.replace(' CST', '').replace(' UTC', '')
                                dt = datetime.strptime(time_clean, '%a %Y-%m-%d %H:%M:%S')
                                active_since = dt.isoformat()
                            except Exception:
                                pass
                            break
                except Exception:
                    pass

                services.append({
                    'name': unit,
                    'load': load_state,
                    'active': active_state,
                    'sub': sub_state,
                    'status': f'{active_state} ({sub_state})',
                    'enabled': enabled,
                    'description': description,
                    'active_since': active_since
                })

        return {'success': True, 'services': services}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def control_systemd_service(service, action):
    """控制systemd服务（用户级）"""
    import time
    try:
        if action in ['start', 'stop', 'restart']:
            subprocess.run(['systemctl', '--user', action, service], capture_output=True, text=True)

            if action in ['start', 'restart']:
                for _ in range(10):
                    time.sleep(0.5)
                    result = subprocess.run(
                        ['systemctl', '--user', 'is-active', service],
                        capture_output=True, text=True, timeout=2
                    )
                    if 'active' in result.stdout.lower():
                        break

        elif action in ['enable', 'disable']:
            subprocess.run(['systemctl', '--user', action, service], capture_output=True, text=True)

        return {'success': True, 'message': f'{service} {action} 成功'}
    except Exception as e:
        return {'success': False, 'message': str(e)}
