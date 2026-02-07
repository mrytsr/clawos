// ============ 终端功能模块 ============

let term = null;
let fitAddon = null;
let socket = null;
let termInitialized = false;
let isTermOpen = false;
let ctrlMode = false;
let altMode = false;

function focusTerminal() {
    if (term && typeof term.focus === 'function') term.focus();
    const container = document.getElementById('terminal-container');
    if (!container || typeof container.querySelector !== 'function') return;
    const ta = container.querySelector('textarea');
    if (ta && typeof ta.focus === 'function') {
        try {
            ta.focus({ preventScroll: true });
        } catch (e) {
            ta.focus();
        }
    }
}

function sendToTerminal(input) {
    if (!input) return;
    if (socket && socket.connected) {
        socket.emit('input', { input: input });
    }
}

function setCtrlAreaVisible(visible) {
    const area = document.getElementById('ctrlKeysArea');
    if (!area) return;
    area.style.display = visible ? 'flex' : 'none';
}

function syncKeyButtonState(key, active, el) {
    const btn = el || null;
    if (btn && btn.classList) {
        if (active) btn.classList.add('active');
        else btn.classList.remove('active');
    }
}

function stopBtnEvent(e) {
    if (!e) return;
    if (typeof e.preventDefault === 'function') e.preventDefault();
    if (typeof e.stopPropagation === 'function') e.stopPropagation();
    const t = e.currentTarget;
    if (t && typeof t.blur === 'function') t.blur();
}

function keySeq(key) {
    if (key === 'tab') return '\t';
    if (key === 'esc') return '\x1b';
    if (key === 'enter') return '\r';
    if (key === 'up') return '\x1b[A';
    if (key === 'down') return '\x1b[B';
    if (key === 'backspace') return '\x7f';
    return '';
}

function handleKeyBtn(e, key) {
    stopBtnEvent(e);
    if (key === 'ctrl') {
        ctrlMode = !ctrlMode;
        if (ctrlMode && altMode) altMode = false;
        syncKeyButtonState('ctrl', ctrlMode, e && e.currentTarget);
        setCtrlAreaVisible(ctrlMode);
        focusTerminal();
        return false;
    }
    if (key === 'alt') {
        altMode = !altMode;
        if (altMode && ctrlMode) {
            ctrlMode = false;
            setCtrlAreaVisible(false);
        }
        syncKeyButtonState('alt', altMode, e && e.currentTarget);
        focusTerminal();
        return false;
    }

    const seq = keySeq(key);
    if (seq) sendToTerminal(seq);
    focusTerminal();
    return false;
}

function handleCtrlBtn(e, keyChar) {
    stopBtnEvent(e);
    const c = String(keyChar || '').toLowerCase();
    if (c.length !== 1) {
        focusTerminal();
        return false;
    }
    const code = c.charCodeAt(0);
    if (code < 97 || code > 122) {
        focusTerminal();
        return false;
    }
    const ctrlCode = code - 96;
    sendToTerminal(String.fromCharCode(ctrlCode));
    focusTerminal();
    return false;
}

function openTerminal(path, isDir) {
    closeMenuModal();
    if (typeof window !== 'undefined' && window.SERVER_IS_WINDOWS) {
        showToast('服务端环境不支持 Web 终端（需要 Linux PTY/termios）', 'warning');
        return;
    }
    isTermOpen = true;
    
    // 计算路径
    let termPath = '/root/.openclaw/workspace';
    if (path) {
        if (isDir) {
            termPath = '/root/.openclaw/workspace/' + path;
        } else {
            const lastSlash = path.lastIndexOf('/');
            termPath = lastSlash > 0 ? '/root/.openclaw/workspace/' + path.substring(0, lastSlash) : '/root/.openclaw/workspace';
        }
    }
    
    const pathEl = document.getElementById('termPath');
    if (pathEl) pathEl.textContent = termPath;
    
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    
    if (drawer) drawer.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
    
    if (!termInitialized) {
        initTerminal(termPath);
        termInitialized = true;
    } else if (socket) {
        socket.disconnect();
        socket.connect();
    }
    
    setTimeout(() => {
        if (fitAddon) {
            fitAddon.fit();
            if (socket && socket.connected) {
                socket.emit('resize', { cols: term.cols, rows: term.rows });
            }
        }
        focusTerminal();
    }, 300);
}

function initTerminal(cwd) {
    term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: 'Menlo, Monaco, "Courier New", monospace',
        theme: { background: '#000000' }
    });
    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(document.getElementById('terminal-container'));
    
    socket = io('/term', { reconnection: true, reconnectionAttempts: 5, reconnectionDelay: 1000 });
    
    socket.on('connect', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[32m*** 已连接 ***\x1b[0m\r\n');
        }
        socket.emit('create_terminal', { cwd: cwd });
        fitAddon.fit();
        socket.emit('resize', { cols: term.cols, rows: term.rows });
    });

    socket.on('output', (data) => {
        if (isTermOpen) {
            term.write(data.data);
        }
    });

    socket.on('disconnect', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[33m*** 连接中... ***\x1b[0m\r\n');
        }
    });

    socket.on('connect_error', () => {
        if (isTermOpen) {
            term.write('\r\n\x1b[31m*** 连接失败 ***\x1b[0m\r\n');
        }
    });

    term.onData((data) => {
        if (socket && socket.connected) {
            socket.emit('input', { input: data });
        }
    });
    
    term.onResize((size) => {
        if (socket && socket.connected) {
            socket.emit('resize', { cols: size.cols, rows: size.rows });
        }
    });
    
    window.addEventListener('resize', () => {
        const drawerEl = document.getElementById('terminalDrawer');
        if (fitAddon && drawerEl && drawerEl.classList.contains('open')) {
            fitAddon.fit();
            if (socket && socket.connected) {
                socket.emit('resize', { cols: term.cols, rows: term.rows });
            }
        }
    });
}

function closeTerminal() {
    isTermOpen = false;
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    if (socket) {
        socket.disconnect();
    }
}

// 导出
window.openTerminal = openTerminal;
window.closeTerminal = closeTerminal;
window.termInitialized = termInitialized;
window.handleKeyBtn = handleKeyBtn;
window.handleCtrlBtn = handleCtrlBtn;
