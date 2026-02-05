import mimetypes
import os
import shutil
from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

import config
from lib import file_utils, path_utils


file_bp = Blueprint('file', __name__)


def _get_paths():
    root_dir = config.ROOT_DIR
    trash_dir = config.TRASH_DIR
    return root_dir, trash_dir


@file_bp.route('/')
@file_bp.route('/browse/')
@file_bp.route('/browse/<path:path>')
def browse(path=''):
    root_dir, _trash_dir = _get_paths()
    if path == '.' or path == '':
        current_dir = root_dir
    else:
        current_dir = os.path.join(root_dir, path)
    current_dir = os.path.normpath(current_dir)
    if not current_dir.startswith(root_dir):
        current_dir = root_dir
    if not os.path.exists(current_dir) or not os.path.isdir(current_dir):
        return "目录不存在", 404

    items = file_utils.list_directory(current_dir)
    breadcrumbs = path_utils.get_breadcrumbs(current_dir, root_dir)
    return render_template(
        'index.html',
        items=items,
        current_dir=current_dir,
        breadcrumbs=breadcrumbs,
        message=request.args.get('message'),
        msg_type=request.args.get('msg_type', 'success'),
        ROOT_DIR=root_dir,
        os=os,
    )


@file_bp.route('/view/<path:path>')
def view_file(path):
    root_dir, _trash_dir = _get_paths()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return "非法路径", 403
    if not os.path.exists(full_path):
        return "文件不存在", 404
    if os.path.isdir(full_path):
        return redirect(url_for('file.browse', path=path))

    mime_type, _ = mimetypes.guess_type(full_path)
    _, ext = os.path.splitext(full_path)
    ext_lower = ext.lower()
    chrome_native = [
        '.pdf',
        '.mp4',
        '.webm',
        '.ogg',
        '.mov',
        '.avi',
        '.mkv',
        '.mp3',
        '.wav',
        '.flac',
        '.aac',
        '.m4a',
        '.svg',
        '.ico',
        '.webp',
        '.avif',
    ]

    if ext_lower in chrome_native:
        return redirect(url_for('file.serve_file', path=path))
    if mime_type and (
        mime_type.startswith('image')
        or ext_lower in file_utils.IMAGE_EXTENSIONS
    ):
        return render_template(
            'image_viewer.html',
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
        )
    if ext_lower in ['.xlsx', '.xls']:
        return render_template(
            'excel_viewer.html',
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
        )
    if ext_lower in ['.docx', '.doc']:
        return render_template(
            'word_viewer.html',
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
        )
    if mime_type and mime_type.startswith('text'):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return render_template(
                "code_mirror.html",
                content=content,
                filename=os.path.basename(full_path),
                file_path=path,
                current_dir=os.path.dirname(path),
                extension=ext_lower,
            )
        except UnicodeDecodeError:
            try:
                with open(full_path, 'r', encoding='gbk') as f:
                    content = f.read()
                return render_template(
                    "code_mirror.html",
                    content=content,
                    filename=os.path.basename(full_path),
                    file_path=path,
                    current_dir=os.path.dirname(path),
                    extension=ext_lower,
                )
            except Exception:
                return redirect(url_for('file.download_file', path=path))

    return redirect(url_for('file.download_file', path=path))


@file_bp.route('/edit/<path:path>')
def edit_file(path):
    root_dir, _trash_dir = _get_paths()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return "非法路径", 403
    if not os.path.exists(full_path):
        return "文件不存在", 404
    if os.path.isdir(full_path):
        return redirect(url_for('file.browse', path=path))

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(full_path, 'r', encoding='gbk') as f:
                content = f.read()
        except Exception:
            return "无法读取文件内容", 400

    _, ext = os.path.splitext(full_path)
    if ext.lower() in file_utils.MARKDOWN_EXTENSIONS:
        return render_template(
            "markdown_editor.html",
            content=content,
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
        )

    extension = ext.lower()
    if extension not in file_utils.CODE_EXTENSIONS:
        extension = '.txt'
    return render_template(
        "code_editor.html",
        content=content,
        filename=os.path.basename(full_path),
        file_path=path,
        current_dir=os.path.dirname(path),
        extension=extension,
    )


@file_bp.route('/save_file/<path:path>', methods=['POST'])
def save_file(path):
    root_dir, _trash_dir = _get_paths()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        payload = request.get_json() or {}
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(payload.get('content', ''))
        return jsonify({'success': True, 'message': '文件保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@file_bp.route('/download/<path:path>')
def download_file(path):
    root_dir, _trash_dir = _get_paths()
    path = (path or '').lstrip('/\\').replace('\\', '/')
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return "非法路径", 403
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return "文件不存在", 404
    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path),
        as_attachment=True,
    )


@file_bp.route('/serve/<path:path>')
def serve_file(path):
    root_dir, _trash_dir = _get_paths()
    path = (path or '').lstrip('/\\').replace('\\', '/')
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return "非法路径", 403
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return "文件不存在", 404

    mime_types = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.py': 'text/x-python',
        '.sh': 'application/x-sh',
        '.yaml': 'application/yaml',
        '.yml': 'application/yaml',
        '.csv': 'text/csv',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.webp': 'image/webp',
    }
    ext = os.path.splitext(path)[1].lower()
    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path),
        mimetype=mime_types.get(ext),
    )


@file_bp.route('/thumbnail/<path:path>')
def thumbnail(path):
    return serve_file(path)


@file_bp.route('/upload/', methods=['POST'])
@file_bp.route('/upload/<path:path>', methods=['POST'])
def upload_file(path=''):
    root_dir, _trash_dir = _get_paths()
    if 'file' not in request.files:
        return redirect(
            url_for(
                'file.browse',
                path=path,
                message='没有选择文件',
                msg_type='error',
            )
        )
    file = request.files['file']
    if file.filename == '':
        return redirect(
            url_for(
                'file.browse',
                path=path,
                message='没有选择文件',
                msg_type='error',
            )
        )
    upload_dir = os.path.normpath(os.path.join(root_dir, path))
    if not upload_dir.startswith(root_dir):
        upload_dir = root_dir
    if file:
        filename = file.filename
        filepath = os.path.join(upload_dir, filename)
        counter = 1
        name, ext = os.path.splitext(filename)
        while os.path.exists(filepath):
            filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(upload_dir, filename)
            counter += 1
        file.save(filepath)
        return redirect(
            url_for(
                'file.browse',
                path=path,
                message='文件上传成功',
                msg_type='success',
            )
        )
    return redirect(url_for('file.browse', path=path))


@file_bp.route('/delete/<path:path>', methods=['DELETE'])
def delete_item(path):
    root_dir, trash_dir = _get_paths()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    if os.path.normpath(full_path) == os.path.normpath(trash_dir):
        return jsonify({'success': False, 'message': '不能删除回收站文件夹'})
    try:
        os.makedirs(trash_dir, exist_ok=True)
        item_name = os.path.basename(full_path)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        trash_name = f"{timestamp}_{item_name}"
        trash_path = os.path.join(trash_dir, trash_name)
        counter = 1
        while os.path.exists(trash_path):
            trash_name = f"{timestamp}_{item_name}_{counter}"
            trash_path = os.path.join(trash_dir, trash_name)
            counter += 1
        shutil.move(full_path, trash_path)
        return jsonify({'success': True, 'message': '已移到回收站'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@file_bp.route('/rename/<path:path>', methods=['POST'])
def rename_item(path):
    root_dir, _trash_dir = _get_paths()
    payload = request.json if isinstance(request.json, dict) else {}
    new_name = (payload.get('new_name') or '').strip()
    if not new_name:
        return jsonify({'success': False, 'message': '请输入新名称'})
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        new_path = os.path.normpath(
            os.path.join(os.path.dirname(full_path), new_name)
        )
        if not new_path.startswith(root_dir):
            return jsonify({'success': False, 'message': '非法路径'})
        os.rename(full_path, new_path)
        return jsonify({'success': True, 'message': '重命名成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@file_bp.route('/move/<path:path>', methods=['POST'])
def move_item(path):
    root_dir, _trash_dir = _get_paths()
    payload = request.json if isinstance(request.json, dict) else {}
    target_path = (payload.get('target_path') or '').strip()
    if not target_path:
        return jsonify({'success': False, 'message': '请输入目标路径'})
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        target_full = os.path.normpath(os.path.join(root_dir, target_path))
        if not target_full.startswith(root_dir):
            return jsonify({'success': False, 'message': '非法路径'})
        os.makedirs(target_full, exist_ok=True)
        item_name = os.path.basename(full_path)
        new_location = os.path.join(target_full, item_name)
        if os.path.exists(new_location):
            return jsonify({'success': False, 'message': '目标位置已存在同名文件'})
        shutil.move(full_path, new_location)
        return jsonify({'success': True, 'message': '移动成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@file_bp.route('/clone/<path:path>', methods=['POST'])
def clone_item(path):
    root_dir, _trash_dir = _get_paths()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'})
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': '文件不存在'})
    try:
        item_name = os.path.basename(full_path)
        parent_dir = os.path.dirname(full_path)
        if os.path.isdir(full_path):
            clone_name = f"{item_name}_clone"
            clone_path = os.path.join(parent_dir, clone_name)
            counter = 1
            while os.path.exists(clone_path):
                clone_name = f"{item_name}_clone_{counter}"
                clone_path = os.path.join(parent_dir, clone_name)
                counter += 1
            shutil.copytree(full_path, clone_path)
        else:
            name, ext = os.path.splitext(item_name)
            clone_name = f"{name}_clone{ext}"
            clone_path = os.path.join(parent_dir, clone_name)
            counter = 1
            while os.path.exists(clone_path):
                clone_name = f"{name}_clone_{counter}{ext}"
                clone_path = os.path.join(parent_dir, clone_name)
                counter += 1
            shutil.copy2(full_path, clone_path)
        return jsonify({'success': True, 'message': f'克隆到 {clone_name}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@file_bp.route('/mkdir', methods=['POST'])
@file_bp.route('/mkdir/<path:parent>', methods=['POST'])
def mkdir(parent=''):
    root_dir, _trash_dir = _get_paths()
    parent = (parent or '').lstrip('/\\').replace('\\', '/')
    name = (request.json or {}).get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '请输入名称'}), 400
    if any(sep in name for sep in ['/', '\\']):
        return jsonify({'success': False, 'message': '非法名称'}), 400
    parent_full = os.path.normpath(os.path.join(root_dir, parent))
    if not parent_full.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'}), 403
    try:
        target = os.path.normpath(os.path.join(parent_full, name))
        if not target.startswith(root_dir):
            return jsonify({'success': False, 'message': '非法路径'}), 403
        if os.path.exists(target):
            return jsonify({'success': False, 'message': '已存在同名项目'}), 409
        os.makedirs(target, exist_ok=False)
        return jsonify({'success': True, 'message': '创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@file_bp.route('/touch', methods=['POST'])
@file_bp.route('/touch/<path:parent>', methods=['POST'])
def touch(parent=''):
    root_dir, _trash_dir = _get_paths()
    parent = (parent or '').lstrip('/\\').replace('\\', '/')
    name = (request.json or {}).get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': '请输入名称'}), 400
    if any(sep in name for sep in ['/', '\\']):
        return jsonify({'success': False, 'message': '非法名称'}), 400
    parent_full = os.path.normpath(os.path.join(root_dir, parent))
    if not parent_full.startswith(root_dir):
        return jsonify({'success': False, 'message': '非法路径'}), 403
    try:
        target = os.path.normpath(os.path.join(parent_full, name))
        if not target.startswith(root_dir):
            return jsonify({'success': False, 'message': '非法路径'}), 403
        if os.path.exists(target):
            return jsonify({'success': False, 'message': '已存在同名项目'}), 409
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'x', encoding='utf-8'):
            pass
        return jsonify({'success': True, 'message': '创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@file_bp.route('/trash')
def trash():
    _root_dir, trash_dir = _get_paths()
    os.makedirs(trash_dir, exist_ok=True)
    items = []
    for name in os.listdir(trash_dir):
        if name.startswith('.'):
            continue
        path = os.path.join(trash_dir, name)
        parts = name.split('_', 2)
        deleted_at = parts[0] if len(parts) >= 2 else '未知'
        try:
            dt = datetime.strptime(deleted_at, '%Y%m%d%H%M%S')
            deleted_at = dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
        items.append({
            'name': name,
            'path': path,
            'deleted_at': deleted_at,
            'is_dir': os.path.isdir(path),
        })
    items.sort(key=lambda x: x['name'], reverse=True)
    return render_template("trash.html", items=items)


@file_bp.route('/trash/clear', methods=['POST'])
def trash_clear():
    _root_dir, trash_dir = _get_paths()
    os.makedirs(trash_dir, exist_ok=True)
    try:
        for name in os.listdir(trash_dir):
            if name.startswith('.'):
                continue
            path = os.path.join(trash_dir, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        return jsonify({'success': True, 'message': '回收站已清空'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@file_bp.route('/trash/restore/<name>', methods=['POST'])
def trash_restore(name):
    root_dir, trash_dir = _get_paths()
    os.makedirs(trash_dir, exist_ok=True)
    if not name or '/' in name or '\\' in name:
        return jsonify({'success': False, 'message': '非法名称'}), 400
    trash_item = os.path.normpath(os.path.join(trash_dir, name))
    if not trash_item.startswith(os.path.normpath(trash_dir)):
        return jsonify({'success': False, 'message': '非法路径'}), 400
    if not os.path.exists(trash_item):
        return jsonify({'success': False, 'message': '文件不存在'}), 404

    payload = request.get_json(silent=True) or {}
    target_path = (payload.get('target_path') or '').strip()
    if not target_path:
        return jsonify({'success': False, 'message': '请输入还原路径'}), 400

    target_full = os.path.normpath(os.path.join(root_dir, target_path))
    if not target_full.startswith(os.path.normpath(root_dir)):
        return jsonify({'success': False, 'message': '非法路径'}), 403
    if os.path.exists(target_full):
        return jsonify({'success': False, 'message': '目标已存在'}), 409

    try:
        os.makedirs(os.path.dirname(target_full), exist_ok=True)
        shutil.move(trash_item, target_full)
        return jsonify({'success': True, 'message': '还原成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
