import os
import shutil
import subprocess
import tarfile
import zipfile
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

import config
from ctrl.task_ctrl import create_task, update_task
from lib import file_utils, git_utils, json_utils, path_utils


browser_bp = Blueprint('browser', __name__)

PIN_FILE = os.path.join(config.SCRIPT_DIR, 'data', 'pin.json')


def _get_paths():
    root_dir = os.path.normpath(config.ROOT_DIR)
    trash_dir = os.path.normpath(config.TRASH_DIR)
    return root_dir, trash_dir


def _resolve_safe_file(path):
    root_dir, _trash_dir = _get_paths()
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


def _resolve_safe_dir(path, ensure_exists=False):
    root_dir, _trash_dir = _get_paths()
    p = (path or '').lstrip('/\\').replace('\\', '/')
    full_path = os.path.normpath(os.path.join(root_dir, p))
    try:
        if os.path.commonpath([root_dir, full_path]) != root_dir:
            return None, None, "非法路径"
    except Exception:
        return None, None, "非法路径"
    if ensure_exists:
        os.makedirs(full_path, exist_ok=True)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return None, None, "目录不存在"
    return root_dir, full_path, None


def _normalize_pin_dir(dir_path):
    p = (dir_path or '').strip()
    p = p.lstrip('/\\').replace('\\', '/')
    p = p.strip('/')
    if p in {'.', '/'}:
        return ''
    return p


def _load_pin_store():
    data = json_utils.load_json(PIN_FILE, default={'pins': []})
    pins = data.get('pins') if isinstance(data, dict) else None
    if not isinstance(pins, list):
        pins = []
    normalized = []
    for it in pins:
        if not isinstance(it, dict):
            continue
        d = _normalize_pin_dir(it.get('dir'))
        n = str(it.get('name') or '').strip()
        t = it.get('pinned_at')
        if not n or any(sep in n for sep in ['/', '\\']) or '..' in n:
            continue
        try:
            t_int = int(t)
        except Exception:
            continue
        normalized.append({'dir': d, 'name': n, 'pinned_at': t_int})
    return {'pins': normalized}


def _save_pin_store(store):
    pins = store.get('pins') if isinstance(store, dict) else None
    if not isinstance(pins, list):
        pins = []
    json_utils.save_json(PIN_FILE, {'pins': pins})


def _pin_dir_from_full_path(root_dir, full_path):
    try:
        rel = os.path.relpath(full_path, root_dir).replace('\\', '/')
    except Exception:
        rel = ''
    if rel == '.':
        rel = ''
    return _normalize_pin_dir(rel)


def _prune_pins_for_deleted_item(root_dir, full_path, is_dir):
    try:
        root_dir = os.path.normpath(root_dir)
        full_path = os.path.normpath(full_path)

        item_name = os.path.basename(full_path)
        parent_dir = os.path.dirname(full_path)

        parent_pin_dir = _pin_dir_from_full_path(root_dir, parent_dir)
        deleted_dir = _pin_dir_from_full_path(root_dir, full_path) if is_dir else ''

        store = _load_pin_store()
        pins = store.get('pins') if isinstance(store, dict) else None
        if not isinstance(pins, list) or not pins:
            return

        changed = False
        keep = []
        for it in pins:
            if not isinstance(it, dict):
                changed = True
                continue
            d = _normalize_pin_dir(it.get('dir'))
            n = str(it.get('name') or '').strip()
            if d == parent_pin_dir and n == item_name:
                changed = True
                continue
            if is_dir and deleted_dir:
                if d == deleted_dir or d.startswith(deleted_dir + '/'):
                    changed = True
                    continue
            keep.append(it)

        if changed:
            store['pins'] = keep
            _save_pin_store(store)
    except Exception:
        return


@browser_bp.route('/')
@browser_bp.route('/browse/')
@browser_bp.route('/browse/<path:path>')
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
    item_names = set()
    for it in items:
        if isinstance(it, dict) and it.get('name'):
            item_names.add(str(it.get('name')))

    rel_dir = path_utils.get_relative_path(current_dir, root_dir)
    pin_dir = _normalize_pin_dir(rel_dir)
    store = _load_pin_store()
    pins_all = store.get('pins', []) if isinstance(store, dict) else []
    initial_pins = []
    for it in pins_all:
        if not isinstance(it, dict):
            continue
        if it.get('dir') != pin_dir:
            continue
        name = str(it.get('name') or '').strip()
        if not name or name not in item_names:
            continue
        try:
            t = int(it.get('pinned_at') or 0)
        except Exception:
            t = 0
        initial_pins.append({'name': name, 'pinned_at': t})
    initial_pins.sort(key=lambda x: int(x.get('pinned_at') or 0), reverse=True)
    initial_git_status = None
    try:
        initial_git_status = git_utils.get_git_status_detailed(current_dir)
    except Exception:
        initial_git_status = None

    breadcrumbs = path_utils.get_breadcrumbs(current_dir, root_dir)
    return render_template(
        'index.html',
        items=items,
        current_dir=current_dir,
        breadcrumbs=breadcrumbs,
        initial_pin_dir=pin_dir,
        initial_pins=initial_pins,
        initial_git_status=initial_git_status,
        message=request.args.get('message'),
        msg_type=request.args.get('msg_type', 'success'),
        ROOT_DIR=root_dir,
        os=os,
    )


@browser_bp.route('/api/pin/list')
def api_pin_list():
    dir_rel = _normalize_pin_dir(request.args.get('dir', ''))
    _root_dir, full_dir, err = _resolve_safe_dir(dir_rel, ensure_exists=False)
    if err:
        return jsonify({'success': False, 'error': {'message': err}}), 400

    store = _load_pin_store()
    pins = store['pins']
    filtered = []
    changed = False
    for it in pins:
        if it.get('dir') != dir_rel:
            continue
        name = it.get('name')
        if not name:
            continue
        full_item = os.path.normpath(os.path.join(full_dir, name))
        if not full_item.startswith(os.path.normpath(full_dir)):
            changed = True
            continue
        if not os.path.exists(full_item):
            changed = True
            continue
        filtered.append({'name': name, 'pinned_at': int(it.get('pinned_at') or 0)})

    filtered.sort(key=lambda x: int(x.get('pinned_at') or 0), reverse=True)
    if changed:
        keep = []
        for it in pins:
            if it.get('dir') != dir_rel:
                keep.append(it)
                continue
            n = it.get('name')
            if not n:
                continue
            full_item = os.path.normpath(os.path.join(full_dir, n))
            if not full_item.startswith(os.path.normpath(full_dir)):
                continue
            if not os.path.exists(full_item):
                continue
            keep.append(it)
        store['pins'] = keep
        _save_pin_store(store)

    return jsonify({'success': True, 'data': {'dir': dir_rel, 'pins': filtered}})


@browser_bp.route('/api/pin/toggle', methods=['POST'])
def api_pin_toggle():
    payload = request.get_json(silent=True) or {}
    dir_rel = _normalize_pin_dir(payload.get('dir') or request.args.get('dir', ''))
    name = str(payload.get('name') or request.args.get('name', '')).strip()

    if not name:
        return jsonify({'success': False, 'error': {'message': '缺少名称'}}), 400
    if any(sep in name for sep in ['/', '\\']) or '..' in name:
        return jsonify({'success': False, 'error': {'message': '非法名称'}}), 400

    _root_dir, full_dir, err = _resolve_safe_dir(dir_rel, ensure_exists=False)
    if err:
        return jsonify({'success': False, 'error': {'message': err}}), 400

    full_item = os.path.normpath(os.path.join(full_dir, name))
    if not full_item.startswith(os.path.normpath(full_dir)):
        return jsonify({'success': False, 'error': {'message': '非法路径'}}), 403
    if not os.path.exists(full_item):
        return jsonify({'success': False, 'error': {'message': '文件不存在'}}), 404

    store = _load_pin_store()
    pins = store['pins']
    exists = False
    next_pins = []
    for it in pins:
        if it.get('dir') == dir_rel and it.get('name') == name:
            exists = True
            continue
        next_pins.append(it)

    pinned = False
    pinned_at = None
    if not exists:
        pinned = True
        pinned_at = int(datetime.now().timestamp() * 1000)
        next_pins.append({'dir': dir_rel, 'name': name, 'pinned_at': pinned_at})

    store['pins'] = next_pins
    _save_pin_store(store)

    current = [it for it in next_pins if it.get('dir') == dir_rel]
    current.sort(key=lambda x: int(x.get('pinned_at') or 0), reverse=True)
    resp_pins = [
        {'name': it.get('name'), 'pinned_at': int(it.get('pinned_at') or 0)}
        for it in current
        if it.get('name')
    ]
    return jsonify(
        {
            'success': True,
            'data': {
                'dir': dir_rel,
                'name': name,
                'pinned': pinned,
                'pinned_at': pinned_at,
                'pins': resp_pins,
            },
        }
    )


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


@browser_bp.route('/api/archive/list/<path:path>')
def api_archive_list(path):
    _root_dir, full_path, err = _resolve_safe_file(path)
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
                    items.append(
                        {
                            'path': inner,
                            'is_dir': False,
                            'size': int(info.file_size or 0),
                            'size_human': path_utils.format_size(int(info.file_size or 0)),
                        }
                    )
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
                    items.append(
                        {
                            'path': inner,
                            'is_dir': False,
                            'size': size,
                            'size_human': path_utils.format_size(size),
                        }
                    )
            for d in dirs:
                items.append({'path': d + '/', 'is_dir': True, 'size': 0, 'size_human': ''})
        else:
            seven = shutil.which('7z') or shutil.which('7za') or shutil.which('7zr')
            if not seven:
                return (
                    jsonify({'success': False, 'error': {'message': '缺少 7z 命令，无法预览该压缩包'}}),
                    400,
                )
            proc = subprocess.run([seven, 'l', '-slt', full_path], capture_output=True, text=True, timeout=30)
            if proc.returncode != 0:
                return (
                    jsonify(
                        {'success': False, 'error': {'message': (proc.stderr or proc.stdout or '列出失败').strip()}}
                    ),
                    400,
                )
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
                items.append(
                    {
                        'path': inner,
                        'is_dir': bool(is_dir),
                        'size': int(size or 0),
                        'size_human': '' if is_dir else path_utils.format_size(int(size or 0)),
                    }
                )

        items.sort(key=lambda x: (not x.get('is_dir', False), x.get('path', '').lower()))
        return jsonify({'success': True, 'data': {'items': items}})
    except Exception as e:
        return jsonify({'success': False, 'error': {'message': str(e)}}), 500


@browser_bp.route('/api/archive/extract/<path:path>', methods=['POST'])
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


@browser_bp.route('/api/archive/create', methods=['POST'])
def api_archive_create():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({'success': False, 'error': {'message': 'Invalid JSON'}}), 400

    paths = payload.get('paths') or []
    if not isinstance(paths, list) or not paths:
        return jsonify({'success': False, 'error': {'message': 'paths required'}}), 400

    fmt = (payload.get('format') or 'zip').strip().lower()
    if fmt not in {'zip', 'tar.gz'}:
        return jsonify({'success': False, 'error': {'message': '不支持的格式'}}), 400

    output_dir = (payload.get('output_dir') or '').strip()
    root_dir, out_dir_full, err = _resolve_safe_dir(output_dir, ensure_exists=False)
    if err:
        return jsonify({'success': False, 'error': {'message': err}}), 400

    archive_name = (payload.get('name') or '').strip()
    if not archive_name:
        archive_name = '新建压缩包.zip' if fmt == 'zip' else '新建压缩包.tar.gz'
    archive_name = os.path.basename(archive_name)
    if fmt == 'zip' and not archive_name.lower().endswith('.zip'):
        archive_name = archive_name + '.zip'
    if fmt == 'tar.gz' and not archive_name.lower().endswith('.tar.gz'):
        if archive_name.lower().endswith('.tar'):
            archive_name = archive_name + '.gz'
        else:
            archive_name = archive_name + '.tar.gz'

    root_dir = os.path.normpath(root_dir)
    output_full = os.path.normpath(os.path.join(out_dir_full, archive_name))
    try:
        if os.path.commonpath([root_dir, output_full]) != root_dir:
            return jsonify({'success': False, 'error': {'message': '非法目标文件'}}), 400
    except Exception:
        return jsonify({'success': False, 'error': {'message': '非法目标文件'}}), 400

    if os.path.exists(output_full):
        base = archive_name
        ext = ''
        if fmt == 'tar.gz':
            base = archive_name[:-7]
            ext = '.tar.gz'
        else:
            base, ext = os.path.splitext(archive_name)
        counter = 1
        while True:
            cand = os.path.join(out_dir_full, f'{base}({counter}){ext}')
            if not os.path.exists(cand):
                output_full = cand
                break
            counter += 1

    resolved = []
    for p in paths:
        if not isinstance(p, str) or not p.strip():
            continue
        rel = p.strip().lstrip('/\\').replace('\\', '/')
        full = os.path.normpath(os.path.join(root_dir, rel))
        try:
            if os.path.commonpath([root_dir, full]) != root_dir:
                continue
        except Exception:
            continue
        if not os.path.exists(full):
            continue
        resolved.append((rel, full))
    if not resolved:
        return jsonify({'success': False, 'error': {'message': '未找到可压缩项'}}), 400

    def _build_plan():
        entries = []
        seen = set()
        file_count = 0
        for _rel, full in resolved:
            top = os.path.basename(full.rstrip('/\\'))
            if not top:
                continue
            if os.path.isdir(full):
                for root, dirs, files in os.walk(full):
                    dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
                    for d in dirs:
                        arc = os.path.join(top, os.path.relpath(os.path.join(root, d), full)).replace('\\', '/').rstrip('/') + '/'
                        if arc not in seen:
                            seen.add(arc)
                            entries.append(('dir', os.path.join(root, d), arc))
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.path.islink(fp):
                            continue
                        arc = os.path.join(top, os.path.relpath(fp, full)).replace('\\', '/')
                        if arc not in seen:
                            seen.add(arc)
                            entries.append(('file', fp, arc))
                            file_count += 1
                if file_count == 0:
                    arc = top.rstrip('/') + '/'
                    if arc not in seen:
                        seen.add(arc)
                        entries.append(('dir', full, arc))
            else:
                arc = top
                if arc not in seen:
                    seen.add(arc)
                    entries.append(('file', full, arc))
                    file_count += 1
        return entries, max(file_count, 1)

    def _run(task_id):
        entries, total = _build_plan()
        update_task(task_id, status='pending', progress=0.0, message='准备中…')

        done = 0
        if fmt == 'zip':
            zf = None
            try:
                zf = zipfile.ZipFile(output_full, 'w', compression=zipfile.ZIP_DEFLATED)
                for kind, fp, arc in entries:
                    if kind == 'dir':
                        arc_dir = (arc or '').replace('\\', '/').rstrip('/') + '/'
                        if arc_dir:
                            try:
                                zf.writestr(arc_dir, b'')
                            except Exception:
                                pass
                        continue
                    zf.write(fp, arcname=arc)
                    done += 1
                    update_task(task_id, progress=(done * 100.0 / total), message=f'压缩中… {done}/{total}')
            finally:
                if zf:
                    zf.close()
        else:
            tf = None
            try:
                tf = tarfile.open(output_full, 'w:gz')
                for kind, fp, arc in entries:
                    if kind == 'dir':
                        tf.add(fp, arcname=(arc or '').replace('\\', '/').rstrip('/') + '/', recursive=False)
                        continue
                    if os.path.isdir(fp):
                        tf.add(fp, arcname=arc.rstrip('/'), recursive=False)
                        continue
                    tf.add(fp, arcname=arc, recursive=False)
                    done += 1
                    update_task(task_id, progress=(done * 100.0 / total), message=f'压缩中… {done}/{total}')
            finally:
                if tf:
                    tf.close()

    task_id = create_task(_run, name=f'archive:create:{fmt}')
    rel_out = os.path.relpath(output_full, root_dir).replace('\\', '/')
    return jsonify({'success': True, 'data': {'taskId': task_id, 'output': rel_out}})


@browser_bp.route('/api/upload', methods=['POST'])
def api_upload_file():
    root_dir, _trash_dir = _get_paths()

    f = request.files.get('file')
    if not f:
        return jsonify({'success': False, 'error': {'message': 'file required'}}), 400

    target_dir = (request.form.get('target_dir') or '').strip().lstrip('/\\').replace('\\', '/')
    _root, target_full, err = _resolve_safe_dir(target_dir, ensure_exists=True)
    if err:
        return jsonify({'success': False, 'error': {'message': err}}), 400

    desired = (request.form.get('filename') or f.filename or '').strip()
    desired = os.path.basename(desired)
    if not desired:
        return jsonify({'success': False, 'error': {'message': 'filename required'}}), 400

    out_full = os.path.normpath(os.path.join(target_full, desired))
    try:
        if os.path.commonpath([root_dir, out_full]) != root_dir:
            return jsonify({'success': False, 'error': {'message': '非法目标文件'}}), 400
    except Exception:
        return jsonify({'success': False, 'error': {'message': '非法目标文件'}}), 400

    if os.path.exists(out_full):
        base, ext = os.path.splitext(desired)
        counter = 1
        while True:
            cand = os.path.join(target_full, f'{base}({counter}){ext}')
            if not os.path.exists(cand):
                out_full = cand
                desired = os.path.basename(out_full)
                break
            counter += 1

    try:
        f.save(out_full)
    except Exception as e:
        return jsonify({'success': False, 'error': {'message': str(e)}}), 500

    rel_out = os.path.relpath(out_full, root_dir).replace('\\', '/')
    return jsonify({'success': True, 'data': {'path': rel_out, 'filename': desired}})


@browser_bp.route('/upload/', methods=['POST'])
@browser_bp.route('/upload/<path:path>', methods=['POST'])
def upload_file(path=''):
    root_dir, _trash_dir = _get_paths()
    if 'file' not in request.files:
        return redirect(
            url_for(
                'browser.browse',
                path=path,
                message='没有选择文件',
                msg_type='error',
            )
        )
    file = request.files['file']
    if file.filename == '':
        return redirect(
            url_for(
                'browser.browse',
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
                'browser.browse',
                path=path,
                message='文件上传成功',
                msg_type='success',
            )
        )
    return redirect(url_for('browser.browse', path=path))


@browser_bp.route('/delete/<path:path>', methods=['DELETE'])
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
        is_dir = os.path.isdir(full_path)
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
        _prune_pins_for_deleted_item(root_dir, full_path, is_dir)
        return jsonify({'success': True, 'message': '已移到回收站'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@browser_bp.route('/rename/<path:path>', methods=['POST'])
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
        new_path = os.path.normpath(os.path.join(os.path.dirname(full_path), new_name))
        if not new_path.startswith(root_dir):
            return jsonify({'success': False, 'message': '非法路径'})
        os.rename(full_path, new_path)
        return jsonify({'success': True, 'message': '重命名成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@browser_bp.route('/move/<path:path>', methods=['POST'])
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


@browser_bp.route('/clone/<path:path>', methods=['POST'])
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


@browser_bp.route('/mkdir', methods=['POST'])
@browser_bp.route('/mkdir/<path:parent>', methods=['POST'])
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


@browser_bp.route('/touch', methods=['POST'])
@browser_bp.route('/touch/<path:parent>', methods=['POST'])
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


@browser_bp.route('/trash')
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
        items.append({'name': name, 'path': path, 'deleted_at': deleted_at, 'is_dir': os.path.isdir(path)})
    items.sort(key=lambda x: x['name'], reverse=True)
    return render_template("trash.html", items=items)


@browser_bp.route('/trash/clear', methods=['POST'])
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


@browser_bp.route('/trash/restore/<name>', methods=['POST'])
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

