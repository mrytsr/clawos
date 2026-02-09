import os
import subprocess
import time


GIT_REPOS = [
    '/home/tjx/.openclaw/workspace/clawos',
    '/home/tjx/.openclaw/workspace/xiandan',
    '/home/tjx/.openclaw/workspace',
]

_CACHE_TTL_SEC = 30
_commit_cache = {}


def _is_git_repo(repo_path):
    return os.path.exists(os.path.join(repo_path, '.git'))


def _run_git(repo_path, args, timeout=10):
    cmd = ['git', *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        cwd=repo_path,
        timeout=timeout,
        env={**os.environ, 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'},
    )


def get_git_log(repo_path, max_count=50):
    try:
        if not _is_git_repo(repo_path):
            return None

        fmt = '%H%x09%ad%x09%s'
        cmd = [
            'log',
            '-n',
            str(max_count),
            '--date=format:%Y-%m-%d %H:%M:%S',
            f'--pretty=format:{fmt}',
        ]
        result = _run_git(repo_path, cmd, timeout=10)
        if result.returncode != 0:
            return None

        logs = []
        for line in result.stdout.splitlines():
            raw = line.strip('\n').strip('\r')
            if not raw:
                continue
            parts = raw.split('\t', 2)
            if len(parts) < 2:
                continue
            commit_hash = parts[0].strip()
            committed_at = parts[1].strip()
            subject = parts[2].strip() if len(parts) > 2 else ''
            logs.append(
                {
                    'hash': commit_hash,
                    'committed_at': committed_at,
                    'subject': subject,
                }
            )
        return logs
    except Exception as e:
        print(f"Error getting git log from {repo_path}: {e}")
        return None


def get_git_status(repo_path):
    """获取仓库的 git 状态"""
    try:
        if not _is_git_repo(repo_path):
            return None

        branch_result = _run_git(
            repo_path,
            ['rev-parse', '--abbrev-ref', 'HEAD'],
            timeout=5,
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'

        remote_result = _run_git(repo_path, ['branch', '-r'], timeout=5)
        remote_count = len([b for b in remote_result.stdout.strip().split('\n') if b.strip()])

        return {
            'branch': branch,
            'remote_count': remote_count
        }
    except Exception as e:
        print(f"Error getting git status from {repo_path}: {e}")
        return None


def get_git_status_detailed(repo_path):
    """获取仓库的详细git状态 (用于文件列表页面)"""
    try:
        if not _is_git_repo(repo_path):
            return None
        
        # 获取分支
        branch_result = _run_git(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'], timeout=5)
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'
        
        # 获取状态统计
        status_result = _run_git(repo_path, ['status', '--porcelain'], timeout=10)
        porcelain = status_result.stdout.strip() if status_result.returncode == 0 else ''
        
        # 统计各类文件
        added = 0      # 新增 A
        modified = 0  # 修改 M
        deleted = 0    # 删除 D
        untracked = 0 # 未追踪 ?
        
        if porcelain:
            for line in porcelain.splitlines():
                line = line.strip()
                if not line:
                    continue
                status = line[:1] if len(line) >= 1 else ''
                # 判断状态类型
                if status == 'A' or status == '?' or status == ' ':
                    # 未追踪或新增
                    if line.startswith('??'):
                        untracked += 1
                    elif line.startswith('A '):
                        added += 1
                    elif line.startswith(' M') or line.startswith('M '):
                        modified += 1
                    elif line.startswith(' D') or line.startswith('D '):
                        deleted += 1
                elif status == 'M':
                    modified += 1
                elif status == 'D':
                    deleted += 1
                elif status == 'A':
                    added += 1
        
        # 简化计数逻辑（porcelain格式）
        added = len([l for l in porcelain.splitlines() if l.startswith('A ') or l.startswith('A' + chr(0))])
        modified = len([l for l in porcelain.splitlines() if l.startswith(' M') or l.startswith('M ')])
        deleted = len([l for l in porcelain.splitlines() if l.startswith(' D') or l.startswith('D ')])
        untracked = len([l for l in porcelain.splitlines() if l.startswith('??')])
        
        # 是否有改动
        has_changes = bool(porcelain)
        
        # 获取当前commit hash
        hash_result = _run_git(repo_path, ['rev-parse', 'HEAD'], timeout=5)
        commit_hash = hash_result.stdout.strip()[:8] if hash_result.returncode == 0 else ''
        
        return {
            'is_repo': True,
            'branch': branch,
            'commit': commit_hash,
            'added': added,
            'modified': modified,
            'deleted': deleted,
            'untracked': untracked,
            'has_changes': has_changes,
            'total_changes': added + modified + deleted + untracked
        }
    except Exception as e:
        print(f"Error getting detailed git status from {repo_path}: {e}")
        return None


def get_git_repo_info(repo_path, max_logs=50):
    """获取仓库完整信息（状态+日志），用于Git管理抽屉"""
    try:
        if not _is_git_repo(repo_path):
            return None
        
        import os
        name = os.path.basename(repo_path)
        
        # 获取分支
        branch_result = _run_git(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'], timeout=5)
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'
        
        # 获取commit hash
        hash_result = _run_git(repo_path, ['rev-parse', 'HEAD'], timeout=5)
        commit_hash = hash_result.stdout.strip()[:8] if hash_result.returncode == 0 else ''
        
        # 获取状态统计
        status_result = _run_git(repo_path, ['status', '--porcelain'], timeout=10)
        porcelain = status_result.stdout.strip() if status_result.returncode == 0 else ''
        
        # 统计
        added = modified = deleted = untracked = 0
        if porcelain:
            for line in porcelain.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith('??'):
                    untracked += 1
                elif line.startswith('A '):
                    added += 1
                elif line.startswith(' M') or line.startswith('M '):
                    modified += 1
                elif line.startswith(' D') or line.startswith('D '):
                    deleted += 1
        
        has_changes = bool(porcelain)
        
        # 获取日志
        fmt = '%H%x09%ad%x09%s'
        log_cmd = [
            'log',
            '-n', str(max_logs),
            '--date=format:%Y-%m-%d %H:%M:%S',
            f'--pretty=format:{fmt}',
        ]
        log_result = _run_git(repo_path, log_cmd, timeout=10)
        logs = []
        if log_result.returncode == 0:
            for line in log_result.stdout.splitlines():
                raw = line.strip('\n').strip('\r')
                if not raw:
                    continue
                parts = raw.split('\t', 2)
                if len(parts) >= 2:
                    logs.append({
                        'hash': parts[0].strip(),
                        'committed_at': parts[1].strip(),
                        'subject': parts[2].strip() if len(parts) > 2 else ''
                    })
        
        return {
            'is_repo': True,
            'path': repo_path,
            'name': name,
            'branch': branch,
            'commit': commit_hash,
            'status': {
                'has_changes': has_changes,
                'untracked': untracked,
                'added': added,
                'modified': modified,
                'deleted': deleted
            },
            'logs': logs
        }
    except Exception as e:
        print(f"Error getting git repo info from {repo_path}: {e}")
        return None


def resolve_repo_path(repo_id):
    try:
        idx = int(repo_id)
    except Exception:
        return None
    if idx < 0 or idx >= len(GIT_REPOS):
        return None
    return GIT_REPOS[idx]


def get_commit_log_text(repo_path, commit_hash):
    if not _is_git_repo(repo_path):
        return None
    cache_key = (repo_path, commit_hash, 'log')
    cached = _commit_cache.get(cache_key)
    if cached and (time.time() - cached['ts'] <= _CACHE_TTL_SEC):
        return cached['value']
    result = _run_git(
        repo_path,
        [
            'log',
            '-1',
            '--pretty=fuller',
            '--date=format:%Y-%m-%d %H:%M:%S',
            commit_hash,
        ],
        timeout=10,
    )
    if result.returncode != 0:
        return None
    _commit_cache[cache_key] = {'ts': time.time(), 'value': result.stdout}
    return result.stdout


def get_commit_numstat(repo_path, commit_hash):
    if not _is_git_repo(repo_path):
        return None
    cache_key = (repo_path, commit_hash, 'numstat')
    cached = _commit_cache.get(cache_key)
    if cached and (time.time() - cached['ts'] <= _CACHE_TTL_SEC):
        return cached['value']
    result = _run_git(
        repo_path,
        [
            'show',
            '-1',
            '--numstat',
            '--format=',
            commit_hash,
        ],
        timeout=10,
    )
    if result.returncode != 0:
        return None
    rows = []
    for line in result.stdout.splitlines():
        raw = line.strip('\n').strip('\r')
        if not raw:
            continue
        parts = raw.split('\t')
        if len(parts) < 3:
            continue
        added_raw, deleted_raw, path = parts[0], parts[1], parts[2]
        is_binary = added_raw == '-' or deleted_raw == '-'
        added = int(added_raw) if added_raw.isdigit() else 0
        deleted = int(deleted_raw) if deleted_raw.isdigit() else 0
        modified = min(added, deleted) if not is_binary else 0
        added_only = max(0, added - modified)
        deleted_only = max(0, deleted - modified)
        rows.append(
            {
                'path': path,
                'added': added_only,
                'modified': modified,
                'deleted': deleted_only,
                'is_binary': is_binary,
            }
        )
    _commit_cache[cache_key] = {'ts': time.time(), 'value': rows}
    return rows


def get_commit_patch_text(repo_path, commit_hash):
    if not _is_git_repo(repo_path):
        return None
    cache_key = (repo_path, commit_hash, 'patch')
    cached = _commit_cache.get(cache_key)
    if cached and (time.time() - cached['ts'] <= _CACHE_TTL_SEC):
        return cached['value']
    result = _run_git(
        repo_path,
        [
            'format-patch',
            '-1',
            '--stdout',
            '--no-signature',
            commit_hash,
        ],
        timeout=15,
    )
    if result.returncode != 0:
        return None
    _commit_cache[cache_key] = {'ts': time.time(), 'value': result.stdout}
    return result.stdout


def get_commit_diff_text(repo_path, commit_hash):
    if not _is_git_repo(repo_path):
        return None
    cache_key = (repo_path, commit_hash, 'diff')
    cached = _commit_cache.get(cache_key)
    if cached and (time.time() - cached['ts'] <= _CACHE_TTL_SEC):
        return cached['value']
    result = _run_git(
        repo_path,
        [
            'show',
            '-1',
            '--patch',
            '--format=',
            '--no-color',
            commit_hash,
        ],
        timeout=15,
    )
    if result.returncode != 0:
        return None
    _commit_cache[cache_key] = {'ts': time.time(), 'value': result.stdout}
    return result.stdout


def get_all_git_repos_info():
    """获取所有配置的仓库的 git 信息"""
    result = []
    for idx, repo_path in enumerate(GIT_REPOS):
        repo_name = os.path.basename(repo_path)
        log = get_git_log(repo_path)
        status = get_git_status(repo_path)

        info = {
            'id': idx,
            'name': repo_name,
            'path': repo_path,
            'logs': log or [],
            'status': status
        }
        result.append(info)
    return result
