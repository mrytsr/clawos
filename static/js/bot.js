// ============ 机器人对话模块 ============

let botIsConnected = false;
let botSocket = null;
let botLastToken = '';
let botRequests = new Map();
let currentBotResponse = ''; 
let currentRunId = null;

// Generate UUID for IDs
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function setBotWsStatus(connected, statusText) {
    const dot = document.getElementById('botWsDot');
    const text = document.getElementById('botWsStatus');
    if (dot) {
        dot.className = connected
            ? 'bot-status-dot bot-dot-connected'
            : 'bot-status-dot bot-dot-disconnected';
        dot.title = statusText || (connected ? '已连接' : '未连接');
    }
    if (text) {
        text.textContent = statusText || (connected ? '已连接' : '未连接');
    }
}

function loadBotStats() {
    fetch('/api/stats', { headers: { 'Authorization': 'Basic ' + btoa('admin:admin') } })
        .then(r => r.json())
        .then(data => {
            const sent = document.getElementById('botSentCount');
            const conv = document.getElementById('botConvCount');
            const stats = data && data.success && data.data ? data.data : null;
            if (stats) {
                if (sent) sent.textContent = String(stats.sent_count ?? 0);
                if (conv) conv.textContent = String(stats.conv_count ?? 0);
            }
        });
}

// Wrapper for sending requests with ID and Promise
function botRequest(method, params) {
    return new Promise((resolve, reject) => {
        if (!botSocket || botSocket.readyState !== WebSocket.OPEN) {
            reject(new Error('WebSocket not connected'));
            return;
        }
        const id = generateUUID();
        const frame = { type: 'req', id, method, params };
        botRequests.set(id, { resolve, reject });
        botSocket.send(JSON.stringify(frame));
        
        // Timeout after 30s
        setTimeout(() => {
            if (botRequests.has(id)) {
                botRequests.get(id).reject(new Error('Request timeout'));
                botRequests.delete(id);
            }
        }, 30000);
    });
}

function ensureBotSocket() {
    if (botSocket && (botSocket.readyState === WebSocket.OPEN || botSocket.readyState === WebSocket.CONNECTING)) {
        return botSocket;
    }

    try {
        botSocket = new WebSocket('ws://179.utjx.cn:18789');
    } catch (e) {
        console.error('WebSocket Init Error:', e);
        setBotWsStatus(false, '初始化失败');
        return null;
    }

    botSocket.onopen = function() {
        console.log('Bot WS Connected');
        setBotWsStatus(false, '鉴权中...');
    };

    botSocket.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            // Handle Responses
            if (data.type === 'res') {
                const req = botRequests.get(data.id);
                if (req) {
                    botRequests.delete(data.id);
                    if (data.ok) {
                        req.resolve(data.payload);
                    } else {
                        console.error('Req Error:', data.error);
                        req.reject(new Error(data.error.message || 'Unknown error'));
                    }
                }
                return;
            }

            // Handle Events
            if (data.type === 'event') {
                if (data.event === 'connect.challenge') {
                    sendBotConnect();
                } else {
                    handleBotEvent(data);
                }
            }
        } catch (e) {
            console.error('Bot WS Parse Error', e);
        }
    };

    botSocket.onclose = function(event) {
        console.log('Bot WS Closed', event.code, event.reason);
        botIsConnected = false;
        let msg = '未连接';
        if (event.code === 1008) {
            msg = '认证失败 (1008)';
            showToast('连接被拒绝：Token 无效或协议错误', 'error');
        } else if (event.code === 1006) {
            msg = '连接中断';
        }
        setBotWsStatus(false, msg);
        
        // Clear pending requests
        botRequests.forEach(req => req.reject(new Error('Connection closed')));
        botRequests.clear();
    };

    botSocket.onerror = function(err) {
        console.error('Bot WS Error', err);
        botIsConnected = false;
        setBotWsStatus(false, '连接错误');
    };

    return botSocket;
}

function sendBotConnect() {
    setBotWsStatus(false, '鉴权中...');
    const token = botLastToken;
    
    // Official Client Protocol
    const params = {
        minProtocol: 3,
        maxProtocol: 3,
        client: {
            id: "webchat-ui", 
            version: "1.0.0", 
            platform: "web", 
            mode: "webchat"
        },
        auth: { token },
        caps: []
    };

    botRequest('connect', params)
        .then(res => {
             console.log('Bot Connected', res);
             botIsConnected = true;
             setBotWsStatus(true, '已连接');
        })
        .catch(err => {
             console.error('Connect Failed', err);
             setBotWsStatus(false, '鉴权失败: ' + (err.message || 'Unknown'));
             if (botSocket) botSocket.close();
        });
}

function handleBotEvent(data) {
    // Handle streaming chat response
    // Events can be 'chat.event', 'agent', etc.
    
    // Logic to extract text delta
    let delta = '';
    let isFinal = false;

    // Check for 'agent' event (lifecycle, text_delta, etc)
    if (data.event === 'agent' && data.payload) {
        const p = data.payload;
        if (p.stream === 'text_delta' && p.data && p.data.text) {
            delta = p.data.text;
        } else if (p.stream === 'lifecycle' && p.data && p.data.phase === 'end') {
            isFinal = true;
        }
    } 
    // Check for 'chat.event' (if server sends that instead)
    else if (data.event === 'chat.event' && data.payload) {
        // Adapt based on actual payload structure if different
        if (data.payload.delta) delta = data.payload.delta;
        if (data.payload.state === 'final') isFinal = true;
    }

    if (delta) {
        currentBotResponse += delta;
        updateBotResponseUI(currentBotResponse);
    }

    if (isFinal) {
        // Save full response to history
        saveBotMessageToHistory(currentBotResponse);
        currentBotResponse = '';
        currentRunId = null;
    }
}

function updateBotResponseUI(text) {
    // Ideally update the last message bubble if it exists, or create one
    // For simplicity, we can reload history if we are saving incrementally? 
    // No, that flickers. 
    // We should find the specific DOM element and update it.
    
    // If we are using the simple loadBotHistory approach which clears container:
    // We need to implement a "temporary" message append.
    
    const list = document.getElementById('botHistoryList');
    if (!list) return;
    
    let tempMsg = document.getElementById('bot-temp-response');
    if (!tempMsg) {
        // Create temp message
        const li = document.createElement('li');
        li.className = 'bot-msg bot-msg-bot';
        li.innerHTML = `
            <div class="bot-avatar">🤖</div>
            <div class="bot-bubble">
                <div class="bot-name">Claw (Typing...)</div>
                <div class="bot-text" id="bot-temp-response-text"></div>
            </div>
        `;
        // Append to list (make sure it's at bottom)
        list.appendChild(li);
        tempMsg = document.getElementById('bot-temp-response-text');
        tempMsg.parentElement.parentElement.id = 'bot-temp-response'; // Mark container
        
        // Scroll to bottom
        const container = document.querySelector('.bot-history');
        if (container) container.scrollTop = container.scrollHeight;
    } else {
        tempMsg = document.getElementById('bot-temp-response-text');
    }
    
    if (tempMsg) {
        // Simple text escape
        tempMsg.textContent = text; 
        
        // Scroll to bottom
        const container = document.querySelector('.bot-history');
        if (container) container.scrollTop = container.scrollHeight;
    }
}

function saveBotMessageToHistory(text) {
    fetch('/api/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: JSON.stringify({ type: 'bot', text: text })
    }).then(() => {
        // Remove temp message
        const tempMsg = document.getElementById('bot-temp-response');
        if (tempMsg) tempMsg.remove();
        // Reload full history
        loadBotHistory();
        loadBotStats();
    });
}

function loadBotHistory() {
    fetch('/api/history', { headers: { 'Authorization': 'Basic ' + btoa('admin:admin') } })
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('botHistoryList');
            if (!list) return;
            list.innerHTML = '';
            
            const history = data && data.success && data.data ? data.data.history : [];
            history.forEach(item => {
                const li = document.createElement('li');
                li.className = 'bot-msg bot-msg-' + (item.type || 'bot');
                
                const avatar = item.type === 'user' ? '👤' : '🤖';
                const name = item.type === 'user' ? 'You' : 'Claw';
                
                li.innerHTML = `
                    <div class="bot-avatar">${avatar}</div>
                    <div class="bot-bubble">
                        <div class="bot-name">${name} <span style="font-size:0.8em;opacity:0.6;margin-left:5px">${item.time || ''}</span></div>
                        <div class="bot-text">${escapeHtml(item.text)}</div>
                    </div>
                `;
                list.appendChild(li);
            });
            
            // Scroll to bottom
            const container = document.querySelector('.bot-history');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        });
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;")
               .replace(/</g, "&lt;")
               .replace(/>/g, "&gt;")
               .replace(/"/g, "&quot;")
               .replace(/'/g, "&#039;");
}

function botSend() {
    const input = document.getElementById('botInput');
    if (!input) return;
    const val = input.value.trim();
    if (!val) return;
    
    if (!botIsConnected) {
        showToast('请先连接助手', 'error');
        // Try to connect
        ensureBotSocket();
        return;
    }

    input.value = '';

    // 1. Save User Message Locally
    fetch('/api/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: JSON.stringify({ type: 'user', text: val })
    }).then(() => {
        loadBotHistory();
        loadBotStats();
    });

    // 2. Send to Gateway
    let sessionKey = localStorage.getItem('bot_session_key');
    if (!sessionKey) {
        sessionKey = 'session-' + generateUUID();
        localStorage.setItem('bot_session_key', sessionKey);
    }
    
    const runId = generateUUID();
    currentRunId = runId;
    currentBotResponse = ''; // Reset buffer

    botRequest('chat.send', {
        sessionKey: sessionKey,
        message: val,
        deliver: false,
        idempotencyKey: runId,
        attachments: []
    }).then(res => {
        console.log('Message Sent', res);
        // Show temp response bubble immediately
        updateBotResponseUI('Thinking...');
    }).catch(err => {
        console.error('Send Failed', err);
        showToast('发送失败: ' + err.message, 'error');
    });
}

function botConnect(token) {
    botLastToken = token;
    const ws = ensureBotSocket();
    // If already connected, we might need to re-auth? 
    // ensureBotSocket checks readyState. 
    // If connected, it won't reconnect.
    // If we want to force auth, we might need to send auth frame again?
    // But official protocol authenticates during connect.
    // So if WS is open, we assume authenticated.
}

function initBot() {
    // Load history
    loadBotHistory();
    loadBotStats();
    
    // Bind Enter key
    const input = document.getElementById('botInput');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                botSend();
            }
        });
    }
}
