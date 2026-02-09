function apiData(resp) {
    if (!resp || typeof resp !== 'object') return null;
    if (resp.success && resp.data && typeof resp.data === 'object') return resp.data;
    return null;
}

function __gitCommitShortId(hash) {
    return String(hash || '').slice(0, 8);
}

function __gitTruncate(text, maxLen) {
    const s = String(text || '');
    if (s.length <= maxLen) return { text: s, truncated: false };
    return { text: s.slice(0, maxLen) + '…', truncated: true };
}

function __gitCommitUrl(repoPath, commitHash) {
    const hash = String(commitHash || '');
    const path = String(repoPath || '');
    return '/commit/' + encodeURIComponent(hash) + '?repoPath=' + encodeURIComponent(path);
}

function __gitPrepareCommitNavigation(repoPath, listEl, commitHash) {
    __gitSaveScroll(repoPath, listEl);
    __gitSetReturnFlag(repoPath);
    return __gitCommitUrl(repoPath, commitHash);
}

function __gitNextActiveIndex(currentIndex, key, total) {
    const t = Number(total || 0);
    if (!Number.isFinite(t) || t <= 0) return -1;

    let idx = Number.isFinite(currentIndex) ? currentIndex : -1;
    if (idx < 0) idx = 0;
    if (idx >= t) idx = t - 1;

    if (key === 'ArrowDown') return Math.min(t - 1, idx + 1);
    if (key === 'ArrowUp') return Math.max(0, idx - 1);
    return idx;
}

function __gitScrollKey(repoPath) {
    return 'gitListScroll:' + String(repoPath || '');
}

function __gitSaveScroll(repoPath, listEl) {
    try {
        if (!window.sessionStorage) return;
        if (!listEl) return;
        window.sessionStorage.setItem(__gitScrollKey(repoPath), String(listEl.scrollTop || 0));
    } catch (e) {
        return;
    }
}

function __gitLoadScroll(repoPath) {
    try {
        if (!window.sessionStorage) return 0;
        const v = window.sessionStorage.getItem(__gitScrollKey(repoPath));
        const n = parseInt(v || '0', 10);
        return Number.isFinite(n) && n >= 0 ? n : 0;
    } catch (e) {
        return 0;
    }
}

function __gitSetReturnFlag(repoPath) {
    try {
        if (!window.sessionStorage) return;
        window.sessionStorage.setItem('gitCommitReturn', JSON.stringify({ repoPath: String(repoPath || ''), at: Date.now() }));
    } catch (e) {
        return;
    }
}

function __gitConsumeReturnFlag() {
    try {
        if (!window.sessionStorage) return null;
        const raw = window.sessionStorage.getItem('gitCommitReturn');
        if (!raw) return null;
        window.sessionStorage.removeItem('gitCommitReturn');
        const payload = JSON.parse(raw);
        if (!payload || typeof payload !== 'object') return null;
        const repoPath = payload.repoPath;
        if (!repoPath || typeof repoPath !== 'string') return null;
        return repoPath;
    } catch (e) {
        return null;
    }
}

function __gitListCss() {
    return '<style>' +
        '.git-shell { display:flex; flex-direction:column; gap:10px; }' +
        '.git-top { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }' +
        '.git-select { padding:8px 12px; border:1px solid #d0d7de; border-radius:8px; background:#fff; font-size:14px; flex:1; }' +
        '.git-list { max-height: calc(70vh - 120px); overflow:auto; outline:none; }' +
        '.git-item { padding:10px 12px; border-bottom:1px solid #eee; cursor:pointer; display:flex; flex-direction:column; gap:4px; }' +
        '.git-item:hover { background:#f6f8fa; }' +
        '.git-item.active { background:#ddf4ff; }' +
        '.git-meta { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }' +
        '.git-time { font-size:12px; color:#0969da; font-family: ui-monospace, monospace; }' +
        '.git-hash { font-size:11px; color:#57606a; font-family: ui-monospace, monospace; cursor:pointer; }' +
        '.git-hash:hover { color:#0969da; text-decoration:underline; }' +
        '.git-author { font-size:12px; color:#57606a; }' +
        '.git-subject { font-size:13px; color:#24292f; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }' +
        '.git-diff-btn { border:1px solid #d0d7de; background:#fff; border-radius:6px; padding:4px 10px; cursor:pointer; font-size:12px; }' +
        '.git-diff-btn:hover { background:#f6f8fa; }' +
        '.git-push-btn { border:1px solid #d0d7de; background:#fff; border-radius:6px; padding:4px 10px; cursor:pointer; font-size:12px; }' +
        '.git-push-btn:hover { background:#f6f8fa; }' +
        '.git-push-btn[disabled] { opacity:0.65; cursor:not-allowed; }' +
        '.git-skeleton { padding:10px 12px; border-bottom:1px solid #eee; }' +
        '.git-skel-line { height:10px; border-radius:6px; background: linear-gradient(90deg, #f6f8fa 0%, #eaeef2 40%, #f6f8fa 80%); background-size: 240px 100%; animation: gitShimmer 1.2s infinite linear; }' +
        '.git-skel-line.sm { width: 55%; margin-top: 8px; height: 11px; }' +
        '.git-skel-line.md { width: 75%; }' +
        '.git-skel-line.lg { width: 92%; }' +
        '@keyframes gitShimmer { 0% { background-position: -240px 0; } 100% { background-position: 240px 0; } }' +
        '.git-banner { display:flex; gap:10px; align-items:center; justify-content:space-between; padding:10px 12px; border:1px solid #ff818266; background:#ffebe9; color:#cf222e; border-radius:8px; }' +
        '.git-banner button { border:1px solid #d0d7de; background:#fff; border-radius:6px; padding:6px 10px; cursor:pointer; font-size:12px; }' +
        '.git-empty { padding:28px 16px; text-align:center; color:#57606a; }' +
        '.git-empty svg { display:block; margin:0 auto 10px; opacity:0.9; }' +
        '.git-foot { padding:10px 12px; text-align:center; color:#6e7781; font-size:12px; }' +
        '</style>';
}

function __gitDirtyLineHtml(hasChanges, statusText, changeInfo) {
    const color = hasChanges ? '#cf222e' : '#2da44e';
    const btn = hasChanges
        ? '<button type="button" class="git-diff-btn" id="gitDiffBtn">diff</button><button type="button" class="git-push-btn" id="gitPushBtn">推送变更</button>'
        : '';
    const hint = hasChanges ? '<span id="gitPushHint" style="font-size:12px;color:#57606a;"></span>' : '';
    return '<div id="gitRepoDirtyLine" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px;color:' + color + ';margin-top:4px;">' +
        '<span>' + escapeHtml(statusText || '') + escapeHtml(changeInfo || '') + '</span>' +
        btn +
        hint +
        '</div>';
}

function __gitBindPushButton(repoPath) {
    const btn = document.getElementById('gitPushBtn');
    if (!btn) return;
    const hint = document.getElementById('gitPushHint');
    btn.addEventListener('click', function() {
        if (btn.disabled) return;
        btn.disabled = true;
        const prevText = btn.textContent;
        let didReload = false;
        btn.textContent = '推送中…';
        if (hint) hint.textContent = '处理中…';
        const headers = authHeaders ? (authHeaders() || {}) : {};
        headers['Content-Type'] = 'application/json';
        fetch('/api/git/push-changes', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ path: String(repoPath || '') })
        })
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                const payload = apiData(resp);
                if (!payload) {
                    const msg = resp && resp.error && resp.error.message ? resp.error.message : '推送失败';
                    throw new Error(msg);
                }
                if (payload.status === 'clean') {
                    if (typeof showToast === 'function') showToast('当前没有可提交的变更');
                    if (hint) hint.textContent = '没有可提交的变更';
                    return;
                }
                if (payload.pushed) {
                    if (typeof showToast === 'function') showToast('已推送：' + (payload.commit_msg || ''));
                    didReload = true;
                    window.loadGitList(repoPath);
                    return;
                }
                const msg = payload.message || '推送失败';
                throw new Error(msg);
            })
            .catch(function(e) {
                const msg = e && e.message ? e.message : '推送失败';
                if (typeof showToast === 'function') showToast(msg);
                if (hint) hint.textContent = msg;
            })
            .finally(function() {
                if (!didReload) {
                    btn.disabled = false;
                    btn.textContent = prevText;
                }
            });
    });
}

function __gitBindDiffButton(repoPath) {
    const btn = document.getElementById('gitDiffBtn');
    if (!btn) return;
    btn.addEventListener('click', function() {
        const url = '/git/diff?repoPath=' + encodeURIComponent(String(repoPath || ''));
        try {
            window.open(url, '_blank', 'noopener');
        } catch (e) {
            window.location.href = url;
        }
    });
}

function __gitSkeletonHtml(rows) {
    const n = rows || 8;
    let html = '';
    for (let i = 0; i < n; i += 1) {
        html += '<div class="git-skeleton">' +
            '<div class="git-skel-line ' + (i % 3 === 0 ? 'lg' : i % 3 === 1 ? 'md' : 'lg') + '"></div>' +
            '<div class="git-skel-line sm"></div>' +
            '</div>';
    }
    return html;
}

function __gitEmptyHtml() {
    return '<div class="git-empty">' +
        '<svg width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M18 22C18 18.686 20.686 16 24 16H48C51.314 16 54 18.686 54 22V50C54 53.314 51.314 56 48 56H24C20.686 56 18 53.314 18 50V22Z" stroke="#8C959F" stroke-width="2"/>' +
        '<path d="M26 27H46" stroke="#8C959F" stroke-width="2" stroke-linecap="round"/>' +
        '<path d="M26 35H42" stroke="#8C959F" stroke-width="2" stroke-linecap="round"/>' +
        '<path d="M26 43H38" stroke="#8C959F" stroke-width="2" stroke-linecap="round"/>' +
        '</svg>' +
        '<div style="font-size:14px;font-weight:600;margin-bottom:4px;">暂无提交记录</div>' +
        '<div style="font-size:12px;">该仓库还没有提交或日志不可用</div>' +
        '</div>';
}

function __gitErrorBannerHtml(message) {
    const msg = escapeHtml(message || '加载失败');
    return '<div class="git-banner" role="alert">' +
        '<div style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + msg + '</div>' +
        '<button type="button" id="gitRetryBtn">重试</button>' +
        '</div>';
}

function __gitCommitItemHtml(commit, branch, repoPath, index) {
    const time = escapeHtml(commit.committed_at || '');
    const author = escapeHtml(commit.author || '');
    const subjectRaw = String(commit.subject || '');
    const trunc = __gitTruncate(subjectRaw, 60);
    const subject = escapeHtml(trunc.text || '');
    const hashFull = String(commit.hash || '');
    const shortHash = escapeHtml(__gitCommitShortId(hashFull));
    const hashEsc = escapeHtml(hashFull);
    const repoPathEsc = escapeHtml(repoPath || '');

    return '<div class="git-item" data-index="' + String(index) + '" data-hash="' + hashEsc + '" data-repo="' + repoPathEsc + '">' +
        '<div class="git-meta">' +
        '<span class="git-time">' + time + '</span>' +
        '<span class="git-hash" data-hash="' + hashEsc + '" data-repo="' + repoPathEsc + '">' + shortHash + '</span>' +
        '<span class="git-author" title="' + author + '">' + (author || '-') + '</span>' +
        (branch ? '<span style="background:#ddf4ff;color:#0969da;padding:1px 6px;border-radius:999px;font-size:10px;">' + escapeHtml(branch) + '</span>' : '') +
        '</div>' +
        '<div class="git-subject" title="' + escapeHtml(subjectRaw) + '">' + (subject || '-') + '</div>' +
        '</div>';
}

function __gitMountCommitList(container, repoPath, headerData) {
    const state = {
        repoPath: repoPath,
        page: 1,
        perPage: 20,
        maxCount: 50,
        hasMore: true,
        loading: false,
        activeIndex: -1,
        commits: []
    };

    const headerHtml = headerData && headerData.html ? headerData.html : '';
    container.innerHTML = __gitListCss() + '<div class="git-shell">' + headerHtml +
        '<div class="git-list" id="gitCommitList" tabindex="0" aria-label="Git commits">' +
        __gitSkeletonHtml(8) +
        '</div>' +
        '<div class="git-foot" id="gitCommitFoot" style="display:none;"></div>' +
        '</div>';

    const listEl = document.getElementById('gitCommitList');
    const footEl = document.getElementById('gitCommitFoot');

    function setFoot(text) {
        if (!footEl) return;
        if (!text) {
            footEl.style.display = 'none';
            footEl.textContent = '';
            return;
        }
        footEl.style.display = 'block';
        footEl.textContent = text;
    }

    function setActiveIndex(nextIndex, ensureVisible) {
        if (!listEl) return;
        const total = state.commits.length;
        if (total <= 0) {
            state.activeIndex = -1;
            return;
        }
        let idx = nextIndex;
        if (idx < 0) idx = 0;
        if (idx >= total) idx = total - 1;

        const prev = state.activeIndex;
        state.activeIndex = idx;
        if (prev >= 0) {
            const prevEl = listEl.querySelector('.git-item[data-index="' + String(prev) + '"]');
            if (prevEl) prevEl.classList.remove('active');
        }
        const curEl = listEl.querySelector('.git-item[data-index="' + String(idx) + '"]');
        if (curEl) curEl.classList.add('active');
        if (ensureVisible && curEl && typeof curEl.scrollIntoView === 'function') {
            curEl.scrollIntoView({ block: 'nearest' });
        }
    }

    function navigateToCommit(commitHash) {
        window.location.href = __gitPrepareCommitNavigation(state.repoPath, listEl, commitHash);
    }

    function renderInitial(commits) {
        if (!listEl) return;
        if (!commits || commits.length === 0) {
            listEl.innerHTML = __gitEmptyHtml();
            setFoot('');
            return;
        }
        listEl.innerHTML = commits.map(function(c, i) {
            return __gitCommitItemHtml(c, headerData && headerData.branch, state.repoPath, i);
        }).join('');

        const savedScrollTop = __gitLoadScroll(state.repoPath);
        if (savedScrollTop > 0) listEl.scrollTop = savedScrollTop;
        setActiveIndex(0, false);
        try { listEl.focus(); } catch (e) { return; }
    }

    function appendCommits(commits, startIndex) {
        if (!listEl) return;
        if (!commits || commits.length === 0) return;
        const html = commits.map(function(c, i) {
            return __gitCommitItemHtml(c, headerData && headerData.branch, state.repoPath, startIndex + i);
        }).join('');
        listEl.insertAdjacentHTML('beforeend', html);
    }

    function fetchPage(page) {
        if (state.loading) return;
        state.loading = true;
        setFoot('加载中…');
        fetch('/api/git/commit-list?path=' + encodeURIComponent(state.repoPath) +
            '&max_count=' + String(state.maxCount) +
            '&page=' + String(page) +
            '&per_page=' + String(state.perPage), { headers: authHeaders() })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                const payload = apiData(data);
                if (!payload || !payload.is_repo) {
                    if (listEl) listEl.innerHTML = '<div style="padding:16px;text-align:center;color:#cf222e;">此目录不是Git仓库</div>';
                    setFoot('');
                    state.hasMore = false;
                    state.commits = [];
                    return;
                }

                const rows = Array.isArray(payload.commits) ? payload.commits : [];
                const pg = payload.pagination || {};
                state.hasMore = !!pg.has_more;
                state.page = pg.page ? pg.page : page;

                if (page === 1) {
                    state.commits = rows.slice();
                    renderInitial(state.commits);
                } else {
                    const startLen = state.commits.length;
                    rows.forEach(function(r) { state.commits.push(r); });
                    appendCommits(rows, startLen);
                }

                if (!state.hasMore) {
                    setFoot(state.commits.length > 0 ? '已加载全部提交' : '');
                } else {
                    setFoot('');
                }
            })
            .catch(function() {
                if (!listEl) return;
                listEl.innerHTML = __gitErrorBannerHtml('接口异常：无法获取提交记录');
                setFoot('');
                const btn = document.getElementById('gitRetryBtn');
                if (btn) btn.addEventListener('click', function() { __gitMountCommitList(container, repoPath, headerData); });
            })
            .finally(function() {
                state.loading = false;
            });
    }

    if (listEl) {
        listEl.addEventListener('scroll', function() {
            __gitSaveScroll(state.repoPath, listEl);
            if (!state.hasMore || state.loading) return;
            const threshold = 200;
            if (listEl.scrollTop + listEl.clientHeight >= listEl.scrollHeight - threshold) {
                fetchPage(state.page + 1);
            }
        });

        listEl.addEventListener('click', function(e) {
            const target = e.target;
            if (!target) return;
            const item = target.closest ? target.closest('.git-item') : null;
            if (item && item.getAttribute) {
                const idx = parseInt(item.getAttribute('data-index') || '-1', 10);
                if (Number.isFinite(idx) && idx >= 0) setActiveIndex(idx, false);
            }
            const hashEl = target.closest ? target.closest('.git-hash') : null;
            if (hashEl && hashEl.getAttribute) {
                const hash = hashEl.getAttribute('data-hash') || '';
                if (hash) navigateToCommit(hash);
            }
        });

        listEl.addEventListener('keydown', function(e) {
            if (!e) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                setActiveIndex(__gitNextActiveIndex(state.activeIndex, 'ArrowDown', state.commits.length), true);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                setActiveIndex(__gitNextActiveIndex(state.activeIndex, 'ArrowUp', state.commits.length), true);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (state.activeIndex < 0 || state.activeIndex >= state.commits.length) return;
                const c = state.commits[state.activeIndex];
                if (c && c.hash) navigateToCommit(c.hash);
            }
        });
    }

    fetchPage(1);
}

window.loadGitList = function(specificRepoPath) {
    const container = document.getElementById('gitListContainer');
    if (container) container.innerHTML = __gitListCss() + '<div class="git-shell"><div class="git-list">' + __gitSkeletonHtml(8) + '</div></div>';
    
    // 如果指定了路径，直接获取该仓库的信息
    if (specificRepoPath) {
        fetch('/api/git/repo-status?path=' + encodeURIComponent(specificRepoPath), { headers: authHeaders() })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                const payload = apiData(data);
                if (!container) return;
                if (!payload || !payload.is_repo) {
                    container.innerHTML = __gitListCss() + '<div style="padding:16px;text-align:center;color:#cf222e;">此目录不是Git仓库</div>';
                    return;
                }

                const repo = payload;
                const branch = repo.branch || 'unknown';
                const commit = repo.commit || '';
                const repoStatus = repo.status || {};
                const hasChanges = repoStatus.has_changes || false;

                let statusText = hasChanges ? '✗ Dirty' : '✓ Clean';
                let changeInfo = '';
                if (hasChanges) {
                    const changes = [];
                    if (repoStatus.untracked > 0) changes.push('[+' + repoStatus.untracked + ']');
                    if (repoStatus.modified > 0) changes.push('[~' + repoStatus.modified + ']');
                    if (repoStatus.deleted > 0) changes.push('[-' + repoStatus.deleted + ']');
                    if (changes.length > 0) changeInfo = ' ' + changes.join(' ');
                }

                const headerHtml = '<div style="padding:12px 16px;background:#f6f8fa;border-bottom:1px solid #d0d7de;border-radius:8px 8px 0 0;">' +
                    '<div style="font-size:14px;font-weight:600;color:#24292f;margin-bottom:8px;">📦 ' + escapeHtml(repo.name) + '</div>' +
                    '<div style="font-size:12px;color:#57606a;">分支: <span style="background:#ddf4ff;color:#0969da;padding:1px 6px;border-radius:999px;font-size:10px;">' + escapeHtml(branch) + '</span> <span style="font-family:ui-monospace;color:#57606a;">@' + escapeHtml(commit) + '</span></div>' +
                    '<div style="font-size:12px;color:#57606a;margin-top:4px;word-break:break-all;">路径: ' + escapeHtml(repo.path) + '</div>' +
                    __gitDirtyLineHtml(hasChanges, statusText, changeInfo) +
                    '</div>';

                __gitMountCommitList(container, specificRepoPath, { html: headerHtml, branch: branch });
                if (hasChanges) {
                    __gitBindDiffButton(specificRepoPath);
                    __gitBindPushButton(specificRepoPath);
                }
            })
            .catch(function() {
                if (!container) return;
                container.innerHTML = __gitListCss() + __gitErrorBannerHtml('接口异常：无法获取仓库信息');
                const btn = document.getElementById('gitRetryBtn');
                if (btn) btn.addEventListener('click', function() { window.loadGitList(specificRepoPath); });
            });
        return;
    }
    
    // 原版：使用下拉选择多个仓库
    fetch('/api/git/list', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && payload.repos) {
                const container = document.getElementById('gitListContainer');
                if (container) {
                    window.__gitRepos = payload.repos || [];
                    const css = __gitListCss();
                    const html = css + '<div class="git-shell"><div class="git-top"><span style="font-size:12px;color:#57606a;">仓库</span><select id="gitRepoSelect" class="git-select"></select></div><div id="gitRepoPanel"></div></div>';
                    container.innerHTML = html;

                    const repos = window.__gitRepos || [];
                    const select = document.getElementById('gitRepoSelect');
                    const panelEl = document.getElementById('gitRepoPanel');

                    function renderRepo(repo) {
                        if (!repo) return;
                        const branch = repo.status ? repo.status.branch : '-';
                        select.value = String(repo.id);
                        if (!panelEl) return;
                        __gitMountCommitList(panelEl, repo.path, { html: '', branch: branch });
                    }

                    repos.forEach(function(r) {
                        const opt = document.createElement('option');
                        opt.value = String(r.id);
                        opt.textContent = r.name + ' (' + (r.status && r.status.branch ? r.status.branch : '-') + ')';
                        select.appendChild(opt);
                    });

                    select.addEventListener('change', function() {
                        const rid = this.value;
                        const repo = repos.find(function(r) { return String(r.id) === String(rid); });
                        renderRepo(repo);
                    });

                    if (repos.length > 0) renderRepo(repos[0]);
                }
            }
        });
};

function __setContainerHtml(id, html) {
    const el = document.getElementById(id);
    if (!el) return null;
    el.innerHTML = html;
    return el;
}

function __loadingHtml(label) {
    return '<div style="text-align:center;padding:40px;color:#666;">🔄 ' + escapeHtml(label || '加载中...') + '</div>';
}

function __emptyHtml(label) {
    return '<div style="text-align:center;padding:40px;color:#666;">' + escapeHtml(label || '暂无数据') + '</div>';
}

function __errorHtml(label) {
    return '<div style="text-align:center;padding:40px;color:#cf222e;">' + escapeHtml(label || '加载失败') + '</div>';
}

function __postJson(url, payload) {
    return fetch(url, {
        method: 'POST',
        headers: Object.assign({ 'Content-Type': 'application/json' }, (typeof authHeaders === 'function') ? authHeaders() : {}),
        body: JSON.stringify(payload || {})
    }).then(function(r) { return r.json(); });
}

function __fmtPct(n) {
    const v = typeof n === 'number' && Number.isFinite(n) ? n : 0;
    return (Math.round(v * 10) / 10).toFixed(1);
}

function __fmtInt(n) {
    const v = typeof n === 'number' && Number.isFinite(n) ? n : 0;
    return String(Math.round(v));
}

window.loadProcessList = function() {
    const container = __setContainerHtml('processListContainer', __loadingHtml('加载中...'));
    fetch('/api/process/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const processes = payload && Array.isArray(payload.processes) ? payload.processes : [];
            const stats = payload && payload.stats ? payload.stats : {};
            if (!processes.length) {
                container.innerHTML = __emptyHtml('暂无进程数据');
                return;
            }

            const cpuPct = typeof stats.cpu_percent === 'number' ? stats.cpu_percent : null;
            const memUsed = typeof stats.memory_used === 'number' ? stats.memory_used : null;
            const memTotal = typeof stats.memory_total === 'number' ? stats.memory_total : null;
            const memPct = typeof stats.memory_percent === 'number' ? stats.memory_percent : null;
            const procCount = typeof stats.process_count === 'number' ? stats.process_count : processes.length;

            const header = '<div style="padding:14px 16px;border-bottom:1px solid #eee;background:#f6f8fa;">'
                + '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;">'
                + '<div style="font-weight:600;">总进程：' + escapeHtml(String(procCount)) + '</div>'
                + '<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#57606a;">'
                + '<span>CPU：' + (cpuPct === null ? '-' : escapeHtml(__fmtPct(cpuPct)) + '%') + '</span>'
                + '<span>内存：' + (memUsed === null || memTotal === null ? '-' : escapeHtml(formatSize(memUsed)) + ' / ' + escapeHtml(formatSize(memTotal)) + (memPct === null ? '' : ' (' + escapeHtml(__fmtPct(memPct)) + '%)')) + '</span>'
                + '</div>'
                + '</div>'
                + '</div>';

            const rows = processes.map(function(p) {
                const pid = p.pid;
                const cpu = typeof p.cpu_percent === 'number' ? p.cpu_percent : 0;
                const mem = typeof p.memory_percent === 'number' ? p.memory_percent : 0;
                const rss = typeof p.memory_rss === 'number' ? p.memory_rss : 0;
                const user = p.user || '-';
                const cmd = p.command || p.full_command || '-';
                const elapsed = p.elapsed || '-';
                const safePid = escapeHtml(String(pid));
                return '<div style="padding:12px 16px;border-bottom:1px solid #eee;">'
                    + '<div style="display:flex;gap:12px;align-items:flex-start;justify-content:space-between;">'
                    + '<div style="min-width:0;">'
                    + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(cmd)) + '</div>'
                    + '<div style="margin-top:4px;font-size:12px;color:#57606a;display:flex;gap:10px;flex-wrap:wrap;">'
                    + '<span>PID ' + safePid + '</span>'
                    + '<span>' + escapeHtml(String(user)) + '</span>'
                    + '<span>CPU ' + escapeHtml(__fmtPct(cpu)) + '%</span>'
                    + '<span>MEM ' + escapeHtml(__fmtPct(mem)) + '%</span>'
                    + '<span>' + escapeHtml(formatSize(rss)) + '</span>'
                    + '<span>' + escapeHtml(String(elapsed)) + '</span>'
                    + '</div>'
                    + '</div>'
                    + '<div style="display:flex;gap:8px;flex-shrink:0;">'
                    + '<button type="button" data-action="proc-detail" data-pid="' + safePid + '" style="border:1px solid #d0d7de;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;">详情</button>'
                    + '<button type="button" data-action="proc-kill" data-pid="' + safePid + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">结束</button>'
                    + '</div>'
                    + '</div>'
                    + '</div>';
            }).join('');

            container.innerHTML = header + rows;

            Array.from(container.querySelectorAll('button[data-action="proc-detail"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const pid = parseInt(btn.getAttribute('data-pid') || '0', 10);
                    if (!pid) return;
                    window.openProcessDetailModal(pid);
                });
            });

            Array.from(container.querySelectorAll('button[data-action="proc-kill"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const pid = parseInt(btn.getAttribute('data-pid') || '0', 10);
                    if (!pid) return;
                    const ok = window.confirm('确认结束进程 PID ' + String(pid) + ' ?');
                    if (!ok) return;
                    fetch('/api/process/kill/' + encodeURIComponent(String(pid)), { method: 'POST', headers: authHeaders() })
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            const payload = apiData(data);
                            if (payload && payload.message && typeof window.showToast === 'function') window.showToast(payload.message, 'success');
                            window.loadProcessList();
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('结束失败', 'error');
                        });
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败');
        });
};

window.openProcessDetailModal = function(pid) {
    Drawer.open('processDetailModal');
    const container = __setContainerHtml('processDetailContent', __loadingHtml('加载中...'));
    fetch('/api/process/ports/' + encodeURIComponent(String(pid)), { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const ports = payload && Array.isArray(payload.ports) ? payload.ports : [];
            const rows = ports.length
                ? ports.map(function(p) {
                    return '<div style="padding:10px 12px;border:1px solid #d0d7de;border-radius:8px;background:#fff;display:flex;justify-content:space-between;gap:10px;">'
                        + '<div style="font-weight:600;">' + escapeHtml(String(p.protocol || '-')) + ' ' + escapeHtml(String(p.port || '-')) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;text-align:right;">' + escapeHtml(String(p.state || '-')) + (p.program ? ' · ' + escapeHtml(String(p.program)) : '') + '</div>'
                        + '</div>';
                }).join('<div style="height:8px;"></div>')
                : __emptyHtml('未发现监听端口');

            container.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
                + '<div style="font-weight:600;">PID ' + escapeHtml(String(pid)) + '</div>'
                + '<div style="display:flex;gap:8px;">'
                + '<button type="button" id="procDetailRefreshBtn" style="border:1px solid #d0d7de;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;">刷新</button>'
                + '<button type="button" id="procDetailKillBtn" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">结束</button>'
                + '</div>'
                + '</div>'
                + rows;

            const refreshBtn = document.getElementById('procDetailRefreshBtn');
            if (refreshBtn) refreshBtn.addEventListener('click', function() { window.openProcessDetailModal(pid); });
            const killBtn = document.getElementById('procDetailKillBtn');
            if (killBtn) killBtn.addEventListener('click', function() {
                const ok = window.confirm('确认结束进程 PID ' + String(pid) + ' ?');
                if (!ok) return;
                fetch('/api/process/kill/' + encodeURIComponent(String(pid)), { method: 'POST', headers: authHeaders() })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        const payload = apiData(data);
                        if (payload && payload.message && typeof window.showToast === 'function') window.showToast(payload.message, 'success');
                        Drawer.close('processDetailModal');
                        window.loadProcessList();
                    })
                    .catch(function() {
                        if (typeof window.showToast === 'function') window.showToast('结束失败', 'error');
                    });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败');
        });
};

window.loadSystemPackageList = function() {
    const container = __setContainerHtml('systemPackageListContainer', __loadingHtml('加载中...'));
    fetch('/api/system-packages/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const packages = payload && Array.isArray(payload.packages) ? payload.packages : [];
            if (!packages.length) {
                container.innerHTML = __emptyHtml('暂无系统包数据');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + packages.map(function(p) {
                const name = p.name || '-';
                const version = p.version || '';
                const manager = p.manager || '';
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:center;">'
                    + '<div style="min-width:0;">'
                    + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
                    + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(version)) + (manager ? ' · ' + escapeHtml(String(manager)) : '') + '</div>'
                    + '</div>'
                    + '<button type="button" data-action="sys-pkg-uninstall" data-name="' + escapeHtml(String(name)) + '" data-manager="' + escapeHtml(String(manager)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;flex-shrink:0;">卸载</button>'
                    + '</div>';
            }).join('') + '</div>';

            Array.from(container.querySelectorAll('button[data-action="sys-pkg-uninstall"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const name = btn.getAttribute('data-name') || '';
                    const manager = btn.getAttribute('data-manager') || '';
                    if (!name) return;
                    const ok = window.confirm('确认卸载 ' + name + ' ?');
                    if (!ok) return;
                    __postJson('/api/system-packages/uninstall', { name: name, manager: manager })
                        .then(function(data) {
                            const payload = apiData(data);
                            const msg = payload && payload.message ? payload.message : '已提交';
                            if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                            window.loadSystemPackageList();
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('卸载失败', 'error');
                        });
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

function __renderPkgList(containerId, opts) {
    const options = opts || {};
    const title = options.title || '';
    const listUrl = options.listUrl || '';
    const installUrl = options.installUrl || '';
    const uninstallUrl = options.uninstallUrl || '';
    const container = __setContainerHtml(containerId, __loadingHtml('加载中...'));
    fetch(listUrl, { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const packages = payload && Array.isArray(payload.packages) ? payload.packages : [];

            const header = '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px;">'
                + '<input id="' + escapeHtml(containerId) + '_installInput" type="text" placeholder="输入包名，例如 ' + escapeHtml(title) + '" style="flex:1;min-width:180px;padding:10px 12px;border:1px solid #d0d7de;border-radius:10px;font-size:14px;">'
                + '<button type="button" id="' + escapeHtml(containerId) + '_installBtn" style="border:1px solid #0969da;background:#0969da;color:#fff;border-radius:10px;padding:10px 14px;cursor:pointer;">安装</button>'
                + '</div>';

            if (!packages.length) {
                container.innerHTML = header + __emptyHtml('暂无已安装包');
            } else {
                const rows = '<div style="display:flex;flex-direction:column;gap:10px;">' + packages.map(function(p) {
                    const name = p.name || '-';
                    const version = p.version || '';
                    return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:center;">'
                        + '<div style="min-width:0;">'
                        + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(version)) + '</div>'
                        + '</div>'
                        + '<button type="button" data-action="pkg-uninstall" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;flex-shrink:0;">卸载</button>'
                        + '</div>';
                }).join('') + '</div>';
                container.innerHTML = header + rows;
            }

            const inputEl = document.getElementById(containerId + '_installInput');
            const installBtn = document.getElementById(containerId + '_installBtn');
            if (installBtn) {
                installBtn.addEventListener('click', function() {
                    const pkg = inputEl ? (inputEl.value || '').trim() : '';
                    if (!pkg) return;
                    installBtn.disabled = true;
                    installBtn.textContent = '安装中...';
                    __postJson(installUrl, { package: pkg })
                        .then(function(data) {
                            const payload = apiData(data);
                            const msg = payload && payload.message ? payload.message : '已提交';
                            if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                            __renderPkgList(containerId, options);
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('安装失败', 'error');
                        })
                        .finally(function() {
                            installBtn.disabled = false;
                            installBtn.textContent = '安装';
                        });
                });
            }

            Array.from(container.querySelectorAll('button[data-action="pkg-uninstall"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const name = btn.getAttribute('data-name') || '';
                    if (!name) return;
                    const ok = window.confirm('确认卸载 ' + name + ' ?');
                    if (!ok) return;
                    __postJson(uninstallUrl, { package: name })
                        .then(function(data) {
                            const payload = apiData(data);
                            const msg = payload && payload.message ? payload.message : '已提交';
                            if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                            __renderPkgList(containerId, options);
                        })
                        .catch(function() {
                            if (typeof window.showToast === 'function') window.showToast('卸载失败', 'error');
                        });
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败');
        });
}

window.loadPipList = function() {
    __renderPkgList('pipListContainer', {
        title: 'requests',
        listUrl: '/api/pip/list',
        installUrl: '/api/pip/install',
        uninstallUrl: '/api/pip/uninstall'
    });
};

window.loadNpmList = function() {
    __renderPkgList('npmListContainer', {
        title: 'eslint',
        listUrl: '/api/npm/list',
        installUrl: '/api/npm/install',
        uninstallUrl: '/api/npm/uninstall'
    });
};

window.loadDockerTabs = function(tab) {
    const t = (tab || 'images') === 'containers' ? 'containers' : 'images';
    const imagesEl = document.getElementById('dockerImagesContainer');
    const containersEl = document.getElementById('dockerContainersContainer');
    const tabs = Array.from(document.querySelectorAll('#dockerModal .docker-tab'));
    tabs.forEach(function(btn) {
        const isActive = (btn.getAttribute('data-tab') || '') === t;
        if (isActive) btn.classList.add('active');
        else btn.classList.remove('active');
        btn.style.borderBottomColor = isActive ? '#0969da' : 'transparent';
        btn.style.color = isActive ? '#0969da' : '#24292f';
        btn.style.fontWeight = isActive ? '600' : '400';
    });
    if (imagesEl) imagesEl.style.display = t === 'images' ? 'block' : 'none';
    if (containersEl) containersEl.style.display = t === 'containers' ? 'block' : 'none';

    if (t === 'images') {
        if (imagesEl) imagesEl.innerHTML = __loadingHtml('加载镜像...');
        fetch('/api/docker/images', { headers: authHeaders() })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                const payload = apiData(data);
                if (!imagesEl) return;
                const images = payload && Array.isArray(payload.images) ? payload.images : [];
                if (!images.length) {
                    imagesEl.innerHTML = __emptyHtml('暂无镜像');
                    return;
                }
                imagesEl.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + images.map(function(img) {
                    const repo = img.repository || '-';
                    const tag = img.tag || '';
                    const id = img.id || '';
                    const size = img.size || '';
                    const created = img.created || '';
                    return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:center;">'
                        + '<div style="min-width:0;">'
                        + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(repo)) + (tag ? ':' + escapeHtml(String(tag)) : '') + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(id)) + (size ? ' · ' + escapeHtml(String(size)) : '') + (created ? ' · ' + escapeHtml(String(created)) : '') + '</div>'
                        + '</div>'
                        + '<button type="button" data-action="docker-img-rm" data-id="' + escapeHtml(String(id)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;flex-shrink:0;">删除</button>'
                        + '</div>';
                }).join('') + '</div>';

                Array.from(imagesEl.querySelectorAll('button[data-action="docker-img-rm"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        if (!id) return;
                        const ok = window.confirm('确认删除镜像 ' + id + ' ?');
                        if (!ok) return;
                        __postJson('/api/docker/image/rm', { id: id })
                            .then(function(data) {
                                const payload = apiData(data);
                                const msg = payload && payload.message ? payload.message : '已提交';
                                if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                                window.loadDockerTabs('images');
                            })
                            .catch(function() {
                                if (typeof window.showToast === 'function') window.showToast('删除失败', 'error');
                            });
                    });
                });
            })
            .catch(function() {
                if (imagesEl) imagesEl.innerHTML = __errorHtml('加载失败（Docker 可能未安装）');
            });
    } else {
        if (containersEl) containersEl.innerHTML = __loadingHtml('加载容器...');
        fetch('/api/docker/containers', { headers: authHeaders() })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                const payload = apiData(data);
                if (!containersEl) return;
                const containers = payload && Array.isArray(payload.containers) ? payload.containers : [];
                if (!containers.length) {
                    containersEl.innerHTML = __emptyHtml('暂无容器');
                    return;
                }
                containersEl.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + containers.map(function(c) {
                    const id = c.id || '';
                    const name = c.name || '';
                    const image = c.image || '';
                    const status = c.status || '';
                    const ports = c.ports || '';
                    const running = status.toLowerCase().indexOf('up') >= 0;
                    const actionText = running ? '停止' : '启动';
                    const actionType = running ? 'stop' : 'start';
                    return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
                        + '<div style="min-width:0;">'
                        + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name || id)) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-all;">' + escapeHtml(String(image)) + '</div>'
                        + '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-all;">' + escapeHtml(String(status)) + (ports ? ' · ' + escapeHtml(String(ports)) : '') + '</div>'
                        + '</div>'
                        + '<div style="display:flex;gap:8px;flex-shrink:0;">'
                        + '<button type="button" data-action="docker-ctr-act" data-id="' + escapeHtml(String(id)) + '" data-op="' + escapeHtml(String(actionType)) + '" style="border:1px solid #0969da;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#0969da;">' + escapeHtml(String(actionText)) + '</button>'
                        + '<button type="button" data-action="docker-ctr-rm" data-id="' + escapeHtml(String(id)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">删除</button>'
                        + '</div>'
                        + '</div>';
                }).join('') + '</div>';

                Array.from(containersEl.querySelectorAll('button[data-action="docker-ctr-act"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        const op = btn.getAttribute('data-op') || '';
                        if (!id || !op) return;
                        const url = op === 'stop' ? '/api/docker/container/stop' : '/api/docker/container/start';
                        __postJson(url, { id: id })
                            .then(function(data) {
                                const payload = apiData(data);
                                const msg = payload && payload.message ? payload.message : '已提交';
                                if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                                window.loadDockerTabs('containers');
                            })
                            .catch(function() {
                                if (typeof window.showToast === 'function') window.showToast('操作失败', 'error');
                            });
                    });
                });

                Array.from(containersEl.querySelectorAll('button[data-action="docker-ctr-rm"]')).forEach(function(btn) {
                    btn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const id = btn.getAttribute('data-id') || '';
                        if (!id) return;
                        const ok = window.confirm('确认删除容器 ' + id + ' ?');
                        if (!ok) return;
                        __postJson('/api/docker/container/rm', { id: id, force: true })
                            .then(function(data) {
                                const payload = apiData(data);
                                const msg = payload && payload.message ? payload.message : '已提交';
                                if (typeof window.showToast === 'function') window.showToast(msg, 'success');
                                window.loadDockerTabs('containers');
                            })
                            .catch(function() {
                                if (typeof window.showToast === 'function') window.showToast('删除失败', 'error');
                            });
                    });
                });
            })
            .catch(function() {
                if (containersEl) containersEl.innerHTML = __errorHtml('加载失败（Docker 可能未安装）');
            });
    }
};

function __systemdControl(service, action) {
    const svc = String(service || '');
    const act = String(action || '');
    if (!svc || !act) return;
    if (typeof window.showTaskListener === 'function') window.showTaskListener('正在执行 ' + act + ' …');
    __postJson('/api/systemd/control', { service: svc, action: act })
        .then(function(data) {
            const payload = apiData(data);
            const taskId = payload && payload.taskId ? payload.taskId : null;
            if (!taskId || !window.TaskPoller || typeof window.TaskPoller.start !== 'function') {
                if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
                window.loadSystemdList();
                return;
            }
            if (window.__activeTaskPoller && typeof window.__activeTaskPoller.cancel === 'function') {
                window.__activeTaskPoller.cancel();
                window.__activeTaskPoller = null;
            }
            window.__activeTaskPoller = window.TaskPoller.start(taskId, {
                intervalMs: 900,
                timeoutMs: 30 * 1000,
                onUpdate: function(evt) {
                    if (!evt) return;
                    const st = evt.status;
                    if (typeof window.showTaskListener === 'function') window.showTaskListener('systemd ' + act + '：' + (st || 'running') + ' …');
                }
            });
            window.__activeTaskPoller.promise.then(function(res) {
                window.__activeTaskPoller = null;
                if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
                if (!res || !res.ok) {
                    if (typeof window.showToast === 'function') window.showToast('操作失败', 'error');
                    window.loadSystemdList();
                    return;
                }
                if (typeof window.showToast === 'function') window.showToast('操作完成', 'success');
                window.loadSystemdList();
            });
        })
        .catch(function() {
            if (typeof window.hideTaskListener === 'function') window.hideTaskListener();
            if (typeof window.showToast === 'function') window.showToast('操作失败', 'error');
        });
}

window.loadSystemdList = function() {
    const container = __setContainerHtml('systemdListContainer', __loadingHtml('加载中...'));
    fetch('/api/systemd/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const services = payload && Array.isArray(payload.services) ? payload.services : [];
            if (!services.length) {
                container.innerHTML = __emptyHtml('暂无服务数据');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + services.map(function(s) {
                const name = s.name || '-';
                const desc = s.description || '';
                const active = s.active || '';
                const sub = s.sub || '';
                const enabled = !!s.enabled;
                const isActive = String(active).toLowerCase() === 'active';
                const badgeColor = isActive ? '#2da44e' : '#cf222e';
                const badgeText = isActive ? 'active' : (active || 'inactive');
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
                    + '<div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">'
                    + '<div style="min-width:0;">'
                    + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
                    + '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(String(name)) + '</div>'
                    + '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:' + badgeColor + ';color:#fff;">' + escapeHtml(String(badgeText)) + '</span>'
                    + (enabled ? '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:#ddf4ff;color:#0969da;">enabled</span>' : '')
                    + '</div>'
                    + (desc ? '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-word;">' + escapeHtml(String(desc)) + '</div>' : '')
                    + '<div style="font-size:12px;color:#57606a;margin-top:2px;">' + escapeHtml(String(active)) + (sub ? ' (' + escapeHtml(String(sub)) + ')' : '') + '</div>'
                    + '</div>'
                    + '<div style="display:flex;gap:8px;flex-shrink:0;flex-wrap:wrap;justify-content:flex-end;">'
                    + '<button type="button" data-action="systemd" data-op="start" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #2da44e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#2da44e;">启动</button>'
                    + '<button type="button" data-action="systemd" data-op="stop" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #cf222e;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#cf222e;">停止</button>'
                    + '<button type="button" data-action="systemd" data-op="restart" data-name="' + escapeHtml(String(name)) + '" style="border:1px solid #0969da;background:#fff;border-radius:8px;padding:6px 10px;cursor:pointer;color:#0969da;">重启</button>'
                    + '</div>'
                    + '</div>'
                    + '</div>';
            }).join('') + '</div>';

            Array.from(container.querySelectorAll('button[data-action="systemd"]')).forEach(function(btn) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    const op = btn.getAttribute('data-op') || '';
                    const name = btn.getAttribute('data-name') || '';
                    if (!op || !name) return;
                    __systemdControl(name, op);
                });
            });
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

window.loadDiskList = function() {
    const container = __setContainerHtml('diskListContainer', __loadingHtml('加载中...'));
    fetch('/api/disk/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const disks = payload && Array.isArray(payload.disks) ? payload.disks : [];
            if (!disks.length) {
                container.innerHTML = __emptyHtml('暂无磁盘数据');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + disks.map(function(d) {
                const dev = d.device || '-';
                const total = d.total || '-';
                const used = d.used || '-';
                const avail = d.available || '-';
                const pct = d.use_percent || '-';
                const mp = d.mountpoint || '-';
                const fs = d.fstype || '';
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
                    + '<div style="font-weight:600;word-break:break-all;">' + escapeHtml(String(dev)) + '</div>'
                    + '<div style="font-size:12px;color:#57606a;margin-top:2px;word-break:break-all;">挂载：' + escapeHtml(String(mp)) + (fs ? ' · ' + escapeHtml(String(fs)) : '') + '</div>'
                    + '<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#57606a;margin-top:6px;">'
                    + '<span>已用 ' + escapeHtml(String(used)) + '</span>'
                    + '<span>可用 ' + escapeHtml(String(avail)) + '</span>'
                    + '<span>总量 ' + escapeHtml(String(total)) + '</span>'
                    + '<span>使用率 ' + escapeHtml(String(pct)) + '%</span>'
                    + '</div>'
                    + '</div>';
            }).join('') + '</div>';
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

window.loadNetworkList = function() {
    const container = __setContainerHtml('networkListContainer', __loadingHtml('加载中...'));
    fetch('/api/network/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            const interfaces = payload && Array.isArray(payload.interfaces) ? payload.interfaces : [];
            if (!interfaces.length) {
                container.innerHTML = __emptyHtml('暂无网络信息');
                return;
            }
            container.innerHTML = '<div style="display:flex;flex-direction:column;gap:10px;">' + interfaces.map(function(n) {
                const name = n.name || '-';
                const state = n.state || '-';
                const ipv4 = n.ipv4 || '';
                const ipv6 = n.ipv6 || '';
                const mac = n.mac || '';
                const mtu = n.mtu || '';
                const bc = n.broadcast || '';
                const up = String(state).toUpperCase() === 'UP';
                const badgeColor = up ? '#2da44e' : '#cf222e';
                return '<div style="border:1px solid #d0d7de;border-radius:10px;background:#fff;padding:12px 14px;">'
                    + '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">'
                    + '<div style="font-weight:600;">' + escapeHtml(String(name)) + '</div>'
                    + '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:' + badgeColor + ';color:#fff;">' + escapeHtml(String(state)) + '</span>'
                    + (mtu ? '<span style="font-size:11px;padding:2px 8px;border-radius:999px;background:#f6f8fa;color:#57606a;">MTU ' + escapeHtml(String(mtu)) + '</span>' : '')
                    + '</div>'
                    + '<div style="font-size:12px;color:#57606a;margin-top:6px;display:flex;flex-direction:column;gap:4px;">'
                    + (ipv4 ? '<div>IPv4：' + escapeHtml(String(ipv4)) + '</div>' : '')
                    + (ipv6 ? '<div>IPv6：' + escapeHtml(String(ipv6)) + '</div>' : '')
                    + (mac ? '<div>MAC：' + escapeHtml(String(mac)) + '</div>' : '')
                    + (bc ? '<div>Broadcast：' + escapeHtml(String(bc)) + '</div>' : '')
                    + '</div>'
                    + '</div>';
            }).join('') + '</div>';
        })
        .catch(function() {
            if (container) container.innerHTML = __errorHtml('加载失败（可能不支持此系统）');
        });
};

window.closeGitModal = function() { Drawer.close('gitModal'); };
window.openGitModal = function() { Drawer.open('gitModal'); loadGitList(); };
window.openProcessModal = function() { Drawer.open('processModal'); loadProcessList(); };
window.openSystemPackageModal = function() { Drawer.open('systemPackageModal'); loadSystemPackageList(); };
window.openPipModal = function() { Drawer.open('pipModal'); loadPipList(); };
window.openNpmModal = function() { Drawer.open('npmModal'); loadNpmList(); };
window.openDockerModal = function() { Drawer.open('dockerModal'); loadDockerTabs(); };
window.openSystemdModal = function() { Drawer.open('systemdModal'); loadSystemdList(); };
window.openDiskModal = function() { Drawer.open('diskModal'); loadDiskList(); };
window.openNetworkModal = function() { Drawer.open('networkModal'); loadNetworkList(); };

// GPU显卡信息
window.loadGpuInfo = function() {
    const container = document.getElementById('gpuInfoContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/gpu/info', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && container) {
                const p = payload.parsed || {};
                const raw = payload.raw || '';
                const gpuName = p.name || 'Unknown GPU';
                const memoryUsed = p.memory_used || 0;
                const memoryTotal = p.memory_total || 1;
                const memoryPercent = p.memory_percent || 0;
                const temp = p.temperature || 0;
                const powerUsed = p.power_used || 0;
                const powerTotal = p.power_total || 260;
                const util = p.utilization || 0;
                const driver = p.driver || 'Unknown';
                const cuda = p.cuda || 'Unknown';
                
                const memoryBar = renderProgressBar(memoryUsed, memoryTotal, 'MiB');
                const powerBar = renderProgressBar(powerUsed, powerTotal, 'W');
                const utilBar = renderProgressBar(util, 100, '%');
                const rawHtml = raw
                    ? '<div style="margin-top:12px;">' +
                        '<div style="font-size:13px;color:#666;margin-bottom:6px;">nvidia-smi 原始输出</div>' +
                        '<pre style="margin:0;white-space:pre;overflow:auto;background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px;line-height:1.5;">' +
                        escapeHtml(String(raw)) +
                        '</pre>' +
                    '</div>'
                    : '';
                
                container.innerHTML = '<div style="background:#f6f8fa;padding:12px 16px;border-radius:8px;margin-bottom:12px;"><div style="font-size:18px;font-weight:600;margin-bottom:4px;">' + escapeHtml(gpuName) + '</div><div style="font-size:12px;color:#666;">驱动: ' + escapeHtml(driver) + ' | CUDA: ' + escapeHtml(cuda) + '</div></div><div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:16px;"><div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:' + (temp > 70 ? '#cf222e' : '#24292f') + '">' + temp + '°C</div><div style="font-size:12px;color:#666;margin-top:4px;">温度</div></div><div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px;text-align:center;"><div style="font-size:24px;font-weight:600;color:#24292f">' + util + '%</div><div style="font-size:12px;color:#666;margin-top:4px;">利用率</div></div></div><div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;"><span>显存 ' + memoryUsed + ' / ' + memoryTotal + ' MiB</span><span>' + memoryPercent + '%</span></div><div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">' + memoryBar + '</div></div><div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;"><span>功耗 ' + powerUsed + ' / ' + powerTotal + ' W</span><span>' + Math.round(powerUsed / powerTotal * 100) + '%</span></div><div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">' + powerBar + '</div></div><div style="margin-bottom:12px;"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;"><span>GPU 利用率</span><span>' + util + '%</span></div><div style="height:8px;background:#e1e4e8;border-radius:4px;overflow:hidden;">' + utilBar + '</div></div>' + rawHtml;
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败（可能无GPU或nvidia-smi未安装）</div>';
        });
};

function renderProgressBar(current, total, unit) {
    const percent = Math.min(100, Math.max(0, Math.round(current / total * 100)));
    const color = percent > 80 ? '#cf222e' : percent > 50 ? '#d29922' : '#2da44e';
    return '<div style="width:' + percent + '%;height:100%;background:' + color + ';transition:width 0.3s;"></div>';
}

window.openGpuModal = function() { Drawer.open('gpuModal'); loadGpuInfo(); };

// Ollama模型
window.loadOllamaModels = function() {
    const container = document.getElementById('ollamaModelsContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    fetch('/api/ollama/models', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (payload && container) {
                const models = payload.models || [];
                if (models.length === 0) {
                    container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">暂无模型，请先拉取模型</div>';
                    return;
                }
                container.innerHTML = '<div style="display:flex;flex-direction:column;gap:8px;">' +
                    models.map(function(m) {
                        const name = m.name || 'Unknown';
                        const size = m.size || 0;
                        const sizeFormatted = formatSize(size);
                        const isReasoning = name.toLowerCase().includes('qwq') || name.toLowerCase().includes('r1') || name.toLowerCase().includes('reasoning');
                        return '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;"><div style="flex:1;min-width:0;"><div style="font-weight:500;display:flex;align-items:center;gap:8px;">' + (isReasoning ? '<span style="font-size:12px;background:#ddf4ff;color:#0969da;padding:2px 6px;border-radius:4px;">推理</span>' : '') + '<span>' + escapeHtml(name) + '</span></div><div style="font-size:12px;color:#666;margin-top:2px;">' + sizeFormatted + '</div></div><span style="color:#07c160;font-size:18px;">✓</span></div>';
                    }).join('') + '</div>';
            }
        })
        .catch(function() {
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败（Ollama可能未运行）</div>';
        });
};

function formatSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

window.openOllamaModal = function() { Drawer.open('ollamaModal'); loadOllamaModels(); };

// OpenClaw配置
window.loadOpenclawConfig = function() {
    const container = document.getElementById('openclawConfigContainer');
    if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#666;">🔄 加载中...</div>';
    
    fetch('/api/openclaw/status', { headers: authHeaders() })
        .then(r => r.json())
        .then(data => {
            const payload = apiData(data);
            if (!payload || !container) return;
            
            let html = '';
            
            // ========== 概览卡片 ==========
            const ov = payload.overview || {};
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">概览</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">版本</span><span style="font-weight:500;font-size:14px;">' + escapeHtml(ov.version || '-') + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">系统</span><span style="font-size:12px;color:#57606a;max-width:200px;text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(ov.os || '-') + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">Node</span><span style="font-weight:500;font-size:14px;">' + escapeHtml(ov.node || '-') + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">仪表板</span><a href="' + escapeHtml(ov.dashboard || '#') + '" target="_blank" style="color:#0969da;font-size:13px;">打开 ↗</a></div>';
            html += '<div style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">频道</span><span style="font-size:13px;">' + escapeHtml(ov.channel || '-') + '</span></div>';
            html += '</div></div>';
            
            // ========== Gateway卡片 ==========
            const gw = payload.gateway || {};
            const gwStatus = gw.service_running ? '🟢 运行中' : '🔴 已停止';
            const gwPortClass = gw.port_used ? 'color:#cf222e;' : 'color:#2da44e;';
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Gateway</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">状态</span><span>' + gwStatus + '</span></div>';
            html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">端口</span><span style="' + gwPortClass + 'font-size:14px;">' + (gw.port || '-') + (gw.port_used ? ' (被占用)' : '') + '</span></div>';
            if (gw.latency_ms !== null) {
                html += '<div style="padding:10px 12px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">延迟</span><span>' + gw.latency_ms + 'ms</span></div>';
            }
            if (gw.service_pid) {
                html += '<div style="padding:10px 12px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#666;font-size:13px;">PID</span><span style="font-family:ui-monospace;font-size:13px;">' + gw.service_pid + '</span></div>';
            }
            html += '</div></div>';
            
            // ========== Agents卡片 ==========
            const agents = payload.agents || [];
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Agents (' + agents.length + ')</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            agents.forEach(function(agent, idx) {
                const statusColor = agent.status === 'pending' ? '#cf222e' : '#2da44e';
                html += '<div style="padding:10px 12px;' + (idx < agents.length - 1 ? 'border-bottom:1px solid #eee;' : '') + '">';
                html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">';
                html += '<span style="font-weight:500;font-size:14px;">' + escapeHtml(agent.name || agent.id) + '</span>';
                html += '<span style="font-size:11px;padding:1px 6px;border-radius:999px;background:#ffebe9;color:#cf222e;">' + (agent.sessions || 0) + ' 会话</span>';
                html += '</div>';
                html += '<div style="font-size:12px;color:#57606a;">' + (agent.active_ago || '-') + '</div>';
                html += '</div>';
            });
            html += '</div></div>';
            
            // ========== Channels卡片 ==========
            const channels = payload.channels || {};
            const channelNames = Object.keys(channels);
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">Channels</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            channelNames.forEach(function(ch, idx) {
                const cfg = channels[ch];
                const statusIcon = cfg.status === 'ok' ? '🟢' : (cfg.enabled ? '🟡' : '🔴');
                const statusText = cfg.status === 'ok' ? '已连接' : (cfg.enabled ? '待配置' : '已禁用');
                html += '<div style="padding:10px 12px;' + (idx < channelNames.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;justify-content:space-between;align-items:center;">';
                html += '<div style="display:flex;align-items:center;gap:8px;">';
                html += '<span>' + statusIcon + '</span>';
                html += '<span style="font-weight:500;font-size:14px;text-transform:capitalize;">' + escapeHtml(ch) + '</span>';
                html += '</div>';
                html += '<div style="text-align:right;">';
                html += '<div style="font-size:13px;">' + statusText + '</div>';
                if (cfg.accounts_total > 0) {
                    html += '<div style="font-size:11px;color:#57606a;">' + cfg.accounts_ok + '/' + cfg.accounts_total + ' 账户</div>';
                }
                html += '</div>';
                html += '</div>';
            });
            html += '</div></div>';
            
            // ========== 诊断卡片 ==========
            const diag = payload.diagnosis || {};
            const warnings = diag.warnings || [];
            const checks = diag.checks || {};
            
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;color:#666;margin-bottom:8px;padding-left:4px;">诊断</div>';
            html += '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">';
            
            // Warnings
            if (warnings.length > 0) {
                warnings.forEach(function(w, idx) {
                    html += '<div style="padding:10px 12px;' + (idx < warnings.length - 1 ? 'border-bottom:1px solid #eee;' : '') + 'display:flex;align-items:center;gap:8px;">';
                    html += '<span>⚠️</span>';
                    html += '<span style="font-size:13px;">' + escapeHtml(w.message) + '</span>';
                    html += '</div>';
                });
            } else {
                html += '<div style="padding:10px 12px;display:flex;align-items:center;gap:8px;color:#2da44e;">';
                html += '<span>✅</span>';
                html += '<span style="font-size:13px;">无警告</span>';
                html += '</div>';
            }
            
            // Skills check
            const skills = checks.skills || {};
            if (skills.eligible !== undefined) {
                html += '<div style="padding:10px 12px;border-top:1px solid #eee;display:flex;justify-content:space-between;align-items:center;">';
                html += '<span style="color:#666;font-size:13px;">Skills</span>';
                html += '<span>' + skills.eligible + ' 个已安装</span>';
                html += '</div>';
            }
            
            html += '</div></div>';
            
            container.innerHTML = html;
        })
        .catch(function(err) {
            console.error(err);
            if (container) container.innerHTML = '<div style="text-align:center;padding:40px;color:#cf222e;">加载失败</div>';
        });
};
window.openOpenclawModal = function() { Drawer.open('openclawModal'); loadOpenclawConfig(); };

window.__gitCommitListTestApi = {
    commitShortId: __gitCommitShortId,
    truncate: __gitTruncate,
    commitUrl: __gitCommitUrl,
    prepareCommitNavigation: __gitPrepareCommitNavigation,
    nextActiveIndex: __gitNextActiveIndex,
    scrollKey: __gitScrollKey,
    saveScroll: __gitSaveScroll,
    loadScroll: __gitLoadScroll,
    emptyHtml: __gitEmptyHtml,
    errorBannerHtml: __gitErrorBannerHtml,
    commitItemHtml: __gitCommitItemHtml,
    dirtyLineHtml: __gitDirtyLineHtml
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.__gitCommitListTestApi;
}

if (window && typeof window.addEventListener === 'function') {
    window.addEventListener('pageshow', function() {
        const repoPath = __gitConsumeReturnFlag();
        if (!repoPath) return;
        try {
            Drawer.open('gitModal');
        } catch (e) {
            return;
        }
        try {
            window.loadGitList(repoPath);
        } catch (e) {
            return;
        }
    });
}
