// ============ 终端功能模块 ============

let term = null;
let fitAddon = null;
let socket = null;
let termInitialized = false;
let isTermOpen = false;
let ctrlMode = false;
let altMode = false;
let _vvBound = false;

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

function syncModifierButtons() {
    const drawer = document.getElementById('terminalDrawer');
    if (!drawer || typeof drawer.querySelectorAll !== 'function') return;
    const btns = drawer.querySelectorAll('.terminal-keyboard [data-mod]');
    btns.forEach((b) => {
        const mod = b.getAttribute('data-mod');
        const active = (mod === 'ctrl' && ctrlMode) || (mod === 'alt' && altMode);
        if (active) b.classList.add('active');
        else b.classList.remove('active');
    });
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
    if (key === 'left') return '\x1b[D';
    if (key === 'right') return '\x1b[C';
    if (key === 'home') return '\x1b[H';
    if (key === 'end') return '\x1b[F';
    if (key === 'pgup') return '\x1b[5~';
    if (key === 'pgdn') return '\x1b[6~';
    if (key === 'slash') return '/';
    if (key === 'dash') return '-';
    if (key === 'backspace') return '\x7f';
    return '';
}

function applyModifiersToData(data) {
    if (!data) return '';
    const first = data[0];
    const rest = data.length > 1 ? data.slice(1) : '';

    let out = data;
    if (ctrlMode) {
        const c = String(first).toLowerCase();
        const code = c.charCodeAt(0);
        if (code >= 97 && code <= 122) {
            out = String.fromCharCode(code - 96) + rest;
        } else {
            out = data;
        }
        ctrlMode = false;
        altMode = false;
        syncModifierButtons();
        return out;
    }

    if (altMode) {
        out = '\x1b' + data;
        ctrlMode = false;
        altMode = false;
        syncModifierButtons();
        return out;
    }

    return out;
}

function handleKeyBtn(e, key) {
    stopBtnEvent(e);
    if (key === 'ctrl') {
        ctrlMode = !ctrlMode;
        if (ctrlMode && altMode) altMode = false;
        syncModifierButtons();
        focusTerminal();
        return false;
    }
    if (key === 'alt') {
        altMode = !altMode;
        if (altMode && ctrlMode) ctrlMode = false;
        syncModifierButtons();
        focusTerminal();
        return false;
    }

    const seq = keySeq(key);
    if (seq) sendToTerminal(seq);
    focusTerminal();
    return false;
}

function updateTerminalDrawerLayout() {
    const drawer = document.getElementById('terminalDrawer');
    if (!drawer) return;

    const vv = window.visualViewport;
    if (vv) {
        const overlap = Math.max(0, Math.round(window.innerHeight - vv.height - vv.offsetTop));
        drawer.style.bottom = overlap ? (String(overlap) + 'px') : '';
        const desired = Math.max(240, Math.round(vv.height * 0.8));
        drawer.style.height = String(desired) + 'px';
        drawer.style.maxHeight = String(desired) + 'px';
    } else {
        drawer.style.bottom = '';
        drawer.style.height = '';
        drawer.style.maxHeight = '';
    }
}

function openTerminal(path, isDir) {
    closeMenuModal();
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
    } else if (socket && !socket.connected) {
        socket.connect();
    }
    
    setTimeout(() => {
        if (fitAddon) {
            fitAddon.fit();
            if (socket && socket.connected && term) {
                socket.emit('resize', { cols: term.cols, rows: term.rows });
            }
        }
        updateTerminalDrawerLayout();
        if (!_vvBound && window.visualViewport) {
            _vvBound = true;
            window.visualViewport.addEventListener('resize', function() {
                if (!isTermOpen) return;
                updateTerminalDrawerLayout();
            });
            window.visualViewport.addEventListener('scroll', function() {
                if (!isTermOpen) return;
                updateTerminalDrawerLayout();
            });
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
            const out = applyModifiersToData(data);
            socket.emit('input', { input: out });
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
    ctrlMode = false;
    altMode = false;
    syncModifierButtons();
    const drawerEl = document.getElementById('terminalDrawer');
    if (drawerEl) {
        drawerEl.style.bottom = '';
        drawerEl.style.height = '';
        drawerEl.style.maxHeight = '';
    }
    const drawer = document.getElementById('terminalDrawer');
    const backdrop = document.getElementById('terminalBackdrop');
    if (drawer) drawer.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
}

// 导出
window.openTerminal = openTerminal;
window.closeTerminal = closeTerminal;
window.termInitialized = termInitialized;
window.handleKeyBtn = handleKeyBtn;
