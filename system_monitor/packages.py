# 系统监控模块 - 包管理 (apt/dnf, pip, npm)

from flask import jsonify
import subprocess
import json
import re
import os


def detect_package_manager():
    """检测系统包管理器类型"""
    if subprocess.run(['which', 'dnf'], capture_output=True).returncode == 0:
        return 'dnf'
    elif subprocess.run(['which', 'apt'], capture_output=True).returncode == 0:
        return 'apt'
    return 'unknown'


def list_system_packages(manager=None):
    """获取系统已安装包列表"""
    if manager is None:
        manager = detect_package_manager()
    
    packages = []
    
    try:
        if manager == 'dnf':
            # CentOS/RHEL/Fedora - 使用 dnf repoquery
            result = subprocess.run(
                ['dnf', 'repoquery', '--installed', '--queryformat', '%{NAME} %{VERSION}'],
                capture_output=True, text=True, timeout=15
            )
            for line in result.stdout.strip().split('\n'):
                if line and ' ' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        packages.append({
                            'name': parts[0],
                            'version': parts[1],
                            'manager': 'dnf',
                            'install_time': None
                        })
        else:
            # Debian/Ubuntu
            result = subprocess.run(['dpkg', '-l'], capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                if line and line.startswith('ii '):
                    parts = line.split()
                    if len(parts) >= 3:
                        packages.append({
                            'name': parts[1],
                            'version': parts[2],
                            'manager': 'apt',
                            'install_time': None
                        })
        
        # 限制返回数量，按名称排序
        packages = packages[:200]
        packages.sort(key=lambda x: x['name'].lower())
        return {'success': True, 'packages': packages}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def uninstall_system_package(name, manager):
    """卸载系统包"""
    try:
        if manager == 'dnf':
            subprocess.run(['sudo', 'dnf', 'remove', '-y', name], capture_output=True, text=True)
        else:
            subprocess.run(['sudo', 'apt', 'remove', '-y', name], capture_output=True, text=True)
        return {'success': True, 'message': f'{name} 已卸载'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


# ============ Pip 包管理 ============

def list_pip_packages():
    """获取pip已安装包列表"""
    try:
        from pip._internal.operations.freeze import freeze
        packages = []
        
        for line in freeze():
            if '==' in line:
                name, version = line.split('==', 1)
                packages.append({'name': name, 'version': version})
        
        packages.sort(key=lambda x: x['name'].lower())
        return {'success': True, 'packages': packages}
    except Exception as e:
        # 备用方案：使用 pip list
        try:
            result = subprocess.run(['pip', 'list', '--format=json'], capture_output=True, text=True)
            packages = json.loads(result.stdout)
            packages.sort(key=lambda x: x['name'].lower())
            return {'success': True, 'packages': packages}
        except:
            return {'success': False, 'message': str(e)}


def install_pip_package(package):
    """安装pip包"""
    try:
        subprocess.run(['pip', 'install', package], capture_output=True, text=True)
        return {'success': True, 'message': f'{package} 已安装'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def uninstall_pip_package(package):
    """卸载pip包"""
    try:
        subprocess.run(['pip', 'uninstall', '-y', package], capture_output=True, text=True)
        return {'success': True, 'message': f'{package} 已卸载'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


# ============ NPM 包管理 ============

def find_npm():
    """查找 npm 命令路径"""
    # 直接检查常见的 nvm 路径
    nvm_paths = [
        '/root/.nvm/versions/node/v22.22.0/bin/npm',
        '/root/.nvm/versions/node/v20.10.0/bin/npm',
        '/root/.nvm/versions/node/v18.20.0/bin/npm',
        '/usr/local/bin/npm',
        '/usr/bin/npm',
    ]
    for path in nvm_paths:
        if os.path.exists(path):
            return path
    # 回退到 which
    result = subprocess.run(['which', 'npm'], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_npm_env():
    """获取适合 npm 运行的环境变量"""
    env = os.environ.copy()
    nvm_bin = '/root/.nvm/versions/node/v22.22.0/bin'
    if os.path.exists(nvm_bin):
        env['PATH'] = nvm_bin + ':' + env.get('PATH', '')
    return env


def list_npm_packages():
    """获取npm全局已安装包列表"""
    npm_cmd = find_npm()
    if not npm_cmd:
        return {'success': False, 'message': 'npm 未安装或未找到'}
    
    try:
        result = subprocess.run(
            [npm_cmd, 'list', '-g', '--depth=0', '--json'],
            capture_output=True, text=True, timeout=30, env=get_npm_env()
        )
        
        if result.returncode != 0:
            # 备用方案：使用文本解析
            result = subprocess.run(
                [npm_cmd, 'list', '-g', '--depth=0'],
                capture_output=True, text=True, timeout=30, env=get_npm_env()
            )
            packages = []
            for line in result.stdout.strip().split('\n'):
                match = re.match(r'^(\S+)@(\S+)$', line.strip())
                if match:
                    packages.append({'name': match.group(1), 'version': match.group(2)})
            packages.sort(key=lambda x: x['name'].lower())
            return {'success': True, 'packages': packages}
        
        data = json.loads(result.stdout)
        packages = []
        dependencies = data.get('dependencies', {})
        for name, info in dependencies.items():
            packages.append({'name': name, 'version': info.get('version', '')})
        packages.sort(key=lambda x: x['name'].lower())
        return {'success': True, 'packages': packages}
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'npm list 命令超时'}
    except json.JSONDecodeError:
        return {'success': False, 'message': 'npm 输出解析失败'}
    except Exception as e:
        return {'success': False, 'message': f'获取失败: {str(e)}'}


def install_npm_package(package):
    """安装npm包"""
    npm_cmd = find_npm()
    if not npm_cmd:
        return {'success': False, 'message': 'npm 未安装'}
    
    try:
        result = subprocess.run(
            [npm_cmd, 'install', '-g', package],
            capture_output=True, text=True, timeout=120, env=get_npm_env()
        )
        if result.returncode != 0:
            return {'success': False, 'message': f'安装失败: {result.stderr.strip()}'}
        return {'success': True, 'message': f'{package} 已安装'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': '安装超时，请检查网络连接'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def uninstall_npm_package(package):
    """卸载npm包"""
    npm_cmd = find_npm()
    if not npm_cmd:
        return {'success': False, 'message': 'npm 未安装'}
    
    try:
        result = subprocess.run(
            [npm_cmd, 'uninstall', '-g', package],
            capture_output=True, text=True, timeout=60, env=get_npm_env()
        )
        if result.returncode != 0:
            return {'success': False, 'message': f'卸载失败: {result.stderr.strip()}'}
        return {'success': True, 'message': f'{package} 已卸载'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': '卸载超时'}
    except Exception as e:
        return {'success': False, 'message': str(e)}
