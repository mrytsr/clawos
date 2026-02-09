import os

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import config
from lib import file_utils


edit_bp = Blueprint('edit', __name__)


def _get_root_dir():
    return os.path.normpath(config.ROOT_DIR)


def _resolve_file_path(path):
    root_dir = _get_root_dir()
    p = (path or '').lstrip('/\\').replace('\\', '/')
    full_path = os.path.normpath(os.path.join(root_dir, p))
    try:
        if os.path.commonpath([root_dir, full_path]) != root_dir:
            return None, None, "非法路径"
    except Exception:
        return None, None, "非法路径"
    if not os.path.exists(full_path):
        return None, None, "文件不存在"
    return root_dir, full_path, None


def _read_text_file(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read(), 'utf-8'
    except UnicodeDecodeError:
        with open(full_path, 'r', encoding='gbk', errors='replace') as f:
            return f.read(), 'gbk'


@edit_bp.route('/edit/<path:path>')
def edit_file(path):
    root_dir, full_path, err = _resolve_file_path(path)
    if err:
        return err, 403 if err == "非法路径" else 404
    if os.path.isdir(full_path):
        return redirect(url_for('browser.browse', path=path))

    content, _enc = _read_text_file(full_path)
    _, ext = os.path.splitext(full_path)
    ext_lower = ext.lower()
    current_dir = os.path.dirname((path or '').replace('\\', '/'))
    filename = os.path.basename(full_path)

    if ext_lower in file_utils.MARKDOWN_EXTENSIONS:
        return render_template(
            'markdown_editor.html',
            content=content,
            filename=filename,
            file_path=(path or '').replace('\\', '/'),
            current_dir=current_dir,
            extension=ext_lower,
            ROOT_DIR=root_dir,
            os=os,
        )

    return render_template(
        'code_editor.html',
        content=content,
        filename=filename,
        file_path=(path or '').replace('\\', '/'),
        current_dir=current_dir,
        extension=ext_lower,
        ROOT_DIR=root_dir,
        os=os,
    )


@edit_bp.route('/save_file/<path:path>', methods=['POST'])
def save_file(path):
    root_dir, full_path, err = _resolve_file_path(path)
    if err:
        return jsonify({'success': False, 'message': err}), 403 if err == "非法路径" else 404
    if os.path.isdir(full_path):
        return jsonify({'success': False, 'message': '不能保存目录'}), 400

    data = request.get_json(silent=True) or {}
    content = data.get('content')
    if not isinstance(content, str):
        return jsonify({'success': False, 'message': 'content required'}), 400

    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        rel = os.path.relpath(full_path, root_dir).replace('\\', '/')
        return jsonify({'success': True, 'message': '保存成功', 'path': rel})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

