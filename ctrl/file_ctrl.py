import mimetypes
import os
from urllib.parse import quote

import markdown
from flask import Blueprint, redirect, render_template, request, send_from_directory, url_for

import config
from lib import file_utils


file_bp = Blueprint('file', __name__)


def _get_root_dir():
    return os.path.normpath(config.ROOT_DIR)


@file_bp.route('/view/<path:path>')
def view_file(path):
    root_dir = _get_root_dir()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return "非法路径", 403
    if not os.path.exists(full_path):
        return "文件不存在", 404
    if os.path.isdir(full_path):
        return redirect(url_for('browser.browse', path=path))

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
        rendered_html = markdown.markdown(
            raw_markdown or '',
            extensions=['fenced_code', 'tables'],
            output_format='html5',
        )
        return render_template(
            'markdown.html',
            raw_markdown=raw_markdown,
            rendered_html=rendered_html,
            filename=os.path.basename(full_path),
            file_path=path,
            current_dir=os.path.dirname(path),
        )
    if mime_type and (mime_type.startswith('image') or ext_lower in file_utils.IMAGE_EXTENSIONS):
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


@file_bp.route('/download/<path:path>')
def download_file(path):
    root_dir = _get_root_dir()
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
    root_dir = _get_root_dir()
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


@file_bp.route('/json/editor')
def json_editor():
    """JSON编辑器页面"""
    path = request.args.get('path', '')
    return render_template('json_editor.html', path=path)


@file_bp.route('/thumbnail/<path:path>')
def thumbnail(path):
    return serve_file(path)

