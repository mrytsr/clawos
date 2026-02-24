import os
import subprocess
import time


GIT_REPOS = [
    os.path.expanduser('~/clawos'),
    os.path.expanduser('~/.openclaw/workspace'),
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


def get_git_log_compact(repo_path, max_count=50):
    try:
        if not _is_git_repo(repo_path):
            return None

        fmt = '%H%x09%an%x09%ad%x09%s'
        cmd = [
            'log',
            '-n',
            str(max_count),
            '--date=format:%Y-%m-%d %H:%M',
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
            parts = raw.split('\t', 3)
            if len(parts) < 3:
                continue
            commit_hash = parts[0].strip()
            author = parts[1].strip()
            committed_at = parts[2].strip()
            subject = parts[3].strip() if len(parts) > 3 else ''
            logs.append(
                {
                    'hash': commit_hash,
                    'author': author,
                    'committed_at': committed_at,
                    'subject': subject,
                }
            )
        return logs
    except Exception as e:
        print(f"Error getting git log from {repo_path}: {e}")
        return None


def get_git_log_compact_paged(repo_path, max_count=50, page=1, per_page=20):
    try:
        if not _is_git_repo(repo_path):
            return None

        page = int(page) if page else 1
        per_page = int(per_page) if per_page else 20
        max_count = int(max_count) if max_count else 50

        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 1
        if max_count < 1:
            max_count = 1

        skip = (page - 1) * per_page
        if skip >= max_count:
            return {
                'repo_path': repo_path,
                'page': page,
                'per_page': per_page,
                'max_count': max_count,
                'has_more': False,
                'logs': [],
            }

        remaining = max_count - skip
        request_count = min(remaining, per_page + 1)

        fmt = '%H%x09%an%x09%ad%x09%s'
        cmd = [
            'log',
            '-n',
            str(request_count),
            '--skip',
            str(skip),
            '--date=format:%Y-%m-%d %H:%M',
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
            parts = raw.split('\t', 3)
            if len(parts) < 3:
                continue
            commit_hash = parts[0].strip()
            author = parts[1].strip()
            committed_at = parts[2].strip()
            subject = parts[3].strip() if len(parts) > 3 else ''
            logs.append(
                {
                    'hash': commit_hash,
                    'author': author,
                    'committed_at': committed_at,
                    'subject': subject,
                }
            )

        has_more = False
        if len(logs) > per_page:
            has_more = True
            logs = logs[:per_page]

        return {
            'repo_path': repo_path,
            'page': page,
            'per_page': per_page,
            'max_count': max_count,
            'has_more': has_more,
            'logs': logs,
        }
    except Exception as e:
        print(f"Error getting paged git log from {repo_path}: {e}")
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


def get_git_status_porcelain(repo_path):
    try:
        if not _is_git_repo(repo_path):
            return None
        result = _run_git(repo_path, ['status', '--porcelain'], timeout=10)
        if result.returncode != 0:
            return None
        return result.stdout or ''
    except Exception as e:
        print(f"Error getting porcelain git status from {repo_path}: {e}")
        return None


def git_stage_all(repo_path):
    try:
        if not _is_git_repo(repo_path):
            return None
        result = _run_git(repo_path, ['add', '-A'], timeout=30)
        return result
    except Exception as e:
        print(f"Error staging changes in {repo_path}: {e}")
        return None


def get_git_staged_diff_text(repo_path, max_chars=20000):
    try:
        if not _is_git_repo(repo_path):
            return None
        result = _run_git(repo_path, ['diff', '--cached', '--no-color'], timeout=20)
        if result.returncode != 0:
            return None
        text = result.stdout or ''
        if max_chars and len(text) > int(max_chars):
            return text[: int(max_chars)]
        return text
    except Exception as e:
        print(f"Error getting staged diff from {repo_path}: {e}")
        return None


def get_git_worktree_diff_text(repo_path, max_chars=200000, file_filter=None):
    try:
        if not _is_git_repo(repo_path):
            return None

        # 如果指定了文件，只显示该文件的 diff
        if file_filter:
            # 先尝试 staged diff
            result = _run_git(repo_path, ['diff', '--cached', '--no-color', '--', file_filter], timeout=20)
            staged_text = result.stdout or ''
            
            # 再尝试 unstaged diff  
            result = _run_git(repo_path, ['diff', '--no-color', '--', file_filter], timeout=20)
            unstaged_text = result.stdout or ''
            
            out = ''
            if staged_text.strip():
                out += '===== STAGED =====\n\n' + staged_text.rstrip() + '\n\n'
            if unstaged_text.strip():
                out += '===== UNSTAGED =====\n\n' + unstaged_text.rstrip() + '\n\n'
            
            if not out.strip():
                out = '(no changes for ' + file_filter + ')\n'
            
            if max_chars and len(out) > int(max_chars):
                out = out[:int(max_chars)] + '\n\n... (truncated)\n'
            return out

        staged = _run_git(repo_path, ['diff', '--cached', '--no-color'], timeout=20)
        if staged.returncode != 0:
            return None

        unstaged = _run_git(repo_path, ['diff', '--no-color'], timeout=20)
        if unstaged.returncode != 0:
            return None

        untracked = _run_git(repo_path, ['ls-files', '--others', '--exclude-standard'], timeout=10)
        if untracked.returncode != 0:
            return None

        out = ''
        staged_text = staged.stdout or ''
        unstaged_text = unstaged.stdout or ''
        untracked_text = (untracked.stdout or '').strip()

        if staged_text.strip():
            out += '===== STAGED (git diff --cached) =====\n\n' + staged_text.rstrip() + '\n\n'
        if unstaged_text.strip():
            out += '===== UNSTAGED (git diff) =====\n\n' + unstaged_text.rstrip() + '\n\n'
        if untracked_text:
            out += '===== UNTRACKED (git ls-files --others --exclude-standard) =====\n\n' + untracked_text + '\n'

        if not out.strip():
            out = '(no changes)\n'

        if max_chars and len(out) > int(max_chars):
            return out[: int(max_chars)] + '\n\n... (truncated)\n'
        return out
    except Exception as e:
        print(f"Error getting worktree diff from {repo_path}: {e}")
        return None


def _parse_numstat_lines(text):
    rows = []
    for line in (text or '').splitlines():
        raw = line.strip('\n').strip('\r')
        if not raw:
            continue
        parts = raw.split('\t')
        if len(parts) < 3:
            continue
        added_raw, deleted_raw, path = parts[0], parts[1], '\t'.join(parts[2:])
        is_binary = added_raw == '-' or deleted_raw == '-'
        added = int(added_raw) if (not is_binary and added_raw.isdigit()) else None
        deleted = int(deleted_raw) if (not is_binary and deleted_raw.isdigit()) else None
        rows.append({'path': path, 'added': added, 'deleted': deleted, 'is_binary': is_binary})
    return rows


def get_git_worktree_numstat(repo_path, max_files=300):
    try:
        if not _is_git_repo(repo_path):
            return None

        staged = _run_git(repo_path, ['diff', '--cached', '--numstat'], timeout=20)
        if staged.returncode != 0:
            return None

        unstaged = _run_git(repo_path, ['diff', '--numstat'], timeout=20)
        if unstaged.returncode != 0:
            return None

        untracked = _run_git(repo_path, ['ls-files', '--others', '--exclude-standard'], timeout=10)
        if untracked.returncode != 0:
            return None

        merged = {}

        def upsert(rows):
            for r in rows:
                p = r.get('path') or ''
                if not p:
                    continue
                cur = merged.get(p)
                if not cur:
                    merged[p] = {
                        'path': p,
                        'added': 0 if r.get('added') is not None else None,
                        'deleted': 0 if r.get('deleted') is not None else None,
                        'is_binary': bool(r.get('is_binary')),
                        'untracked': False,
                    }
                    cur = merged[p]

                if r.get('is_binary'):
                    cur['is_binary'] = True
                    cur['added'] = None
                    cur['deleted'] = None
                    continue

                if cur.get('is_binary'):
                    continue

                a = r.get('added') if r.get('added') is not None else 0
                d = r.get('deleted') if r.get('deleted') is not None else 0
                cur['added'] = (cur.get('added') or 0) + int(a)
                cur['deleted'] = (cur.get('deleted') or 0) + int(d)

        upsert(_parse_numstat_lines(staged.stdout))
        upsert(_parse_numstat_lines(unstaged.stdout))

        for p in (untracked.stdout or '').splitlines():
            p = (p or '').strip()
            if not p:
                continue
            if p not in merged:
                merged[p] = {'path': p, 'added': 0, 'deleted': 0, 'is_binary': False, 'untracked': True}
            else:
                merged[p]['untracked'] = True

        rows = list(merged.values())

        def score(r):
            a = r.get('added') or 0
            d = r.get('deleted') or 0
            return int(a) + int(d)

        rows.sort(key=lambda r: (-score(r), str(r.get('path') or '')))
        if max_files and len(rows) > int(max_files):
            rows = rows[: int(max_files)]
        return rows
    except Exception as e:
        print(f"Error getting worktree numstat from {repo_path}: {e}")
        return None


def git_pull_ff_only(repo_path):
    try:
        if not _is_git_repo(repo_path):
            return None
        return _run_git(repo_path, ['pull', '--ff-only'], timeout=120)
    except Exception as e:
        print(f"Error pulling in {repo_path}: {e}")
        return None


def git_commit(repo_path, message):
    try:
        if not _is_git_repo(repo_path):
            return None
        msg = str(message or '').strip()
        if not msg:
            return None
        result = _run_git(repo_path, ['commit', '-m', msg], timeout=60)
        return result
    except Exception as e:
        print(f"Error committing in {repo_path}: {e}")
        return None


def git_checkout_all(repo_path):
    try:
        if not _is_git_repo(repo_path):
            return None
        result = _run_git(repo_path, ['checkout', '.'], timeout=60)
        return result
    except Exception as e:
        print(f"Error checkout all in {repo_path}: {e}")
        return None


def list_git_remotes(repo_path):
    try:
        if not _is_git_repo(repo_path):
            return None
        result = _run_git(repo_path, ['remote'], timeout=5)
        if result.returncode != 0:
            return []
        remotes = []
        for line in (result.stdout or '').splitlines():
            name = (line or '').strip()
            if name:
                remotes.append(name)
        return remotes
    except Exception as e:
        print(f"Error listing remotes in {repo_path}: {e}")
        return None


def get_current_branch(repo_path):
    try:
        if not _is_git_repo(repo_path):
            return None
        result = _run_git(repo_path, ['rev-parse', '--abbrev-ref', 'HEAD'], timeout=5)
        if result.returncode != 0:
            return None
        name = (result.stdout or '').strip()
        return name or None
    except Exception as e:
        print(f"Error getting current branch in {repo_path}: {e}")
        return None


def git_push(repo_path, remote=None, branch=None):
    try:
        if not _is_git_repo(repo_path):
            return None

        remote = str(remote or '').strip()
        if not remote:
            remotes = list_git_remotes(repo_path) or []
            if len(remotes) == 1:
                remote = remotes[0]
            elif 'origin' in remotes:
                remote = 'origin'
            elif remotes:
                remote = remotes[0]
            else:
                remote = 'origin'

        branch = str(branch or '').strip()
        if not branch:
            branch = get_current_branch(repo_path) or ''

        if not branch or branch.lower() == 'unknown' or branch == 'HEAD':
            return _run_git(repo_path, ['push', remote, 'HEAD'], timeout=120)

        return _run_git(repo_path, ['push', remote, branch], timeout=120)
    except Exception as e:
        print(f"Error pushing in {repo_path}: {e}")
        return None
