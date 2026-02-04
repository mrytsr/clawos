import os


def get_relative_path(path, root_dir):
    """获取相对于ROOT_DIR的路径"""
    if path is None:
        return ''
    path = str(path).replace('\\', '/')
    root_dir = str(root_dir).replace('\\', '/')
    if path.startswith(root_dir):
        rel_path = path[len(root_dir):]
        rel_path = rel_path.lstrip('/').lstrip('\\')
        if rel_path == '' or rel_path == '.':
            return ''
        return rel_path
    return path.lstrip('/').lstrip('\\')


def get_breadcrumbs(current_path, root_dir):
    """生成面包屑导航"""
    breadcrumbs = []
    rel_path = get_relative_path(current_path, root_dir)
    if rel_path and rel_path != '.' and rel_path != '/':
        parts = rel_path.strip('/').split('/')
        current = root_dir
        for part in parts:
            if part:
                current = os.path.join(current, part)
                breadcrumbs.append({'name': part, 'path': current})
    return breadcrumbs


def safe_path_join(base, *paths, root_dir=None):
    """安全地连接路径，防止路径遍历"""
    final_path = os.path.join(base, *paths)
    final_path = os.path.normpath(final_path)
    if root_dir and not final_path.startswith(root_dir):
        return base
    return final_path


def format_size(size):
    """格式化文件大小"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{round(size / 1024, 2)} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{round(size / (1024 * 1024), 2)} MB"
    else:
        return f"{round(size / (1024 * 1024 * 1024), 2)} GB"


def get_file_icon(extension):
    """根据文件扩展名返回对应的图标"""
    icons = {
        '.txt': '📄',
        '.pdf': '📕',
        '.doc': '📘',
        '.docx': '📘',
        '.xls': '📗',
        '.xlsx': '📗',
        '.ppt': '📙',
        '.pptx': '📙',
        '.zip': '📦',
        '.rar': '📦',
        '.tar': '📦',
        '.gz': '📦',
        '.py': '🐍',
        '.js': '📜',
        '.html': '🌐',
        '.css': '🎨',
        '.json': '📋',
        '.xml': '📋',
        '.csv': '📊',
        '.md': '📝',
        '.markdown': '📝',
        '.mp3': '🎵',
        '.wav': '🎵',
        '.mp4': '🎬',
        '.avi': '🎬',
        '.mov': '🎬',
    }
    return icons.get(extension.lower(), '📁' if os.path.isdir(extension) else '📄')
