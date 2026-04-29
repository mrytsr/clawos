import os
import re
from urllib.parse import unquote

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import config


edit_bp = Blueprint('edit', __name__)

_WIN_DRIVE_ABS_RE = re.compile(r'^[A-Za-z]:[\\/]')
_WIN_UNC_ABS_RE = re.compile(r'^(?:\\\\|//)[^\\/]+[\\/][^\\/]+')


def _get_root_dir():
    return os.path.normpath(config.ROOT_DIR)


def _normalize_absolute_path(path):
    raw_path = unquote(path or '').strip()
    if not raw_path:
        return None

    if os.name == 'nt':
        if _WIN_UNC_ABS_RE.match(raw_path):
            return os.path.normpath(raw_path.replace('/', '\\'))
        if _WIN_DRIVE_ABS_RE.match(raw_path):
            return os.path.normpath(raw_path.replace('/', '\\'))
        return None

    if raw_path.startswith('/'):
        return os.path.normpath(raw_path)
    return None


def _to_url_path(path):
    return os.path.normpath(path).replace('\\', '/')


def _resolve_file_path(path):
    full_path = _normalize_absolute_path(path)
    if not full_path:
        return None, "仅支持绝对路径"
    if not os.path.exists(full_path):
        return None, "文件不存在"
    return full_path, None


def _read_text_file(full_path):
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read(), 'utf-8'
    except UnicodeDecodeError:
        with open(full_path, 'r', encoding='gbk', errors='replace') as f:
            return f.read(), 'gbk'


@edit_bp.route('/edit')
def edit_file():
    path = request.args.get('path', '')
    full_path, err = _resolve_file_path(path)
    if err:
        return err, 400 if err == "仅支持绝对路径" else 404
    if os.path.isdir(full_path):
        root_dir = _get_root_dir()
        try:
            rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
            if os.path.commonpath([root_dir, full_path]) == root_dir:
                return redirect(url_for('browser.browse', path='' if rel_path == '.' else rel_path))
        except Exception:
            pass
        return "不能编辑目录", 400

    content, _enc = _read_text_file(full_path)
    _, ext = os.path.splitext(full_path)
    ext_lower = ext.lower()
    current_dir = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    file_path = _to_url_path(full_path)

    return render_template(
        'code_editor.html',
        content=content,
        filename=filename,
        file_path=file_path,
        display_path=full_path,
        current_dir=current_dir,
        extension=ext_lower,
        ROOT_DIR=_get_root_dir(),
        os=os,
    )


@edit_bp.route('/save_file', methods=['POST'])
def save_file():
    path = request.args.get('path', '')
    full_path, err = _resolve_file_path(path)
    if err:
        return jsonify({'success': False, 'message': err}), 400 if err == "仅支持绝对路径" else 404
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
        return jsonify({'success': True, 'message': '保存成功', 'path': _to_url_path(full_path)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@edit_bp.route('/code_editor/ai-generate', methods=['POST'])
def ai_generate_code():
    """AI 生成/修改代码."""
    import re
    import json

    data = request.json or {}
    prompt = data.get('prompt', '').strip()
    current_code = data.get('code', '').strip()
    filename = data.get('filename', '').strip()

    if not prompt:
        return jsonify({'success': False, 'message': '请输入 prompt'})

    # 获取文件扩展名用于确定语言
    ext = ''
    if filename:
        _, ext = os.path.splitext(filename)
        ext = ext.lower().lstrip('.')

    system_prompt = f"""你是一个专业程序员。根据用户需求生成或修改代码。

当前文件: {filename}
文件类型: {ext or 'text'}

当前代码:
```
{current_code}
```

要求:
1. 只返回代码本身，不要解释
2. 代码要语法正确，可直接使用
3. 如果是修改，保持代码风格一致
"""

    try:
        from lib.ai_client import AiClient
        client = AiClient('deepseek:deepseek-chat')
        response = client.chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])

        if isinstance(response, str):
            generated_code = response.strip()
        else:
            generated_code = (response.get('choices', [{}])[0].get('message', {}).get('content', '') if isinstance(response, dict) else '').strip()

        # 清理 markdown 代码块
        generated_code = re.sub(r'^```[a-zA-Z]*\n', '', generated_code)
        generated_code = re.sub(r'\n```$', '', generated_code)
        generated_code = generated_code.strip()

        return jsonify({'success': True, 'code': generated_code})

    except Exception as e:
        return jsonify({'success': False, 'message': f'AI 生成失败: {str(e)}'})
