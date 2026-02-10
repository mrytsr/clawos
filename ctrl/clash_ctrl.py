import os
import re
import subprocess
import base64
import requests
from datetime import datetime

from flask import Blueprint, request, jsonify

from ctrl import api_error, api_ok
from lib import systemd_utils


clash_bp = Blueprint('clash', __name__)


# 默认配置路径
DEFAULT_CONFIGS = [
    '/usr/local/clash/config/config.yaml',
    os.path.expanduser('~/.config/clash/config.yaml'),
    os.path.expanduser('~/.config/mihomo/config.yaml'),
    '/etc/clash/config.yaml',
    '/etc/mihomo/config.yaml',
]
DEFAULT_SERVICE = 'clash.service'


def _systemctl_user_show(unit: str):
    """获取 systemd 服务状态"""
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'show', unit, '--no-pager', 
             '--property=Id,Description,LoadState,ActiveState,SubState,UnitFileState,FragmentPath'],
            capture_output=True, text=True, timeout=3,
        )
    except Exception as e:
        return {'available': False, 'error': str(e)}

    if result.returncode != 0:
        return {'available': False, 'error': (result.stderr or result.stdout or '').strip()}

    props = {}
    for line in (result.stdout or '').splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            props[k.strip()] = v.strip()

    running = props.get('ActiveState') == 'active' and props.get('SubState') == 'running'
    return {
        'available': True,
        'id': props.get('Id') or unit,
        'description': props.get('Description') or '',
        'load_state': props.get('LoadState') or '',
        'active_state': props.get('ActiveState') or '',
        'sub_state': props.get('SubState') or '',
        'unit_file_state': props.get('UnitFileState') or '',
        'fragment_path': props.get('FragmentPath') or '',
        'running': running,
    }


def _find_config():
    """查找 Clash 配置文件"""
    for p in DEFAULT_CONFIGS:
        if p and os.path.exists(p):
            return p
    return None


def _parse_clash_yaml(content: str):
    """解析 Clash YAML 配置"""
    text = content or ''
    out = {
        'proxies': [],
        'proxy_groups': [],
        'rules_count': 0,
        'ports': {},
    }
    
    lines = text.split('\n')
    in_proxies = False
    in_proxy_providers = False
    in_proxy_groups = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        if line_stripped.startswith('proxies:'):
            in_proxies = True
            in_proxy_providers = False
            in_proxy_groups = False
            continue
        if 'proxy-providers:' in line_stripped or 'Providers' in line_stripped:
            in_proxies = False
            in_proxy_providers = True
            in_proxy_groups = False
            continue
        if 'proxy-groups:' in line_stripped or 'Groups' in line_stripped:
            in_proxies = False
            in_proxy_providers = False
            in_proxy_groups = True
            continue
        if line_stripped.startswith('rules:') or line_stripped.startswith('Rules:'):
            in_proxies = False
            in_proxy_providers = False
            in_proxy_groups = False
            # 统计规则数量
            remaining = [l.strip() for l in lines[i+1:] if l.strip() and not l.strip().startswith('#')]
            out['rules_count'] = len(remaining)
            continue
        
        # 提取节点
        if in_proxies and line_stripped.startswith('- '):
            # 提取节点名称
            name_match = re.search(r'name\s*:\s*["\']?([^"\'\n,]+)["\']?', line_stripped)
            if name_match:
                name = name_match.group(1).strip()
                # 提取类型
                type_match = re.search(r'type\s*:\s*["\']?([^"\'\n,]+)["\']?', line_stripped)
                node_type = type_match.group(1).strip() if type_match else 'unknown'
                out['proxies'].append({'name': name, 'type': node_type})
        
        # 提取代理组
        if in_proxy_groups and line_stripped.startswith('- name:'):
            name = line_stripped.replace('- name:', '').strip().strip('"').strip("'")
            if name:
                out['proxy_groups'].append(name)
    
    # 提取端口信息
    port_match = re.search(r'(?:listen|port)\s*:\s*(\d+)', text)
    socks_match = re.search(r'socks-port\s*:\s*(\d+)', text)
    mixed_match = re.search(r'mixed-port\s*:\s*(\d+)', text)
    
    out['ports'] = {
        'http': port_match.group(1) if port_match else None,
        'socks': socks_match.group(1) if socks_match else None,
        'mixed': mixed_match.group(1) if mixed_match else None,
    }
    
    return out


@clash_bp.route('/api/clash/state')
def api_clash_state():
    """获取 Clash 状态和配置"""
    config_path = _find_config()
    config = {'present': False, 'path': config_path or '', 'proxies': [], 'proxy_groups': [], 'rules_count': 0, 'ports': {}}
    
    try:
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            parsed = _parse_clash_yaml(content)
            config = {
                'present': True,
                'path': config_path,
                'proxies': parsed['proxies'][:100],  # 限制数量
                'proxy_groups': parsed['proxy_groups'],
                'rules_count': parsed['rules_count'],
                'ports': parsed['ports'],
                'size': len(content),
            }
    except Exception as e:
        config = {'present': False, 'path': config_path or '', 'error': str(e)}

    service = _systemctl_user_show(DEFAULT_SERVICE)
    if not service['available']:
        service = _systemctl_user_show('clash-meta.service') or _systemctl_user_show('mihomo.service')
    
    return api_ok({'config': config, 'service': service})


@clash_bp.route('/api/clash/control', methods=['POST'])
def api_clash_control():
    """控制 Clash 服务"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    
    action = (data.get('action') or '').strip().lower()
    if action not in {'start', 'stop', 'restart'}:
        return api_error('Invalid action', status=400)
    
    # 尝试多个服务名
    service = DEFAULT_SERVICE
    for svc in ['clash.service', 'clash-meta.service', 'mihomo.service']:
        st = _systemctl_user_show(svc)
        if st.get('available'):
            service = svc
            break
    
    result = systemd_utils.control_systemd_service(service, action)
    if isinstance(result, dict) and result.get('success'):
        return api_ok({'ok': True})
    
    return api_error(result.get('message') or 'Error', status=500)


@clash_bp.route('/api/clash/subscribe', methods=['POST'])
def api_clash_subscribe():
    """更新 Clash 订阅"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    
    url = (data.get('url') or '').strip()
    if not url:
        return api_error('Missing URL', status=400)
    
    config_path = _find_config()
    if not config_path:
        return api_error('Config file not found', status=404)
    
    try:
        # 下载订阅
        headers = {
            'User-Agent': 'ClashforWindows/0.20.0',
            'Accept': 'text/yaml,text/plain,*/*',
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        content = response.text.strip()
        
        # 尝试 Base64 解码
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            if decoded.strip().startswith('proxies:') or decoded.strip().startswith('- '):
                content = decoded
        except:
            pass
        
        # 读取现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            existing = f.read()
        
        # 备份
        backup_path = config_path + '.bak.' + datetime.now().strftime('%Y%m%d%H%M%S')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(existing)
        
        # 合并配置
        lines = existing.split('\n')
        new_lines = []
        in_proxies = False
        proxies_started = False
        
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith('proxies:'):
                in_proxies = True
                proxies_started = True
                # 提取订阅中的节点
                sub_nodes = []
                for sub_line in content.split('\n'):
                    sub_line_stripped = sub_line.strip()
                    if sub_line_stripped.startswith('- '):
                        sub_nodes.append(sub_line)
                    elif sub_line_stripped and not sub_line_stripped.startswith('#'):
                        if sub_line_stripped.startswith('proxies:'):
                            continue
                        if not sub_line_stripped.startswith('- ') and ':' in sub_line_stripped:
                            # 是配置项不是节点
                            in_proxies = False
                            break
                # 添加订阅节点
                for node in sub_nodes:
                    new_lines.append('  ' + node)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        return api_ok({
            'success': True,
            'path': config_path,
            'backup': backup_path,
            'message': '订阅更新成功',
        })
        
    except requests.exceptions.RequestException as e:
        return api_error(f'下载失败: {str(e)}', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@clash_bp.route('/api/clash/proxies', methods=['GET'])
def api_clash_proxies():
    """获取代理列表和当前选择"""
    config_path = _find_config()
    if not config_path:
        return api_error('Config file not found', status=404)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parsed = _parse_clash_yaml(content)
        
        # 尝试解析当前选中的节点（通过查找 proxy-groups 中的 selected）
        current_selection = {}
        lines = content.split('\n')
        in_proxy_groups = False
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('proxy-groups:') or 'Groups' in line_stripped:
                in_proxy_groups = True
                continue
            if in_proxy_groups:
                if line_stripped.startswith('- name:'):
                    group_name = line_stripped.replace('- name:', '').strip().strip('"').strip("'")
                    current_selection[group_name] = None
                elif 'proxies:' in line_stripped or 'proxy:' in line_stripped:
                    # 提取当前选中
                    for group_name in current_selection:
                        if group_name not in current_selection or current_selection[group_name] is None:
                            match = re.search(rf'{re.escape(group_name)}["\']?\s*,\s*proxies:\s*\[[^\]]*["\']?([^"\',\]]+)', line)
                            if match:
                                current_selection[group_name] = match.group(1).strip().strip('"').strip("'")
        
        return api_ok({
            'proxies': parsed['proxies'],
            'proxy_groups': parsed['proxy_groups'],
            'current_selection': current_selection,
            'ports': parsed['ports'],
            'rules_count': parsed['rules_count'],
        })
        
    except Exception as e:
        return api_error(str(e), status=500)


@clash_bp.route('/api/clash/switch', methods=['POST'])
def api_clash_switch():
    """切换代理节点（通过修改配置）"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    
    group_name = (data.get('group') or '').strip()
    proxy_name = (data.get('proxy') or '').strip()
    
    if not group_name or not proxy_name:
        return api_error('Missing group or proxy', status=400)
    
    config_path = _find_config()
    if not config_path:
        return api_error('Config file not found', status=404)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并替换代理组中的选中节点
        # 模式: name: xxx, proxies: [..., "新节点", ...]
        pattern = rf'({re.escape(group_name)}["\']?,?\s*proxies:\s*\[)([^"\']*"{re.escape(proxy_name)}["\']?)([^\]]*\])'
        
        def replacer(match):
            prefix = match.group(1)
            old_proxy = match.group(2)
            suffix = match.group(3)
            # 移除旧的选中节点，添加新的
            proxies = [p.strip().strip('"').strip("'") for p in (prefix + old_proxy + suffix).split(',') if p.strip() and p.strip() != old_proxy.strip()]
            # 将新节点放到第一位
            proxies = [proxy_name] + [p for p in proxies if p != proxy_name]
            return prefix + ', '.join([f'"{p}"' for p in proxies]) + suffix
        
        # 简化处理：只替换包含该组名的行中的节点名
        new_content = content
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if group_name in line and ('proxies:' in line or 'proxy:' in line):
                # 找到这行，替换节点名
                # 查找当前选中的节点并替换
                for proxy in re.findall(r'"([^"]+)"', line):
                    if proxy != proxy_name:
                        new_line = line.replace(f'"{proxy}"', f'"{proxy_name}"', 1)
                        lines[i] = new_line
                        break
        
        new_content = '\n'.join(lines)
        
        # 备份
        backup_path = config_path + '.switch.' + datetime.now().strftime('%Y%m%d%H%M%S')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return api_ok({
            'success': True,
            'message': f'已将 {group_name} 切换到 {proxy_name}',
            'backup': backup_path,
        })
        
    except Exception as e:
        return api_error(str(e), status=500)
