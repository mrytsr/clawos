import mimetypes
import os
import shutil
import subprocess
import tarfile
import zipfile
from urllib.parse import quote
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
    if ext_lower in file_utils.MARKDOWN_EXTENSIONS:
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                raw_markdown = f.read()
        except UnicodeDecodeError:
            with open(full_path, 'r', encoding='gbk', errors='replace') as f:
                raw_markdown = f.read()
        return render_template(
            'markdown.html',
            raw_markdown=raw_markdown,
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
        )
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
    if ext_lower in ['.ppt', '.pptx']:
        src = (request.url_root or '').rstrip('/') + url_for('file.serve_file', path=path)
        return redirect('https://view.officeapps.live.com/op/view.aspx?src=' + quote(src, safe=''))
    if mime_type and mime_type.startswith('text'):
        max_bytes = 1024 * 1024
        size = os.path.getsize(full_path)
        truncated = size > max_bytes
        with open(full_path, 'rb') as f:
            raw = f.read(max_bytes if truncated else None)
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            content = raw.decode('gbk', errors='replace')
        return render_template(
            "code_mirror.html",
            content=content,
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
            extension=ext_lower,
            truncated=truncated,
            total_size=size,
        )

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
        '.avif': 'image/avif',
        '.pdf': 'application/pdf',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.ogg': 'application/ogg',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.flac': 'audio/flac',
        '.aac': 'audio/aac',
        '.m4a': 'audio/mp4',
    }
    ext = os.path.splitext(path)[1].lower()
    mime = mime_types.get(ext)
    if not mime:
        guessed, _ = mimetypes.guess_type(full_path)
        mime = guessed
    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path),
        mimetype=mime,
    )


def _resolve_safe_file(path):
    root_dir, _trash_dir = _get_paths()
    root_dir = os.path.normpath(root_dir)
    p = (path or '').lstrip('/\\').replace('\\', '/')
    full_path = os.path.normpath(os.path.join(root_dir, p))
    try:
        if os.path.commonpath([root_dir, full_path]) != root_dir:
            return None, None, "非法路径"
    except Exception:
        return None, None, "非法路径"
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        return None, None, "文件不存在"
    return root_dir, full_path, None


def _is_archive_name(name):
    n = (name or '').lower()
    if n.endswith('.tar.gz') or n.endswith('.tar.bz2') or n.endswith('.tar.xz'):
        return True
    ext = os.path.splitext(n)[1].lower()
    return ext in {'.zip', '.rar', '.tar', '.tgz', '.7z'}


def _archive_kind(name):
    n = (name or '').lower()
    if n.endswith('.tar.gz'):
        return 'tar'
    if n.endswith('.tar.bz2'):
        return 'tar'
    if n.endswith('.tar.xz'):
        return 'tar'
    ext = os.path.splitext(n)[1].lower()
    if ext == '.tgz':
        return 'tar'
    if ext == '.tar':
        return 'tar'
    if ext == '.zip':
        return 'zip'
    if ext in {'.7z', '.rar'}:
        return '7z'
    return None


def _safe_join(base_dir, member_path):
    rel = (member_path or '').replace('\\', '/')
    if not rel or rel.startswith('/') or rel.startswith('\\'):
        return None
    if ':' in rel.split('/')[0]:
        return None
    norm_base = os.path.normpath(base_dir)
    norm = os.path.normpath(os.path.join(norm_base, rel))
    try:
        if os.path.commonpath([norm_base, norm]) != norm_base:
            return None
    except Exception:
        return None
    if not norm.startswith(norm_base):
        return None
    return norm


@file_bp.route('/api/archive/list/<path:path>')
def api_archive_list(path):
    root_dir, full_path, err = _resolve_safe_file(path)
    if err:
        return jsonify({'success': False, 'error': {'message': err}}), 400
    name = os.path.basename(full_path)
    if not _is_archive_name(name):
        return jsonify({'success': False, 'error': {'message': '不是压缩包'}}), 400

    kind = _archive_kind(name)
    items = []
    try:
        if kind == 'zip':
            dirs = set()
            with zipfile.ZipFile(full_path, 'r') as zf:
                for info in zf.infolist():
                    inner = (info.filename or '').replace('\\', '/')
                    if not inner or inner.startswith('/') or ':' in inner.split('/')[0]:
                        continue
                    if inner.endswith('/'):
                        dirs.add(inner.rstrip('/'))
                        continue
                    parts = inner.split('/')
                    if len(parts) > 1:
                        acc = ''
                        for seg in parts[:-1]:
                            acc = (acc + '/' + seg) if acc else seg
                            dirs.add(acc)
                    items.append({
                        'path': inner,
                        'is_dir': False,
                        'size': int(info.file_size or 0),
                        'size_human': path_utils.format_size(int(info.file_size or 0)),
                    })
            for d in dirs:
                items.append({'path': d + '/', 'is_dir': True, 'size': 0, 'size_human': ''})
        elif kind == 'tar':
            dirs = set()
            with tarfile.open(full_path, 'r:*') as tf:
                for m in tf.getmembers():
                    inner = (m.name or '').replace('\\', '/')
                    if not inner or inner.startswith('/') or ':' in inner.split('/')[0]:
                        continue
                    if '..' in inner.split('/'):
                        continue
                    if m.isdir():
                        dirs.add(inner.rstrip('/'))
                        continue
                    parts = inner.split('/')
                    if len(parts) > 1:
                        acc = ''
                        for seg in parts[:-1]:
                            acc = (acc + '/' + seg) if acc else seg
                            dirs.add(acc)
                    size = int(m.size or 0)
                    items.append({
                        'path': inner,
                        'is_dir': False,
                        'size': size,
                        'size_human': path_utils.format_size(size),
                    })
            for d in dirs:
                items.append({'path': d + '/', 'is_dir': True, 'size': 0, 'size_human': ''})
        else:
            seven = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
            if not seven:
                return jsonify({'success': False, 'error': {'message': '缺少 7z 命令，无法预览该压缩包'}}), 400
            proc = subprocess.run([seven, 'l', '-slt', full_path], capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                return jsonify({'success': False, 'error': {'message': (proc.stderr or proc.stdout or '列出失败').strip()}}), 400
            blocks = (proc.stdout or '').split('\n\n')
            for b in blocks:
                if 'Path = ' not in b:
                    continue
                inner = None
                is_dir = False
                size = 0
                for line in b.splitlines():
                    if line.startswith('Path = '):
                        inner = line[len('Path = '):].strip().replace('\\', '/')
                    elif line.startswith('Attributes = '):
                        attrs = line[len('Attributes = '):]
                        if 'D' in attrs:
                            is_dir = True
                    elif line.startswith('Size = '):
                        try:
                            size = int(line[len('Size = '):].strip() or 0)
                        except Exception:
                            size = 0
                if not inner or inner == name:
                    continue
                if inner.startswith('/') or ':' in inner.split('/')[0] or '..' in inner.split('/'):
                    continue
                if is_dir and not inner.endswith('/'):
                    inner = inner + '/'
                items.append({
                    'path': inner,
                    'is_dir': bool(is_dir),
                    'size': int(size or 0),
                    'size_human': '' if is_dir else path_utils.format_size(int(size or 0)),
                })

        items.sort(key=lambda x: (not x.get('is_dir', False), x.get('path', '').lower()))
        return jsonify({'success': True, 'data': {'items': items}})
    except Exception as e:
        return jsonify({'success': False, 'error': {'message': str(e)}}), 500


@file_bp.route('/api/archive/extract/<path:path>', methods=['POST'])
def api_archive_extract(path):
    root_dir, full_path, err = _resolve_safe_file(path)
    if err:
        return jsonify({'success': False, 'error': {'message': err}}), 400
    name = os.path.basename(full_path)
    if not _is_archive_name(name):
        return jsonify({'success': False, 'error': {'message': '不是压缩包'}}), 400

    payload = request.get_json(silent=True) or {}
    target_dir = (payload.get('target_dir') or '').strip()
    if not target_dir:
        target_dir = os.path.dirname((path or '').replace('\\', '/'))
    dest_full = os.path.normpath(os.path.join(root_dir, target_dir))
    try:
        if os.path.commonpath([root_dir, dest_full]) != root_dir:
            return jsonify({'success': False, 'error': {'message': '非法目标目录'}}), 400
    except Exception:
        return jsonify({'success': False, 'error': {'message': '非法目标目录'}}), 400
    os.makedirs(dest_full, exist_ok=True)

    kind = _archive_kind(name)
    extracted = 0
    try:
        if kind == 'zip':
            with zipfile.ZipFile(full_path, 'r') as zf:
                for info in zf.infolist():
                    inner = (info.filename or '').replace('\\', '/')
                    if not inner or inner.endswith('/') or inner.startswith('/') or ':' in inner.split('/')[0] or '..' in inner.split('/'):
                        if inner and inner.endswith('/'):
                            d = _safe_join(dest_full, inner.rstrip('/'))
                            if d:
                                os.makedirs(d, exist_ok=True)
                        continue
                    out_path = _safe_join(dest_full, inner)
                    if not out_path:
                        continue
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    with zf.open(info, 'r') as src, open(out_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    extracted += 1
        elif kind == 'tar':
            with tarfile.open(full_path, 'r:*') as tf:
                for m in tf.getmembers():
                    inner = (m.name or '').replace('\\', '/')
                    if not inner or inner.startswith('/') or ':' in inner.split('/')[0] or '..' in inner.split('/'):
                        continue
                    out_path = _safe_join(dest_full, inner)
                    if not out_path:
                        continue
                    if m.isdir():
                        os.makedirs(out_path, exist_ok=True)
                        continue
                    if not m.isreg():
                        continue
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    src = tf.extractfile(m)
                    if not src:
                        continue
                    with src, open(out_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    extracted += 1
        else:
            seven = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
            if not seven:
                return jsonify({'success': False, 'error': {'message': '缺少 7z 命令，无法解压该压缩包'}}), 400
            proc = subprocess.run([seven, 'x', '-y', '-o' + dest_full, full_path], capture_output=True, text=True, timeout=300)
            if proc.returncode != 0:
                return jsonify({'success': False, 'error': {'message': (proc.stderr or proc.stdout or '解压失败').strip()}}), 400
            extracted = 1
        return jsonify({'success': True, 'data': {'extracted': extracted, 'target_dir': target_dir}})
    except Exception as e:
        return jsonify({'success': False, 'error': {'message': str(e)}}), 500


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
