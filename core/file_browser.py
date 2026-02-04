# 核心模块 - 文件浏览器核心逻辑

import os
from datetime import datetime
from utils import get_file_icon, format_size


# 配置
HIDDEN_FOLDERS = {'__pycache__', '.git', '_trash'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
MARKDOWN_EXTENSIONS = {'.md', '.markdown'}
CODE_EXTENSIONS = {
    '.py', '.js', '.html', '.css', '.json', '.xml', '.txt', '.service',
    '.yaml', '.yml', '.sh', '.bash', '.zsh', '.md', '.markdown', '.vue', '.ts', '.tsx',
    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.php', '.rb', '.pl', '.lua',
    '.sql', '.ini', '.conf', '.cfg', '.log', '.bat', '.ps1', '.dockerfile', '.gitignore',
    '.env', '.properties', '.toml'
}


def get_file_info(path):
    """获取文件信息"""
    stat = os.stat(path)
    return {
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'is_dir': os.path.isdir(path)
    }


def list_directory(directory):
    """列出目录内容，排除隐藏的文件夹"""
    items = []
    try:
        for item in os.listdir(directory):
            if item in HIDDEN_FOLDERS:
                continue
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                info = get_file_info(item_path)
                items.append({
                    'name': item,
                    'path': item_path,
                    'icon': '📁',
                    'size': '-',
                    'modified': info['modified'],
                    'is_dir': True,
                    'is_image': False,
                    'extension': ''
                })
            else:
                _, ext = os.path.splitext(item)
                info = get_file_info(item_path)
                is_image = ext.lower() in IMAGE_EXTENSIONS
                items.append({
                    'name': item,
                    'path': item_path,
                    'icon': get_file_icon(ext),
                    'size': format_size(info['size']),
                    'modified': info['modified'],
                    'is_dir': False,
                    'is_image': is_image,
                    'extension': ext.lower()
                })
    except PermissionError:
        pass
    items.sort(key=lambda x: (not x['is_dir'], x['name']))
    return items


def get_file_details(path, root_dir):
    """获取文件/文件夹详情"""
    full_path = os.path.join(root_dir, path)
    full_path = os.path.normpath(full_path)
    
    if not full_path.startswith(os.path.normpath(root_dir)):
        return {'success': False, 'message': '无效路径'}
    
    if not os.path.exists(full_path):
        return {'success': False, 'message': '文件不存在'}
    
    try:
        try:
            import pwd
        except Exception:
            pwd = None
        stat = os.stat(full_path)
        is_dir = os.path.isdir(full_path)
        
        perms = oct(stat.st_mode)[-3:]
        
        try:
            if pwd is None:
                owner = str(stat.st_uid)
            else:
                owner = pwd.getpwuid(stat.st_uid).pw_name
        except:
            owner = str(stat.st_uid)
        
        import time
        ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_ctime))
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        atime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_atime))
        
        size = stat.st_size
        if size < 1024:
            size_human = f'{size} B'
        elif size < 1024 * 1024:
            size_human = f'{size / 1024:.1f} KB'
        elif size < 1024 * 1024 * 1024:
            size_human = f'{size / 1024 / 1024:.1f} MB'
        else:
            size_human = f'{size / 1024 / 1024 / 1024:.1f} GB'
        
        return {
            'success': True,
            'info': {
                'path': path,
                'name': os.path.basename(full_path),
                'is_dir': is_dir,
                'size': size,
                'size_human': size_human,
                'permissions': perms,
                'owner': owner,
                'ctime': ctime,
                'mtime': mtime,
                'atime': atime
            }
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}


def search_files(root_dir, keyword, hidden_folders=HIDDEN_FOLDERS):
    """搜索文件"""
    if not keyword.strip():
        return {'results': []}
    
    results = []
    try:
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in hidden_folders and not d.startswith('.')]
            
            for name in files:
                if name.startswith('.'):
                    continue
                if keyword.lower() in name.lower():
                    full_path = os.path.join(root, name)
                    rel_path = full_path[len(root_dir):].lstrip('/')
                    ext = os.path.splitext(name)[1].lower()
                    stat = os.stat(full_path)
                    
                    results.append({
                        'name': name,
                        'path': rel_path,
                        'is_dir': False,
                        'size': format_size(stat.st_size),
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'icon': get_file_icon(ext)
                    })
            
            for name in dirs:
                if keyword.lower() in name.lower():
                    full_path = os.path.join(root, name)
                    rel_path = full_path[len(root_dir):].lstrip('/')
                    
                    results.append({
                        'name': name,
                        'path': rel_path,
                        'is_dir': True,
                        'size': '-',
                        'modified': '-',
                        'icon': '📁'
                    })
    except Exception as e:
        return {'error': str(e)}
    
    results.sort(key=lambda x: (not x['is_dir'], x['name']))
    return {'results': results[:100]}
