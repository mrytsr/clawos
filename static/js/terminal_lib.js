/**
 * TerminalLib.js - 可嵌入的终端组件库
 */
(function loadXtermStyle() {
    if (document.querySelector('link[href*="xterm"]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/xterm@5.3.0/css/xterm.css';
    document.head.appendChild(link);
})();

var TerminalLib = (function() {
    var _isInit = false, term = null, fitAddon = null, socket = null;
    var isOpen = false, cwd = '/root/.openclaw/workspace';
    var ctrlMode = false, altMode = false, inputBuffer = '', isReady = false, autoRunFile = null;

    var EXECUTORS = { '.py': 'python3 ', '.js': 'node ', '.sh': 'bash ', '.bash': 'bash ', '.zsh': 'zsh ' };

    function getHTML() {
        return '<div id="term-lib-component" class="term-lib-component" style="display:none;">\
    <div class="term-lib-backdrop" onclick="TerminalLib.close()"></div>\
    <div class="term-lib-drawer">\
        <div class="term-lib-header"><span id="termLibPath" class="term-lib-path">~</span>\
            <button class="term-lib-close" onclick="TerminalLib.close()">×</button></div>\
        <div class="term-lib-container" id="termLibContainer"></div>\
        <div class="term-lib-toolbar">\
            <button class="term-lib-btn" onclick="TerminalLib.send(\'clear\\r\')">清屏</button>\
            <button class="term-lib-btn" onclick="TerminalLib.focus()">聚焦</button>\
            <button class="term-lib-btn" onclick="TerminalLib.toggleKeyboard()">⌨️</button></div>\
        <div class="term-lib-keyboard" id="termLibKeyboard">\
            <div class="term-key-row">\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'esc\')">ESC</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'tab\')">TAB</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'home\')">HOME</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'end\')">END</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'pgup\')">PGUP</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'pgdn\')">PGDN</button></div>\
            <div class="term-key-row">\
                <button class="term-key" data-mod="ctrl" onmousedown="TerminalLib.handleKey(event,\'ctrl\')">CTRL</button>\
                <button class="term-key" data-mod="alt" onmousedown="TerminalLib.handleKey(event,\'alt\')">ALT</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'up\')">↑</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'down\')">↓</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'left\')">←</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'right\')">→</button>\
                <button class="term-key" onmousedown="TerminalLib.handleKey(event,\'enter\')">↵</button></div></div></div></div>\
<style>.term-lib-component{position:fixed;inset:0;z-index:2000;display:flex;align-items:center;justify-content:center}\
.term-lib-backdrop{position:absolute;inset:0;background:rgba(0,0,0,0.6)}\
.term-lib-drawer{position:relative;width:90%;max-width:900px;height:60vh;max-height:500px;background:#000;border-radius:12px;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.6)}\
.term-lib-header{padding:10px 14px;background:#1a1a2e;display:flex;align-items:center;justify-content:space-between}\
.term-lib-path{color:#888;font-size:13px;font-family:monospace}\
.term-lib-close{width:28px;height:28px;border-radius:6px;background:#e94560;border:none;color:#fff;cursor:pointer;font-size:18px}\
.term-lib-close:hover{background:#ff6b6b}\
.term-lib-container{flex:1;padding:8px;overflow:hidden}\
.term-lib-toolbar{padding:8px 12px;background:#1a1a2e;display:flex;gap:8px}\
.term-lib-btn{padding:6px 12px;border-radius:6px;background:#0f3460;border:none;color:#ccc;cursor:pointer;font-size:12px}\
.term-lib-btn:hover{background:#16213e}\
.term-lib-keyboard{padding:8px 12px;background:#1a1a2e;border-top:1px solid #333;display:none;flex-direction:column;gap:6px}\
.term-lib-keyboard.visible{display:flex}\
.term-key-row{display:flex;gap:6px;justify-content:center}\
.term-key{padding:8px 12px;min-width:40px;border-radius:6px;background:#0f3460;border:none;color:#ccc;cursor:pointer;font-size:12px}\
.term-key:hover{background:#16213e}\
.term-key.active{background:#0969da!important;color:#fff}\
</style>';
    }

    function init() {
        if (_isInit) return;
        _isInit = true;
        var div = document.createElement('div');
        div.innerHTML = getHTML();
        document.body.appendChild(div);
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                var el = document.getElementById('term-lib-component');
                if (el && el.style.display !== 'none') close();
            }
        });
    }

    function getExecutor(filename) {
        if (!filename) return null;
        var basename = filename.substring(filename.lastIndexOf('/') + 1);
        var lastDot = basename.lastIndexOf('.');
        var ext = lastDot > 0 ? basename.substring(lastDot).toLowerCase() : '';
        return ext ? (EXECUTORS[ext] || null) : null;
    }

    function doConnect() {
        socket = io('/term', { forceNew: true, reconnection: true, reconnectionAttempts: 3, transports: ['websocket', 'polling'] });
        socket.on('connect', function() {
            isReady = false;
            socket.emit('create_terminal', { cwd: cwd });
            if (term) term.write('\r\n\x1b[32m*** 已连接 ***\x1b[0m\r\n');
            if (fitAddon) fitAddon.fit();
            setTimeout(function() {
                if (socket && socket.connected && cwd) {
                    socket.emit('input', { input: 'cd ' + cwd + '\r' });
                    setTimeout(function() {
                        if (autoRunFile) {
                            var executor = getExecutor(autoRunFile);
                            // cd 之后只用文件名
                            var filename = autoRunFile;
                            if (cwd && autoRunFile.indexOf(cwd) === 0) {
                                filename = autoRunFile.substring(cwd.length).replace(/^\/+/, '');
                            }
                            var cmd = executor ? executor + filename : filename;
                            if (term) term.write('\r\n\x1b[33m> ' + cmd + '\x1b[0m\r\n');
                            socket.emit('input', { input: cmd + '\r' });
                            autoRunFile = null;
                        }
                        isReady = true;
                        if (term) term.focus();
                    }, 300);
                } else {
                    isReady = true;
                }
            }, 500);
        });
        socket.on('output', function(data) {
            if (isOpen && term && data && data.data) term.write(data.data);
        });
        socket.on('disconnect', function() {
            if (isOpen && term) term.write('\r\n\x1b[33m*** 连接断开 ***\x1b[0m\r\n');
        });
    }

    function initTerm() {
        term = new Terminal({ cursorBlink: true, fontSize: 13, fontFamily: 'Menlo,Monaco,monospace', theme: { background: '#000' } });
        fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('termLibContainer'));
        fitAddon.fit();
        doConnect();
        term.onData(function(data) {
            if (!isReady || !socket || !socket.connected) return;
            if (data === '\r' || data === '\n') {
                var executor = getExecutor(inputBuffer);
                if (executor) {
                    var bs = '';
                    for (var i = 0; i < inputBuffer.length; i++) bs += '\x7f';
                    socket.emit('input', { input: bs + executor + inputBuffer + '\r' });
                    inputBuffer = '';
                    return;
                }
                inputBuffer = '';
            } else if (data === '\x7f' || data === '\x08') {
                inputBuffer = inputBuffer.slice(0, -1);
            } else if (data === '\x15') {
                inputBuffer = '';
            } else if (data.length === 1 && data >= ' ') {
                inputBuffer += data;
            }
            socket.emit('input', { input: data });
        });
        term.onResize(function(size) {
            if (socket && socket.connected) socket.emit('resize', { cols: size.cols, rows: size.rows });
        });
    }

    function loadXterm(callback) {
        if (typeof Terminal !== 'undefined' && typeof FitAddon !== 'undefined') {
            callback();
            return;
        }
        var loaded = { xterm: false, fit: false };
        function check() {
            if (loaded.xterm && loaded.fit) callback();
        }
        var s1 = document.createElement('script');
        s1.src = 'https://unpkg.com/xterm@5.3.0/lib/xterm.js';
        s1.onload = function() { loaded.xterm = true; check(); };
        document.body.appendChild(s1);
        var s2 = document.createElement('script');
        s2.src = 'https://unpkg.com/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js';
        s2.onload = function() { loaded.fit = true; check(); };
        document.body.appendChild(s2);
    }

    return {
        open: function(path, file) {
            if (isOpen) return;
            init();
            cwd = path || cwd;
            autoRunFile = file || null;
            inputBuffer = '';
            isReady = false;
            document.getElementById('term-lib-component').style.display = 'flex';
            isOpen = true;
            loadXterm(initTerm);
        },
        close: function() {
            if (!isOpen) return;
            document.getElementById('term-lib-component').style.display = 'none';
            isOpen = false;
            isReady = false;
            inputBuffer = '';
            autoRunFile = null;
        },
        send: function(cmd) {
            if (term && socket && socket.connected) {
                socket.emit('input', { input: cmd });
                term.focus();
            }
        },
        focus: function() { if (term) term.focus(); },
        toggleKeyboard: function() {
            var kb = document.getElementById('termLibKeyboard');
            kb.classList.toggle('visible');
        },
        handleKey: function(e, key) {
            e.preventDefault();
            e.stopPropagation();
            if (key === 'ctrl') {
                ctrlMode = !ctrlMode;
                if (ctrlMode && altMode) altMode = false;
                document.querySelector('.term-key[data-mod="ctrl"]').classList.toggle('active', ctrlMode);
                document.querySelector('.term-key[data-mod="alt"]').classList.toggle('active', altMode);
                focus();
            } else if (key === 'alt') {
                altMode = !altMode;
                if (altMode && ctrlMode) ctrlMode = false;
                document.querySelector('.term-key[data-mod="ctrl"]').classList.toggle('active', ctrlMode);
                document.querySelector('.term-key[data-mod="alt"]').classList.toggle('active', altMode);
                focus();
            } else {
                var map = { 'esc': '\x1b', 'enter': '\r', 'tab': '\t', 'up': '\x1b[A', 'down': '\x1b[B', 'left': '\x1b[D', 'right': '\x1b[C', 'home': '\x1b[H', 'end': '\x1b[F', 'pgup': '\x1b[5~', 'pgdn': '\x1b[6~' };
                var seq = map[key] || key;
                if (seq) send(seq);
                focus();
            }
        },
        isOpen: function() { return isOpen; }
    };
})();
