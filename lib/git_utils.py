import os
import subprocess


GIT_REPOS = [
    '/home/tjx/.openclaw/workspace/clawos',
    '/home/tjx/.openclaw/workspace/xiandan',
    '/home/tjx/.openclaw/workspace',
]


def get_git_log(repo_path, max_count=20):
    """获取指定仓库的 git log"""
    try:
        if not os.path.exists(os.path.join(repo_path, '.git')):
            return None

        cmd = ['git', 'log', '--oneline', '-n', str(max_count)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path, timeout=10)

        if result.returncode == 0:
            logs = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        logs.append({
                            'hash': parts[0],
                            'message': parts[1] if len(parts) > 1 else ''
                        })
            return logs
        return None
    except Exception as e:
        print(f"Error getting git log from {repo_path}: {e}")
        return None


def get_git_status(repo_path):
    """获取仓库的 git 状态"""
    try:
        if not os.path.exists(os.path.join(repo_path, '.git')):
            return None

        branch_result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        )
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else 'unknown'

        remote_result = subprocess.run(
            ['git', 'branch', '-r'],
            capture_output=True, text=True, cwd=repo_path, timeout=5
        )
        remote_count = len([b for b in remote_result.stdout.strip().split('\n') if b.strip()])

        return {
            'branch': branch,
            'remote_count': remote_count
        }
    except Exception as e:
        print(f"Error getting git status from {repo_path}: {e}")
        return None


def get_all_git_repos_info():
    """获取所有配置的仓库的 git 信息"""
    result = []
    for repo_path in GIT_REPOS:
        repo_name = os.path.basename(repo_path)
        log = get_git_log(repo_path)
        status = get_git_status(repo_path)

        info = {
            'name': repo_name,
            'path': repo_path,
            'logs': log or [],
            'status': status
        }
        result.append(info)
    return result
