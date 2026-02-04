// ============ 机器人对话模块 ============

let botIsConnected = false;
let socketio = null;
let botSocketBound = false;

function ensureBotSocket() {
    if (!socketio) {
        socketio = io('/', { reconnection: true, reconnectionAttempts: 5, reconnectionDelay: 1000 });
    }
    if (!botSocketBound) {
        socketio.on('bot_to_proxy', (data) => {
            fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Basic ' + btoa('admin:admin') },
                body: JSON.stringify({ type: 'bot', text: data })
            }).then(() => {
                loadBotHistory();
            });
        });
        botSocketBound = true;
    }
}

function openBotModal() {
    const botDrawer = document.getElementById('botDrawer');
    if (botDrawer) botDrawer.classList.add('open');
    loadBotHistory();
    const savedToken = localStorage.getItem('pywebdeck_bot_token');
    if (savedToken) {
        document.getElementById('botTokenInput').value = savedToken;
        if (!botIsConnected) {
            botConnect();
        }
    }
}

function closeBotModal() {
    const botDrawer = document.getElementById('botDrawer');
    if (botDrawer) botDrawer.classList.remove('open');
}

function toggleBotSettings() {
    const settings = document.getElementById('botSettings');
    if (settings) {
        settings.style.display = settings.style.display === 'none' ? 'block' : 'none';
    }
}

function loadBotHistory() {
    fetch('/api/history', { headers: { 'Authorization': 'Basic ' + btoa('admin:admin') } })
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('botHistory');
            if (container && data.history) {
                let html = '';
                data.history.slice(-50).forEach(item => {
                    html += `<div class="bot-msg ${item.type}"><div class="bot-msg-content">${escapeHtml(item.text)}</div><div class="bot-msg-time">${item.time}</div></div>`;
                });
                container.innerHTML = html;
                container.scrollTop = container.scrollHeight;
            }
        });
}

function botConnect() {
    const token = document.getElementById('botTokenInput').value.trim();
    if (!token) {
        showToast('请输入 Token', 'warning');
        return;
    }
    localStorage.setItem('pywebdeck_bot_token', token);
    ensureBotSocket();
    botIsConnected = true;
    document.getElementById('botWsDot').className = 'bot-status-dot bot-dot-connected';
    document.getElementById('botWsDot').title = '已连接';
}

function botClear() {
    if (!confirm('确定要清空对话记录吗？')) return;
    fetch('/api/clear', { method: 'POST', headers: { 'Authorization': 'Basic ' + btoa('admin:admin') } })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showToast('已清空', 'success');
                loadBotHistory();
            }
        });
}

function botSend() {
    const input = document.getElementById('botInput');
    const message = input.value.trim();
    if (!message) return;
    
    input.value = '';
    
    fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Basic ' + btoa('admin:admin') },
        body: JSON.stringify({ type: 'user', text: message })
    }).then(() => {
        loadBotHistory();
        ensureBotSocket();
        socketio.emit('proxy_to_bot', message);
    });
}

// 导出
window.openBotModal = openBotModal;
window.closeBotModal = closeBotModal;
window.toggleBotSettings = toggleBotSettings;
window.botConnect = botConnect;
window.botClear = botClear;
window.botSend = botSend;
