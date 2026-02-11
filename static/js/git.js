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
        '.git-link-group { display:inline-flex; align-items:stretch; border:1px solid #d0d7de; border-radius:999px; overflow:hidden; }' +
        '.git-link-btn { border:0; background:#f6f8fa; color:#0969da; padding:4px 10px; cursor:pointer; font-size:12px; line-height:18px; }' +
        '.git-link-btn + .git-link-btn { border-left:1px solid #d0d7de; }' +
        '.git-link-btn:hover { background:#ddf4ff; }' +
        '.git-diff-btn { border:1px solid #d0d7de; background:#fff; border-radius:6px; padding:4px 10px; cursor:pointer; font-size:12px; }' +
        '.git-diff-btn:hover { background:#f6f8fa; }' +
        '.git-pull-btn { border:1px solid #d0d7de; background:#fff; border-radius:6px; padding:4px 10px; cursor:pointer; font-size:12px; }' +
        '.git-pull-btn:hover { background:#f6f8fa; }' +
        '.git-pull-btn[disabled] { opacity:0.65; cursor:not-allowed; }' +
        '.git-push-btn { border:1px solid #d0d7de; background:#fff; border-radius:6px; padding:4px 10px; cursor:pointer; font-size:12px; }' +
        '.git-push-btn:hover { background:#f6f8fa; }' +
        '.git-push-btn[disabled] { opacity:0.65; cursor:not-allowed; }' +
        '.git-diffstat-table { width:100%; border-collapse:collapse; font-size:12px; }' +
        '.git-diffstat-table th, .git-diffstat-table td { padding:8px 10px; border-bottom:1px solid #eee; vertical-align:top; }' +
        '.git-diffstat-table th { background:#f6f8fa; color:#57606a; font-weight:600; text-align:left; }' +
        '.git-diffstat-path { font-family: ui-monospace, monospace; word-break:break-all; }' +
        '.git-diffstat-num { font-family: ui-monospace, monospace; text-align:right; }' +
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
        ? '<button type="button" class="git-diff-btn" id="gitDiffBtn">diff</button><button type="button" class="git-pull-btn" id="gitPullBtn">拉取</button><button type="button" class="git-push-btn" id="gitPushBtn">推送变更</button>'
        : '<button type="button" class="git-pull-btn" id="gitPullBtn">拉取</button>';
    const hint = hasChanges ? '<span id="gitPushHint" style="font-size:12px;color:#57606a;"></span>' : '';
    return '<div id="gitRepoDirtyLine" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px;color:' + color + ';margin-top:4px;">' +
        '<span>' + escapeHtml(statusText || '') + escapeHtml(changeInfo || '') + '</span>' +
        btn +
        hint +
        '</div>';
}

function __gitBindPullButton(repoPath) {
    const btn = document.getElementById('gitPullBtn');
    if (!btn) return;
    btn.addEventListener('click', function() {
        if (btn.disabled) return;
        btn.disabled = true;
        const prevText = btn.textContent;
        btn.textContent = '拉取中…';
        const headers = authHeaders ? (authHeaders() || {}) : {};
        headers['Content-Type'] = 'application/json';
        fetch('/api/git/pull', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ path: String(repoPath || '') })
        })
            .then(function(r) { return r.json(); })
            .then(function(resp) {
                const payload = apiData(resp);
                if (!payload) {
                    const msg = resp && resp.error && resp.error.message ? resp.error.message : '拉取失败';
                    throw new Error(msg);
                }
                if (typeof showToast === 'function') showToast(payload.message || '拉取完成');
                window.loadGitList(repoPath);
            })
            .catch(function(e) {
                const msg = e && e.message ? e.message : '拉取失败';
                if (typeof showToast === 'function') showToast(msg);
            })
            .finally(function() {
                btn.disabled = false;
                btn.textContent = prevText;
            });
    });
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

// 直接执行 Diff：打开新窗口显示 diff
function __gitDoDiff(repoPath) {
    const url = '/git/diff?repoPath=' + encodeURIComponent(String(repoPath || ''));
    
    // 显示 loading
    if (typeof window.showTaskListener === 'function') {
        window.showTaskListener('正在加载 diff…');
    }
    window.open(url, '_blank');
    
    // 延迟隐藏
    setTimeout(function() {
        if (typeof window.hideTaskListener === 'function') {
            window.hideTaskListener();
        }
    }, 1000);
}

// 直接执行 Pull
function __gitDoPull(repoPath) {
    const headers = authHeaders ? (authHeaders() || {}) : {};
    headers['Content-Type'] = 'application/json';
    
    // 显示 loading
    if (typeof window.showTaskListener === 'function') {
        window.showTaskListener('正在拉取…');
    }
    
    fetch('/api/git/pull', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ path: String(repoPath || '') })
    })
        .then(function(r) { return r.json(); })
        .then(function(resp) {
            const payload = apiData(resp);
            if (typeof window.hideTaskListener === 'function') {
                window.hideTaskListener();
            }
            
            if (!payload) {
                const msg = resp && resp.error && resp.error.message ? resp.error.message : '拉取失败';
                throw new Error(msg);
            }
            if (typeof showToast === 'function') showToast(payload.message || '拉取完成');
            window.loadGitList(repoPath);
        })
        .catch(function(e) {
            if (typeof window.hideTaskListener === 'function') {
                window.hideTaskListener();
            }
            const msg = e && e.message ? e.message : '拉取失败';
            if (typeof showToast === 'function') showToast(msg);
        });
}

// 直接执行 Push
function __gitDoPush(repoPath) {
    const headers = authHeaders ? (authHeaders() || {}) : {};
    headers['Content-Type'] = 'application/json';
    
    // 显示 loading
    if (typeof window.showTaskListener === 'function') {
        window.showTaskListener('正在推送…');
    }
    
    fetch('/api/git/push-changes', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ path: String(repoPath || '') })
    })
        .then(function(r) { return r.json(); })
        .then(function(resp) {
            const payload = apiData(resp);
            if (typeof window.hideTaskListener === 'function') {
                window.hideTaskListener();
            }
            
            if (!payload) {
                const msg = resp && resp.error && resp.error.message ? resp.error.message : '推送失败';
                throw new Error(msg);
            }
            if (payload.status === 'clean') {
                if (typeof showToast === 'function') showToast('当前没有可提交的变更');
                return;
            }
            if (payload.pushed) {
                if (typeof showToast === 'function') showToast('已推送：' + (payload.commit_msg || ''));
                window.loadGitList(repoPath);
                return;
            }
            const msg = payload.message || '推送失败';
            throw new Error(msg);
        })
        .catch(function(e) {
            if (typeof window.hideTaskListener === 'function') {
                window.hideTaskListener();
            }
            const msg = e && e.message ? e.message : '推送失败';
            if (typeof showToast === 'function') showToast(msg);
        });
}

function __gitRenderDiffFileTable(container, rows, repoPath, meta) {
    if (!container) return;
    const list = Array.isArray(rows) ? rows : [];
    const hasChanges = !!(meta && meta.has_changes);
    const changeInfo = meta && meta.change_info ? String(meta.change_info) : '';
    const statusHtml = hasChanges
        ? '<span style="font-size:12px;color:#e3b341;">⚠️ Dirty</span>'
        : '<span style="font-size:12px;color:#2da44e;">✓ Clean</span>';
    const infoHtml = changeInfo ? '<span style="font-size:11px;color:#666;">' + escapeHtml(changeInfo) + '</span>' : '';
    if (!list.length) {
        container.innerHTML = '<div style="padding:10px 12px;color:#57606a;font-size:12px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">' +
            statusHtml +
            infoHtml +
            '<span>暂无变更</span>' +
            '</div>';
        return;
    }

    const header = '<div style="margin:8px 0 6px;padding-left:4px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">' +
        statusHtml +
        infoHtml +
        '</div>';
    const table = '<div style="background:#fff;border:1px solid #d0d7de;border-radius:8px;overflow:hidden;">' +
        '<table class="git-diffstat-table">' +
        '<thead><tr><th style="width:70%;">文件</th><th class="git-diffstat-num" style="width:15%;">+</th><th class="git-diffstat-num" style="width:15%;">-</th></tr></thead>' +
        '<tbody>' +
        list.map(function(r, idx) {
            const path = String((r && r.path) || '-');
            const pathEsc = escapeHtml(path);
            const add = (r && (r.added === null || r.added === undefined)) ? '—' : String(r.added || 0);
            const del = (r && (r.deleted === null || r.deleted === undefined)) ? '—' : String(r.deleted || 0);
            const trStyle = idx < list.length - 1 ? '' : ' style="border-bottom:0;"';
            const rowStyle = 'cursor:pointer;' + (idx < list.length - 1 ? '' : '');
            return '<tr onclick="__gitOpenFileDiff(\'' + escapeHtml(repoPath) + '\', \'' + pathEsc + '\');" style="' + rowStyle + '">' +
                '<td class="git-diffstat-path" title="' + pathEsc + '" style="color:#0969da;">' + pathEsc + '</td>' +
                '<td class="git-diffstat-num" style="color:#2da44e;"' + trStyle + '>' + escapeHtml(add) + '</td>' +
                '<td class="git-diffstat-num" style="color:#cf222e;"' + trStyle + '>' + escapeHtml(del) + '</td>' +
                '</tr>';
        }).join('') +
        '</tbody></table></div>';

    container.innerHTML = header + table;
}

// 打开单个文件的 diff
function __gitOpenFileDiff(repoPath, filePath) {
    const url = '/git/diff?repoPath=' + encodeURIComponent(repoPath) + '&file=' + encodeURIComponent(filePath);
    window.open(url, '_blank');
}

function __gitLoadDiffFileList(repoPath, meta) {
    const el = document.getElementById('gitDiffFilesBox');
    if (!el) return;
    el.innerHTML = '<div style="padding:10px 12px;color:#57606a;font-size:12px;">加载变更…</div>';
    fetch('/api/git/diff-numstat?path=' + encodeURIComponent(String(repoPath || '')), { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(resp) {
            const payload = apiData(resp);
            if (!payload) {
                const msg = resp && resp.error && resp.error.message ? resp.error.message : '加载失败';
                throw new Error(msg);
            }
            __gitRenderDiffFileTable(el, payload.files || [], repoPath, meta);
        })
        .catch(function() {
            el.innerHTML = '<div style="padding:10px 12px;color:#cf222e;font-size:12px;">加载失败</div>';
        });
}

function __gitSetDrawerTitle(html) {
    const el = document.getElementById('gitDrawerTitle');
    if (!el) return;
    el.innerHTML = html || '🔀 Git管理';
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
    __gitSetDrawerTitle('🔀 Git管理');
    
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
                const repoName = (repo.name || specificRepoPath).replace(/\.git$/, '') + '.git';
                const repoPathArg = escapeHtml(JSON.stringify(String(specificRepoPath || '')));
                const repoStatus = repo.status || {};
                const hasChanges = repoStatus.has_changes || false;
                let changeInfo = '';
                if (hasChanges) {
                    const changes = [];
                    if (repoStatus.modified) changes.push((repoStatus.modified || 0) + ' modified');
                    if (repoStatus.added) changes.push((repoStatus.added || 0) + ' added');
                    if (repoStatus.deleted) changes.push((repoStatus.deleted || 0) + ' deleted');
                    if (repoStatus.untracked) changes.push((repoStatus.untracked || 0) + ' untracked');
                    changeInfo = changes.length ? ' · ' + changes.join(', ') : '';
                }

                const titleHtml = '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
                    '<span style="font-weight:600;word-break:break-all;font-size:15px;">' + escapeHtml(repoName) + '</span>' +
                    '<div class="git-link-group">' +
                    '<button type="button" class="git-link-btn" onclick="__gitDoDiff(' + repoPathArg + ');">diff</button>' +
                    '<button type="button" class="git-link-btn" onclick="__gitDoPull(' + repoPathArg + ');">pull</button>' +
                    '<button type="button" class="git-link-btn" onclick="__gitDoPush(' + repoPathArg + ');">push</button>' +
                    '</div>' +
                    '</div>';
                __gitSetDrawerTitle(titleHtml);

                const headerHtml = '<div style="padding:12px 12px 8px;"><div id="gitDiffFilesBox"></div></div>';
                const diffMeta = { has_changes: hasChanges, change_info: changeInfo };

                __gitMountCommitList(container, specificRepoPath, { html: headerHtml, branch: '' });
                __gitLoadDiffFileList(specificRepoPath, diffMeta);
            })
            .catch(function() {
                if (container) container.innerHTML = __gitErrorBannerHtml('加载失败');
            });
        return;
    }

    fetch('/api/git/list', { headers: authHeaders() })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            const payload = apiData(data);
            if (!container) return;
            if (!payload || !payload.repos || payload.repos.length === 0) {
                container.innerHTML = __gitListCss() + '<div class="git-shell">' + __gitEmptyHtml() + '</div>';
                return;
            }

            window.__gitRepos = payload.repos || [];
            const css = __gitListCss();
            const html = css + '<div class="git-shell"><div class="git-top"><span style="font-size:12px;color:#57606a;">仓库</span><select id="gitRepoSelect" class="git-select"></select></div><div id="gitRepoPanel"></div></div>';
            container.innerHTML = html;

            const repos = window.__gitRepos || [];
            const select = document.getElementById('gitRepoSelect');
            const panelEl = document.getElementById('gitRepoPanel');

            function renderRepo(repo) {
                if (!repo || !panelEl) return;
                const repoPath = repo.path || '';
                const repoName = (repo.name || repoPath).replace(/\.git$/, '') + '.git';
                const repoPathArg = escapeHtml(JSON.stringify(String(repoPath || '')));
                const hasChanges = !!(repo.status && repo.status.has_changes);
                const repoStatus = repo.status || {};
                let changeInfo = '';
                if (hasChanges) {
                    const changes = [];
                    if (repoStatus.modified) changes.push((repoStatus.modified || 0) + ' modified');
                    if (repoStatus.added) changes.push((repoStatus.added || 0) + ' added');
                    if (repoStatus.deleted) changes.push((repoStatus.deleted || 0) + ' deleted');
                    if (repoStatus.untracked) changes.push((repoStatus.untracked || 0) + ' untracked');
                    changeInfo = changes.length ? ' · ' + changes.join(', ') : '';
                }

                const titleHtml = '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' +
                    '<span style="font-weight:600;word-break:break-all;font-size:15px;">' + escapeHtml(repoName) + '</span>' +
                    '<div class="git-link-group">' +
                    '<button type="button" class="git-link-btn" onclick="__gitDoDiff(' + repoPathArg + ');">diff</button>' +
                    '<button type="button" class="git-link-btn" onclick="__gitDoPull(' + repoPathArg + ');">pull</button>' +
                    '<button type="button" class="git-link-btn" onclick="__gitDoPush(' + repoPathArg + ');">push</button>' +
                    '</div>' +
                    '</div>';
                __gitSetDrawerTitle(titleHtml);

                const headerHtml = '<div style="padding:12px 12px 8px;"><div id="gitDiffFilesBox"></div></div>';
                const diffMeta = { has_changes: hasChanges, change_info: changeInfo };

                __gitMountCommitList(panelEl, repoPath, { html: headerHtml, branch: '' });
                __gitLoadDiffFileList(repoPath, diffMeta);
            }

            repos.forEach(function(r) {
                const opt = document.createElement('option');
                opt.value = String(r.id);
                opt.textContent = r.name + ' (' + (r.status && r.status.branch ? r.status.branch : '-') + ')';
                if (select) select.appendChild(opt);
            });

            if (select) {
                select.addEventListener('change', function() {
                    const rid = this.value;
                    const repo = repos.find(function(r) { return String(r.id) === String(rid); });
                    renderRepo(repo);
                });
            }

            if (repos.length > 0) renderRepo(repos[0]);
        })
        .catch(function() {
            if (!container) return;
            container.innerHTML = __gitErrorBannerHtml('加载失败');
            const btn = document.getElementById('gitRetryBtn');
            if (btn) btn.addEventListener('click', function() { window.loadGitList(); });
        });
};

window.closeGitModal = function() { Drawer.close('gitModal'); };
window.openGitModal = function() { Drawer.open('gitModal'); window.loadGitList(); };

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
