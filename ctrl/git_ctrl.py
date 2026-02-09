import os

from flask import Blueprint, Response, render_template, request

import config
from ctrl import api_error, api_ok
from lib.ai_client import AiClient
from lib import git_utils


git_bp = Blueprint('git', __name__)


@git_bp.route('/api/git/list')
def api_git_list():
    result = git_utils.get_all_git_repos_info()
    return api_ok({'repos': result})


@git_bp.route('/api/git/status')
def api_git_status():
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

    result = git_utils.get_git_status_detailed(full_path)
    if result:
        return api_ok(result)
    return api_ok({'is_repo': False})


@git_bp.route('/api/git/repo-status')
def api_git_repo_status():
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

    result = git_utils.get_git_repo_info(full_path, max_logs=50)
    if result:
        return api_ok(result)
    return api_ok({'is_repo': False})


@git_bp.route('/api/git/log')
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


@git_bp.route('/api/git/commit-list')
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


@git_bp.route('/api/git/push-changes', methods=['POST'])
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


@git_bp.route('/api/git/commit')
def api_git_commit():
    repo_id = request.args.get('repoId')
    repo_path_param = request.args.get('repoPath')
    commit_hash = request.args.get('hash')
    include = request.args.get('include', 'summary')

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


@git_bp.route('/api/git/commit/patch')
def api_git_commit_patch():
    repo_id = request.args.get('repoId')
    repo_path_param = request.args.get('repoPath')
    commit_hash = request.args.get('hash')

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


@git_bp.route('/git/commit')
def git_commit_page():
    repo_id = request.args.get('repoId')
    repo_path_param = request.args.get('repoPath')
    commit_hash = request.args.get('hash')

    if not commit_hash:
        return api_error('Missing hash', status=400)

    if repo_path_param:
        if repo_path_param.startswith(config.ROOT_DIR):
            repo_path = repo_path_param
        else:
            repo_path = os.path.normpath(os.path.join(config.ROOT_DIR, repo_path_param))
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


@git_bp.route('/commit/<commit_hash>')
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


@git_bp.route('/git/diff')
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
    return render_template(
        'git_diff.html',
        repo_name=repo_name,
        repo_path=repo_path,
        diff_text=diff_text or '',
    )

