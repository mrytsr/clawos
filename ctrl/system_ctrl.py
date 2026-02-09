import json
import html
import os
import re
import subprocess
from flask import Blueprint, Response, render_template, request, jsonify

import config
from lib.ai_client import AiClient

try:
    import psutil
except ImportError:
    psutil = None

from ctrl import api_error, api_ok

from ctrl.task_ctrl import create_task
from lib import (
    disk_utils,
    docker_utils,
    git_utils,
    network_utils,
    packages_utils,
    process_utils,
    systemd_utils,
)

OPENCLAW_CONFIG_PATH = os.path.expanduser('~/.openclaw/openclaw.json')


system_bp = Blueprint('system', __name__)


def _wrap(result, fail_status=400):
    if isinstance(result, dict) and result.get('success'):
        data = dict(result)
        data.pop('success', None)
        return api_ok(data)
    message = None
    if isinstance(result, dict):
        message = result.get('message')
    return api_error(message or 'Error', status=fail_status)


@system_bp.route('/api/process/list')
def api_process_list():
    """获取进程列表（适合手机展示）"""
    try:
        # 使用 ps 命令获取进程信息
        result = subprocess.run(
            ['ps', 'aux', '--sort=-%cpu'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        lines = result.stdout.strip().split('\n')[1:]  # 跳过表头
        processes = []
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 11:
                try:
                    # ps aux 输出格式: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                    proc = {
                        'pid': int(parts[1]),
                        'user': parts[0],
                        'cpu_percent': float(parts[2]),
                        'memory_percent': float(parts[3]),
                        'memory_rss': int(parts[5]) * 1024,  # KB -> Bytes
                        'elapsed': parts[9],
                        'command': parts[10] if len(parts) > 10 else parts[10],
                        'full_command': ' '.join(parts[10:]) if len(parts) > 10 else parts[10],
                    }
                    processes.append(proc)
                except (ValueError, IndexError):
                    continue
        
        # 计算内存总量和进程数
        memory_total = 0
        try:
            if psutil is None:
                raise ImportError()
            vm = psutil.virtual_memory()
            memory_total = vm.total
        except ImportError:
            # 估算：所有进程 RSS 之和 * 2
            total_rss = sum(p['memory_rss'] for p in processes)
            memory_total = total_rss * 2
        
        memory_used = sum(p['memory_rss'] for p in processes)
        memory_percent = round(memory_used / memory_total * 100, 1) if memory_total > 0 else 0
        
        # 获取 CPU 使用率
        cpu_percent = 0
        try:
            if psutil is None:
                raise ImportError()
            cpu_percent = psutil.cpu_percent()
        except ImportError:
            cpu_percent = sum(p['cpu_percent'] for p in processes[:20])
        
        stats = {
            'cpu_percent': cpu_percent,
            'memory_used': memory_used,
            'memory_total': memory_total,
            'memory_percent': memory_percent,
            'process_count': len(processes),
        }
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'processes': processes[:50]  # 限制50个
            }
        })
    except subprocess.TimeoutExpired:
        return api_error('获取进程信息超时', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/process/kill/<int:pid>', methods=['POST'])
def api_process_kill(pid):
    result = process_utils.kill_process(pid)
    return _wrap(result)


@system_bp.route('/api/process/ports/<int:pid>')
def api_process_ports(pid):
    result = process_utils.get_process_ports_detail(pid)
    return _wrap(result)


@system_bp.route('/api/system-packages/list')
def api_system_packages():
    result = packages_utils.list_system_packages()
    return _wrap(result)


@system_bp.route('/api/system-packages/uninstall', methods=['POST'])
def api_system_packages_uninstall():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.uninstall_system_package(
        data.get('name'),
        data.get('manager'),
    )
    return _wrap(result)


@system_bp.route('/api/pip/list')
def api_pip_list():
    result = packages_utils.list_pip_packages()
    return _wrap(result)


@system_bp.route('/api/pip/install', methods=['POST'])
def api_pip_install():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.install_pip_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/pip/uninstall', methods=['POST'])
def api_pip_uninstall():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.uninstall_pip_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/npm/list')
def api_npm_list():
    result = packages_utils.list_npm_packages()
    return _wrap(result)


@system_bp.route('/api/npm/install', methods=['POST'])
def api_npm_install():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.install_npm_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/npm/uninstall', methods=['POST'])
def api_npm_uninstall():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = packages_utils.uninstall_npm_package(data.get('package'))
    return _wrap(result)


@system_bp.route('/api/docker/images')
def api_docker_images():
    result = docker_utils.list_docker_images()
    return _wrap(result)


@system_bp.route('/api/docker/containers')
def api_docker_containers():
    result = docker_utils.list_docker_containers()
    return _wrap(result)


@system_bp.route('/api/docker/image/rm', methods=['POST'])
def api_docker_image_rm():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.remove_docker_image(data.get('id'))
    return _wrap(result)


@system_bp.route('/api/docker/container/rm', methods=['POST'])
def api_docker_container_rm():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.remove_docker_container(
        data.get('id'),
        data.get('force', False),
    )
    return _wrap(result)


@system_bp.route('/api/docker/container/stop', methods=['POST'])
def api_docker_container_stop():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.stop_docker_container(data.get('id'))
    return _wrap(result)


@system_bp.route('/api/docker/container/start', methods=['POST'])
def api_docker_container_start():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    result = docker_utils.start_docker_container(data.get('id'))
    return _wrap(result)


@system_bp.route('/api/systemd/list')
def api_systemd_list():
    result = systemd_utils.list_systemd_services()
    return _wrap(result)


@system_bp.route('/api/systemd/control', methods=['POST'])
def api_systemd_control():
    data = request.json
    if not isinstance(data, dict):
        return api_error('Invalid JSON', status=400)
    service = data.get('service')
    action = data.get('action')

    def _run():
        result = systemd_utils.control_systemd_service(service, action)
        if isinstance(result, dict) and result.get('success'):
            return
        message = None
        if isinstance(result, dict):
            message = result.get('message')
        raise RuntimeError(message or 'Error')

    task_id = create_task(_run, name=f'systemd:{action}:{service}')
    return api_ok({'taskId': task_id})


@system_bp.route('/api/disk/list')
def api_disk_list():
    result = disk_utils.list_disks()
    return _wrap(result)


@system_bp.route('/api/network/list')
def api_network_list():
    result = network_utils.list_network()
    return _wrap(result)


@system_bp.route('/api/git/list')
def api_git_list():
    result = git_utils.get_all_git_repos_info()
    return api_ok({'repos': result})


@system_bp.route('/api/git/status')
def api_git_status():
    """获取当前目录的Git状态"""
    path = request.args.get('path', '')
    
    # 解析绝对路径
    if path:
        root_dir = os.path.normpath(config.ROOT_DIR)
        candidate = os.path.normpath(path)
        if candidate.startswith(root_dir):
            full_path = candidate
        else:
            full_path = os.path.normpath(os.path.join(config.ROOT_DIR, path))
    else:
        full_path = config.ROOT_DIR
    
    # 安全检查
    if not full_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)
    
    result = git_utils.get_git_status_detailed(full_path)
    if result:
        return api_ok(result)
    else:
        return api_ok({'is_repo': False})


@system_bp.route('/api/git/repo-status')
def api_git_repo_status():
    """获取任意路径的仓库信息（状态+日志），用于Git管理抽屉"""
    path = request.args.get('path', '')
    
    # 解析绝对路径
    if path:
        root_dir = os.path.normpath(config.ROOT_DIR)
        candidate = os.path.normpath(path)
        if candidate.startswith(root_dir):
            full_path = candidate
        else:
            full_path = os.path.normpath(os.path.join(config.ROOT_DIR, path))
    else:
        full_path = config.ROOT_DIR
    
    # 安全检查
    if not full_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)
    
    result = git_utils.get_git_repo_info(full_path, max_logs=50)
    if result:
        return api_ok(result)
    else:
        return api_ok({'is_repo': False})


@system_bp.route('/api/git/log')
def api_git_log():
    path = request.args.get('path', '')

    if path:
        root_dir = os.path.normpath(config.ROOT_DIR)
        candidate = os.path.normpath(path)
        if candidate.startswith(root_dir):
            full_path = candidate
        else:
            full_path = os.path.normpath(os.path.join(config.ROOT_DIR, path))
    else:
        full_path = config.ROOT_DIR

    if not full_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)

    logs = git_utils.get_git_log_compact(full_path, max_count=50)
    if logs is None:
        return api_ok({'is_repo': False, 'logs': []})
    return api_ok({'is_repo': True, 'repoPath': full_path, 'logs': logs})


@system_bp.route('/api/git/commit-list')
def api_git_commit_list():
    path = request.args.get('path', '')
    max_count = request.args.get('max_count', 50)
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 20)

    if path:
        root_dir = os.path.normpath(config.ROOT_DIR)
        candidate = os.path.normpath(path)
        if candidate.startswith(root_dir):
            full_path = candidate
        else:
            full_path = os.path.normpath(os.path.join(config.ROOT_DIR, path))
    else:
        full_path = config.ROOT_DIR

    if not full_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)

    result = git_utils.get_git_log_compact_paged(
        full_path,
        max_count=max_count,
        page=page,
        per_page=per_page,
    )
    if result is None:
        return api_ok(
            {
                'is_repo': False,
                'repoPath': full_path,
                'commits': [],
                'pagination': {
                    'page': int(page) if str(page).isdigit() else 1,
                    'per_page': int(per_page) if str(per_page).isdigit() else 20,
                    'max_count': int(max_count) if str(max_count).isdigit() else 50,
                    'has_more': False,
                },
            }
        )

    return api_ok(
        {
            'is_repo': True,
            'repoPath': result.get('repo_path') or full_path,
            'commits': result.get('logs') or [],
            'pagination': {
                'page': result.get('page') or 1,
                'per_page': result.get('per_page') or 20,
                'max_count': result.get('max_count') or 50,
                'has_more': bool(result.get('has_more')),
            },
        }
    )


@system_bp.route('/api/git/push-changes', methods=['POST'])
def api_git_push_changes():
    payload = request.get_json(silent=True) or {}
    path = payload.get('path') or request.args.get('path', '')

    if path:
        root_dir = os.path.normpath(config.ROOT_DIR)
        candidate = os.path.normpath(path)
        if candidate.startswith(root_dir):
            full_path = candidate
        else:
            full_path = os.path.normpath(os.path.join(config.ROOT_DIR, path))
    else:
        full_path = config.ROOT_DIR

    if not full_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)

    porcelain = git_utils.get_git_status_porcelain(full_path)
    if porcelain is None:
        return api_error('Not a git repository', status=400)
    if not porcelain.strip():
        return api_ok({'status': 'clean'})

    stage_result = git_utils.git_stage_all(full_path)
    if not stage_result or stage_result.returncode != 0:
        err = (stage_result.stderr if stage_result else '') or ''
        return api_error(('git add failed: ' + err.strip())[:400], status=500)

    diff_text = git_utils.get_git_staged_diff_text(full_path, max_chars=20000) or ''
    if not diff_text.strip():
        return api_ok({'status': 'clean'})

    system_prompt = (
        '你是一个为 Git 生成 commit message 的助手。'
        '只输出一行中文提交说明，不要包含引号，不要换行，不要 Markdown。'
        '长度不超过 72 个字符。'
    )
    question = '根据下面的 git diff（已 stage），生成最合适的一行 commit message：\n\n' + diff_text

    commit_msg = None
    try:
        commit_msg = AiClient().ask(question=question, system_prompt=system_prompt)
    except Exception:
        commit_msg = None

    msg = str(commit_msg or '').strip()
    msg = msg.splitlines()[0].strip() if msg else ''
    if (msg.startswith('"') and msg.endswith('"')) or (msg.startswith("'") and msg.endswith("'")):
        msg = msg[1:-1].strip()
    if not msg:
        msg = '更新变更'
    if len(msg) > 72:
        msg = msg[:72].rstrip()

    commit_result = git_utils.git_commit(full_path, msg)
    if not commit_result:
        return api_error('git commit failed', status=500)
    if commit_result.returncode != 0:
        out = (commit_result.stdout or '') + '\n' + (commit_result.stderr or '')
        lowered = out.lower()
        if 'nothing to commit' in lowered or 'no changes' in lowered:
            return api_ok({'status': 'clean'})
        return api_error(('git commit failed: ' + out.strip())[:400], status=500)

    head_hash = ''
    try:
        head_result = git_utils._run_git(full_path, ['rev-parse', 'HEAD'], timeout=10)
        if head_result.returncode == 0:
            head_hash = (head_result.stdout or '').strip()
    except Exception:
        head_hash = ''

    push_result = git_utils.git_push_origin_master(full_path)
    if not push_result:
        return api_error('git push failed', status=500)
    if push_result.returncode != 0:
        out = (push_result.stdout or '') + '\n' + (push_result.stderr or '')
        return api_error(('git push failed: ' + out.strip())[:400], status=500)

    return api_ok({'pushed': True, 'commit_msg': msg, 'commit_hash': head_hash})


@system_bp.route('/api/git/commit')
def api_git_commit():
    # 支持repoId（兼容）或repoPath（新）
    repo_id = request.args.get('repoId')
    repo_path_param = request.args.get('repoPath')
    commit_hash = request.args.get('hash')
    include = request.args.get('include', 'summary')
    
    # 确定仓库路径
    if repo_path_param:
        # 使用repoPath参数
        if repo_path_param.startswith(config.ROOT_DIR):
            repo_path = repo_path_param
        else:
            repo_path = os.path.normpath(os.path.join(config.ROOT_DIR, repo_path_param))
    elif repo_id:
        # 使用repoId（兼容旧版）
        repo_path = git_utils.resolve_repo_path(repo_id)
    else:
        return api_error('Missing repoId or repoPath', status=400)
    
    if not repo_path:
        return api_error('Invalid repository', status=400)
    
    if not commit_hash:
        return api_error('Missing hash', status=400)

    log_text = git_utils.get_commit_log_text(repo_path, commit_hash)
    if not log_text:
        return api_error('Failed to get commit log', status=400)

    if include == 'summary':
        return api_ok({'repoPath': repo_path, 'hash': commit_hash, 'log': log_text})

    numstat = git_utils.get_commit_numstat(repo_path, commit_hash) or []
    diff_text = git_utils.get_commit_diff_text(repo_path, commit_hash) or ''
    return api_ok(
        {
            'repoPath': repo_path,
            'hash': commit_hash,
            'log': log_text,
            'numstat': numstat,
            'diff': diff_text,
        }
    )


@system_bp.route('/api/git/commit/patch')
def api_git_commit_patch():
    # 支持repoId（兼容）或repoPath（新）
    repo_id = request.args.get('repoId')
    repo_path_param = request.args.get('repoPath')
    commit_hash = request.args.get('hash')
    
    # 确定仓库路径
    if repo_path_param:
        if repo_path_param.startswith(config.ROOT_DIR):
            repo_path = repo_path_param
        else:
            repo_path = os.path.normpath(os.path.join(config.ROOT_DIR, repo_path_param))
    elif repo_id:
        repo_path = git_utils.resolve_repo_path(repo_id)
    else:
        return api_error('Missing repoId or repoPath', status=400)
    
    if not repo_path:
        return api_error('Invalid repository', status=400)
    
    if not commit_hash:
        return api_error('Missing hash', status=400)

    patch_text = git_utils.get_commit_patch_text(repo_path, commit_hash)
    if not patch_text:
        return api_error('Failed to generate patch', status=400)

    repo_name = os.path.basename(repo_path) or 'repo'
    filename = f'{repo_name}-{commit_hash[:12]}.patch'
    resp = Response(patch_text, mimetype='text/x-diff; charset=utf-8')
    resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


@system_bp.route('/git/commit')
def git_commit_page():
    # 支持repoId（兼容）或repoPath（新）
    repo_id = request.args.get('repoId')
    repo_path_param = request.args.get('repoPath')
    commit_hash = request.args.get('hash')
    
    if not commit_hash:
        return api_error('Missing hash', status=400)
    
    # 确定仓库路径
    if repo_path_param:
        if repo_path_param.startswith(config.ROOT_DIR):
            repo_path = repo_path_param
        else:
            repo_path = os.path.normpath(os.path.join(config.ROOT_DIR, repo_path_param))
        # 生成一个假的repo_id（用于patch URL）
        repo_id = f"path_{hash(repo_path) % 100000}"
    elif repo_id:
        repo_path = git_utils.resolve_repo_path(repo_id)
    else:
        return api_error('Missing repoId or repoPath', status=400)
    
    if not repo_path:
        return api_error('Invalid repository', status=400)

    repo_name = os.path.basename(repo_path) or repo_path
    log_text = git_utils.get_commit_log_text(repo_path, commit_hash) or ''
    numstat = git_utils.get_commit_numstat(repo_path, commit_hash) or []
    diff_text = git_utils.get_commit_diff_text(repo_path, commit_hash) or ''
    patch_url = f'/api/git/commit/patch?repoPath={repo_path}&hash={commit_hash}'

    return render_template(
        'git_commit.html',
        repo_name=repo_name,
        repo_id=repo_id,
        commit_hash=commit_hash,
        log_text=log_text,
        numstat=numstat,
        diff_text=diff_text,
        patch_url=patch_url,
    )


@system_bp.route('/commit/<commit_hash>')
def commit_page(commit_hash):
    repo_path_param = request.args.get('repoPath') or ''

    if repo_path_param:
        if repo_path_param.startswith(config.ROOT_DIR):
            repo_path = repo_path_param
        else:
            repo_path = os.path.normpath(os.path.join(config.ROOT_DIR, repo_path_param))
    else:
        repo_path = config.ROOT_DIR

    if not repo_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)

    repo_name = os.path.basename(repo_path) or repo_path
    log_text = git_utils.get_commit_log_text(repo_path, commit_hash) or ''
    if not log_text:
        return api_error('Failed to get commit log', status=400)

    numstat = git_utils.get_commit_numstat(repo_path, commit_hash) or []
    diff_text = git_utils.get_commit_diff_text(repo_path, commit_hash) or ''
    patch_url = f'/api/git/commit/patch?repoPath={repo_path}&hash={commit_hash}'
    repo_id = f"path_{hash(repo_path) % 100000}"

    return render_template(
        'git_commit.html',
        repo_name=repo_name,
        repo_id=repo_id,
        commit_hash=commit_hash,
        log_text=log_text,
        numstat=numstat,
        diff_text=diff_text,
        patch_url=patch_url,
    )


@system_bp.route('/git/diff')
def git_diff_page():
    repo_path_param = request.args.get('repoPath') or request.args.get('path') or ''

    if repo_path_param:
        if repo_path_param.startswith(config.ROOT_DIR):
            repo_path = repo_path_param
        else:
            repo_path = os.path.normpath(os.path.join(config.ROOT_DIR, repo_path_param))
    else:
        repo_path = config.ROOT_DIR

    if not repo_path.startswith(os.path.normpath(config.ROOT_DIR)):
        return api_error('Invalid path', status=403)

    diff_text = git_utils.get_git_worktree_diff_text(repo_path, max_chars=200000)
    if diff_text is None:
        return api_error('Not a git repository', status=400)

    repo_name = os.path.basename(repo_path) or repo_path
    safe = html.escape(diff_text or '')
    title = html.escape(f'{repo_name} - git diff')

    page = (
        '<!DOCTYPE html><html lang="zh-CN"><head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title}</title>'
        '<style>'
        'body{margin:0;padding:0;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;}'
        '.hd{position:sticky;top:0;z-index:10;background:#f6f8fa;border-bottom:1px solid #d0d7de;padding:10px 14px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;}'
        '.hd .t{font-size:14px;font-weight:600;color:#24292f;}'
        '.hd .p{font-size:12px;color:#57606a;word-break:break-all;}'
        '.bd{padding:12px 14px;}'
        'pre{margin:0;white-space:pre;overflow:auto;background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px;line-height:1.5;}'
        '</style></head><body>'
        f'<div class="hd"><div class="t">{title}</div><div class="p">{html.escape(repo_path)}</div></div>'
        f'<div class="bd"><pre>{safe}</pre></div>'
        '</body></html>'
    )

    return Response(page, mimetype='text/html; charset=utf-8')


@system_bp.route('/api/gpu/info')
def api_gpu_info():
    """获取NVIDIA GPU信息"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        output = result.stdout or result.stderr
        # 解析关键信息
        gpu_info = {}
        lines = output.split('\n')
        
        # 提取GPU名称
        for line in lines:
            if 'GeForce' in line or 'RTX' in line or 'NVIDIA' in line:
                gpu_info['name'] = line.strip()
                break
        
        # 提取显存、温度、功耗
        for line in lines:
            if 'MiB /' in line:
                # 提取显存使用情况
                match = re.search(r'(\d+)MiB / (\d+)MiB', line)
                if match:
                    used = int(match.group(1))
                    total = int(match.group(2))
                    gpu_info['memory_used'] = used
                    gpu_info['memory_total'] = total
                    gpu_info['memory_percent'] = round(used / total * 100, 1)
                break
        
        for line in lines:
            if 'W / ' in line:
                match = re.search(r'(\d+)W / (\d+)W', line)
                if match:
                    gpu_info['power_used'] = int(match.group(1))
                    gpu_info['power_total'] = int(match.group(2))
                break
        
        for line in lines:
            temp = line.strip()
            if temp and 'C' in temp:
                match = re.search(r'(\d+)C', temp)
                if match:
                    gpu_info['temperature'] = int(match.group(1))
                break
        
        for line in lines:
            if '%' in line and 'Default' in line:
                match = re.search(r'(\d+)%', line)
                if match:
                    gpu_info['utilization'] = int(match.group(1))
                break
        
        # 驱动版本
        for line in lines:
            if 'Driver Version' in line:
                match = re.search(r'Driver Version: ([\d.]+)', line)
                if match:
                    gpu_info['driver'] = match.group(1)
                break
        
        # CUDA版本
        for line in lines:
            if 'CUDA Version' in line:
                match = re.search(r'CUDA Version: ([\d.]+)', line)
                if match:
                    gpu_info['cuda'] = match.group(1)
                break
        
        return api_ok({'raw': output, 'parsed': gpu_info})
    except subprocess.TimeoutExpired:
        return api_error('nvidia-smi超时', status=500)
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/ollama/models')
def api_ollama_models():
    """获取Ollama模型列表"""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            # 尝试ollama list命令
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                models = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            size = parts[1] if len(parts) > 1 else '?'
                            models.append({
                                'name': model_name,
                                'size': size
                            })
                return api_ok({'models': models})
            return api_error('无法获取模型列表')
        
        data = json.loads(result.stdout)
        models = []
        for m in data.get('models', []):
            models.append({
                'name': m.get('name', ''),
                'size': m.get('size', 0),
                'modified': m.get('modified', '')
            })
        return api_ok({'models': models})
    except Exception as e:
        return api_error(str(e), status=500)


@system_bp.route('/api/openclaw/config')
def api_openclaw_config():
    """获取OpenClaw配置"""
    try:
        if not os.path.exists(OPENCLAW_CONFIG_PATH):
            return api_error('配置文件不存在')
        
        with open(OPENCLAW_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # 提取关键配置信息
        simplified = {
            'version': config.get('meta', {}).get('lastTouchedVersion', 'Unknown'),
            'models': {
                'count': 0,
                'list': []
            },
            'channels': {},
            'gateway': {},
            'auth': {}
        }
        
        # 模型列表
        providers = config.get('models', {}).get('providers', {})
        for provider_name, provider_data in providers.items():
            models = provider_data.get('models', [])
            for m in models:
                simplified['models']['list'].append({
                    'id': m.get('id', ''),
                    'name': m.get('name', m.get('id', '')),
                    'reasoning': m.get('reasoning', False)
                })
        simplified['models']['count'] = len(simplified['models']['list'])
        
        # 渠道
        channels = config.get('channels', {})
        for ch_name, ch_data in channels.items():
            simplified['channels'][ch_name] = {
                'enabled': ch_data.get('enabled', False)
            }
        
        # 网关
        gateway = config.get('gateway', {})
        simplified['gateway'] = {
            'port': gateway.get('port', 18789),
            'bind': gateway.get('bind', 'lan'),
            'tailscale': gateway.get('tailscale', {}).get('mode', 'off')
        }
        
        # 认证
        auth = config.get('auth', {}).get('profiles', {})
        simplified['auth'] = {
            'profiles': list(auth.keys())
        }
        
        return api_ok(simplified)
    except json.JSONDecodeError:
        return api_error('配置文件解析失败', status=500)
    except Exception as e:
        return api_error(str(e), status=500)
