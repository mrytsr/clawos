import re
import json
import mimetypes
import os
from urllib.parse import quote

import markdown
from flask import Blueprint, redirect, render_template, request, send_from_directory, url_for, jsonify

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


@file_bp.route('/yaml/editor')
def yaml_editor():
    """YAML/TOML/配置编辑器页面"""
    path = request.args.get('path', '')
    return render_template('yaml_editor.html', path=path)


@file_bp.route('/thumbnail/<path:path>')
def thumbnail(path):
    return serve_file(path)


@file_bp.route('/api/file/read')
def api_file_read():
    """读取文件内容（用于 URL 文件等）"""
    path = request.args.get('path', '')
    if not path:
        return {'success': False, 'error': {'message': '缺少 path 参数'}}
    
    root_dir = _get_root_dir()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return {'success': False, 'error': {'message': '非法路径'}}
    
    if not os.path.exists(full_path):
        return {'success': False, 'error': {'message': '文件不存在'}}
    
    if os.path.isdir(full_path):
        return {'success': False, 'error': {'message': '不能读取目录'}}
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {'success': True, 'data': {'content': content}}
    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}


@file_bp.route('/api/file/write', methods=['POST'])
def api_file_write():
    """写入文件内容（用于创建 URL 文件等）"""
    data = request.get_json(silent=True) or {}
    path = data.get('path', '').strip()
    content = data.get('content', '')
    
    if not path:
        return {'success': False, 'error': {'message': '缺少 path 参数'}}
    
    root_dir = _get_root_dir()
    full_path = os.path.normpath(os.path.join(root_dir, path))
    if not full_path.startswith(root_dir):
        return {'success': False, 'error': {'message': '非法路径'}}
    
    try:
        # 确保父目录存在
        parent_dir = os.path.dirname(full_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {'success': True, 'data': {'path': path}}
    except Exception as e:
        return {'success': False, 'error': {'message': str(e)}}



@file_bp.route('/api/file/email', methods=['POST'])
def send_file_email():
    """通过邮件发送文件"""
    from lib.email_utils import send_email_with_attachment
    from email.mime.text import MIMEText
    import os
    
    data = request.get_json(silent=True) or {}
    file_path = data.get('path', '')
    name = data.get('name', '')
    email = data.get('email', '')
    
    if not file_path or not email:
        return jsonify({'success': False, 'error': '参数不完整'})
    
    # 获取完整路径
    root_dir = config.ROOT_DIR
    full_path = os.path.join(root_dir, file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'error': '文件不存在'})
    
    if os.path.isdir(full_path):
        return jsonify({'success': False, 'error': '不支持文件夹'})
    
    # 发送邮件
    subject = f'文件: {name}'
    body = f'文件: {name}\n路径: {file_path}'
    
    try:
        send_email_with_attachment(email, subject, body, [full_path])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# 邮箱历史记录
EMAIL_HISTORY_DIR = os.path.expanduser('~/.local/clawos')
EMAIL_HISTORY_FILE = os.path.join(EMAIL_HISTORY_DIR, 'email_history.json')

def load_email_history():
    try:
        os.makedirs(EMAIL_HISTORY_DIR, exist_ok=True)
        if os.path.exists(EMAIL_HISTORY_FILE):
            with open(EMAIL_HISTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Email history error: {e}")
        pass
    return []

def save_email_history(emails):
    try:
        with open(EMAIL_HISTORY_FILE, 'w') as f:
            json.dump(emails, f, ensure_ascii=False)
    except Exception as e:
        print(f"Email history error: {e}")
        pass

@file_bp.route('/api/email/history', methods=['GET'])
def get_email_history():
    emails = load_email_history()
    return jsonify({'success': True, 'data': emails})

@file_bp.route('/api/email/history', methods=['POST'])
def add_email_history():
    data = request.json or {}
    email = data.get('email', '').strip()
    if not email or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        return jsonify({'success': False, 'error': '邮箱不能为空'})
    
    emails = load_email_history()
    if email in emails:
        emails.remove(email)
    emails.insert(0, email)
    emails = emails[:10]  # 保留最近10个
    save_email_history(emails)
    return jsonify({'success': True})

@file_bp.route('/api/email/history', methods=['DELETE'])
def delete_email_history():
    data = request.json or {}
    email = data.get('email', '').strip()
    emails = load_email_history()
    if email in emails:
        emails.remove(email)
        save_email_history(emails)
    return jsonify({'success': True})


# Email config
EMAIL_CONFIG_FILE = os.path.join(os.path.expanduser('~/.local/clawos'), 'email_config.json')

def load_email_config():
    try:
        if os.path.exists(EMAIL_CONFIG_FILE):
            with open(EMAIL_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'smtp_host': '', 'smtp_port': 465, 'smtp_ssl': 'ssl', 'smtp_user': '', 'smtp_pass': '', 'smtp_from': ''}

def save_email_config(config_data):
    try:
        os.makedirs(os.path.dirname(EMAIL_CONFIG_FILE), exist_ok=True)
        with open(EMAIL_CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
    except:
        pass

@file_bp.route('/email-config')
def email_config_page():
    return render_template('email_config.html')

@file_bp.route('/api/email/config', methods=['GET'])
def get_email_config():
    config = load_email_config()
    config['smtp_pass'] = ''  # Don't return password
    return jsonify({'success': True, 'data': config})

@file_bp.route('/api/email/config', methods=['POST'])
def set_email_config():
    data = request.json or {}
    save_email_config(data)
    return jsonify({'success': True})

@file_bp.route('/api/email/test', methods=['POST'])
def test_email():
    data = request.json or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'error': '请输入邮箱'})
    
    config = load_email_config()
    if not config.get('smtp_host') or not config.get('smtp_user'):
        return jsonify({'success': False, 'error': '请先配置SMTP'})
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText('这是一封来自 ClawOS 的测试邮件。', 'plain', 'utf-8')
        msg['Subject'] = 'ClawOS 测试邮件'
        msg['From'] = config.get('smtp_user')
        msg['To'] = email
        
        port = int(config.get('smtp_port', 465))
        if config.get('smtp_ssl') == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(config['smtp_host'], port, timeout=30)
        else:
            server = smtplib.SMTP(config['smtp_host'], port, timeout=30)
            if config.get('smtp_ssl') == 'tls':
                server.starttls()
        
        server.login(config['smtp_user'], config['smtp_pass'])
        server.sendmail(config['smtp_user'], [email], msg.as_string())
        server.quit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Alert Demo
@file_bp.route('/alert-demo')
def alert_demo_page():
    return render_template('alert_demo.html')

@file_bp.route('/swal-github')
def swal_github_demo():
    return render_template('swal_github.html')
def alert_demo_page():
    return render_template('alert_demo.html')
