import os
import shutil
from datetime import datetime

from flask import Blueprint, request

import config
from ctrl import api_error, api_ok


batch_bp = Blueprint('batch', __name__)


@batch_bp.route('/api/batch/delete', methods=['POST'])
def batch_delete():
    root_dir = config.ROOT_DIR
    trash_dir = config.TRASH_DIR

    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    paths = data.get('paths', [])
    if not paths:
        return api_error('请选择要删除的文件', status=400)

    deleted, errors = [], []
    for path in paths:
        full_path = os.path.normpath(os.path.join(root_dir, path))
        if not full_path.startswith(root_dir):
            errors.append({'path': path, 'error': '非法路径'})
            continue
        if not os.path.exists(full_path):
            errors.append({'path': path, 'error': '文件不存在'})
            continue
        try:
            os.makedirs(trash_dir, exist_ok=True)
            item_name = os.path.basename(full_path)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            trash_name = f"{timestamp}_{item_name}"
            trash_path = os.path.join(trash_dir, trash_name)
            shutil.move(full_path, trash_path)
            deleted.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})

    return api_ok({
        'deleted': deleted,
        'errors': errors,
        'message': f'已删除 {len(deleted)} 个项目',
    })


@batch_bp.route('/api/batch/copy', methods=['POST'])
def batch_copy():
    root_dir = config.ROOT_DIR

    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    paths = data.get('paths', [])
    target_path = data.get('target')
    if target_path is None:
        target_path = ''
    if not isinstance(target_path, str):
        return api_error('参数不完整', status=400)
    target_path = target_path.strip()
    if not paths:
        return api_error('参数不完整', status=400)

    if target_path == '':
        target_full = root_dir
    else:
        target_full = os.path.normpath(os.path.join(root_dir, target_path))
    if not target_full.startswith(root_dir) or not os.path.isdir(target_full):
        return api_error('目标位置无效', status=400)

    copied, errors = [], []
    for path in paths:
        full_path = os.path.normpath(os.path.join(root_dir, path))
        if not full_path.startswith(root_dir) or not os.path.exists(full_path):
            errors.append({'path': path, 'error': '无效路径'})
            continue
        try:
            item_name = os.path.basename(full_path)
            new_path = os.path.join(target_full, item_name)
            counter = 1
            while os.path.exists(new_path):
                name, ext = os.path.splitext(item_name)
                new_name = f"{name}_{counter}{ext}"
                new_path = os.path.join(target_full, new_name)
                counter += 1
            if os.path.isdir(full_path):
                shutil.copytree(full_path, new_path)
            else:
                shutil.copy2(full_path, new_path)
            copied.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})

    return api_ok({
        'copied': copied,
        'errors': errors,
        'message': f'已复制 {len(copied)} 个项目',
    })


@batch_bp.route('/api/batch/move', methods=['POST'])
def batch_move():
    root_dir = config.ROOT_DIR

    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    paths = data.get('paths', [])
    target_path = data.get('target')
    if target_path is None:
        target_path = ''
    if not isinstance(target_path, str):
        return api_error('参数不完整', status=400)
    target_path = target_path.strip()
    if not paths:
        return api_error('参数不完整', status=400)

    if target_path == '':
        target_full = root_dir
    else:
        target_full = os.path.normpath(os.path.join(root_dir, target_path))
    if not target_full.startswith(root_dir) or not os.path.isdir(target_full):
        return api_error('目标位置无效', status=400)

    moved, errors = [], []
    for path in paths:
        full_path = os.path.normpath(os.path.join(root_dir, path))
        if not full_path.startswith(root_dir) or not os.path.exists(full_path):
            errors.append({'path': path, 'error': '无效路径'})
            continue
        try:
            item_name = os.path.basename(full_path)
            new_path = os.path.join(target_full, item_name)
            counter = 1
            while os.path.exists(new_path):
                name, ext = os.path.splitext(item_name)
                new_name = f"{name}_{counter}{ext}"
                new_path = os.path.join(target_full, new_name)
                counter += 1
            shutil.move(full_path, new_path)
            moved.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})

    return api_ok({
        'moved': moved,
        'errors': errors,
        'message': f'已移动 {len(moved)} 个项目',
    })


@batch_bp.route('/api/batch/symlink', methods=['POST'])
def batch_symlink():
    """批量创建软链接"""
    root_dir = config.ROOT_DIR
    
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    paths = data.get('paths', [])
    target_path = data.get('target')
    if target_path is None:
        target_path = ''
    if not isinstance(target_path, str):
        return api_error('参数不完整', status=400)
    target_path = target_path.strip()
    if not paths:
        return api_error('参数不完整', status=400)

    if target_path == '':
        target_full = root_dir
    else:
        target_full = os.path.normpath(os.path.join(root_dir, target_path))
    if not target_full.startswith(root_dir) or not os.path.isdir(target_full):
        return api_error('目标位置无效', status=400)

    linked, errors = [], []
    for path in paths:
        full_path = os.path.normpath(os.path.join(root_dir, path))
        if not full_path.startswith(root_dir) or not os.path.exists(full_path):
            errors.append({'path': path, 'error': '无效路径'})
            continue
        try:
            item_name = os.path.basename(full_path)
            link_path = os.path.join(target_full, item_name)
            counter = 1
            while os.path.exists(link_path):
                name, ext = os.path.splitext(item_name)
                new_name = f"{name}_link{counter}{ext}"
                link_path = os.path.join(target_full, new_name)
                counter += 1
            os.symlink(full_path, link_path)
            linked.append(path)
        except Exception as e:
            errors.append({'path': path, 'error': str(e)})

    return api_ok({
        'linked': linked,
        'errors': errors,
        'message': f'已创建链接 {len(linked)} 个项目',
    })
