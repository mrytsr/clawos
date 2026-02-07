// ============ 机器人对话模块 ============

let botIsConnected = false;
let botSocket = null;
let botLastToken = '';
let botRequests = new Map();
let currentBotResponse = ''; 
let currentRunId = null;
let botConnectNonce = null;
let botConnectSent = false;
let botConnectTimer = null;
let botReconnectBackoffMs = 800;
let botLastPairingRequestId = null;
let botAutoScrollEnabled = true;
let botUiBound = false;

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

function queueBotConnect() {
    botConnectNonce = null;
    botConnectSent = false;
    if (botConnectTimer !== null) {
        clearTimeout(botConnectTimer);
        botConnectTimer = null;
    }
    botConnectTimer = setTimeout(() => {
        void sendBotConnect(null);
    }, 750);
}

function scheduleBotReconnect() {
    const delay = botReconnectBackoffMs;
    botReconnectBackoffMs = Math.min(Math.floor(botReconnectBackoffMs * 1.7), 15000);
    setTimeout(() => {
        ensureBotSocket();
    }, delay);
}

function ensureBotSocket() {
    if (botSocket && (botSocket.readyState === WebSocket.OPEN || botSocket.readyState === WebSocket.CONNECTING)) {
        return botSocket;
    }

    try {
        const h = 'ws://' + window.location.host + ':18789';
        botSocket = new WebSocket(h);
    } catch (e) {
        console.error('WebSocket Init Error:', e);
        setBotWsStatus(false, '初始化失败');
        return null;
    }

    botSocket.onopen = function() {
        console.log('Bot WS Connected');
        setBotWsStatus(false, '鉴权中...');
        queueBotConnect();
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
                        const err = data.error || {};
                        const e = new Error(err.message || 'Unknown error');
                        e.code = err.code;
                        e.details = err.details;
                        req.reject(e);
                    }
                }
                return;
            }

            // Handle Events
            if (data.type === 'event') {
                if (data.event === 'connect.challenge') {
                    const payload = data.payload || {};
                    botConnectNonce = typeof payload.nonce === 'string' ? payload.nonce : botConnectNonce;
                    void sendBotConnect(payload);
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
        const reason = String(event.reason || '');
        if (event.code === 1008) {
            if (reason.includes('pairing required') && botLastPairingRequestId) {
                msg = `需配对 (ReqID: ${botLastPairingRequestId})`;
            } else if (reason.includes('pairing required')) {
                msg = '需配对';
            } else if (reason.includes('device identity required')) {
                msg = '设备认证失败';
            } else {
                msg = '认证失败 (1008)';
            }
        } else if (event.code === 1006) {
            msg = '连接中断';
        }
        setBotWsStatus(false, msg);
        
        // Clear pending requests
        botRequests.forEach(req => req.reject(new Error('Connection closed')));
        botRequests.clear();

        if (event.code !== 1000 && event.code !== 1008) {
            scheduleBotReconnect();
        }
    };

    botSocket.onerror = function(err) {
        console.error('Bot WS Error', err);
        botIsConnected = false;
        setBotWsStatus(false, '连接错误');
    };

    return botSocket;
}

// ============ Device Identity & Crypto Utils ============
function bufToB64Url(buf) {
    return btoa(String.fromCharCode(...new Uint8Array(buf)))
        .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function b64UrlToBuf(str) {
    const bin = atob(str.replace(/-/g, '+').replace(/_/g, '/'));
    const buf = new Uint8Array(bin.length);
    for(let i=0; i<bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf;
}

function bufToHex(buf) {
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}

const DEVICE_KEY = 'bot_device_identity_v1';

async function getDeviceIdentity() {
    let raw = localStorage.getItem(DEVICE_KEY);
    if (raw) {
        try {
            const stored = JSON.parse(raw);
            const pubKey = await window.crypto.subtle.importKey(
                'raw', b64UrlToBuf(stored.publicKey), {name: 'Ed25519'}, true, ['verify']
            );
            // Check if private key is JWK or raw/pkcs8. Storing as JWK is easier for re-import
            const privKey = await window.crypto.subtle.importKey(
                'jwk', stored.privateKeyJwk, {name: 'Ed25519'}, true, ['sign']
            );
            return { ...stored, pubKeyObj: pubKey, privKeyObj: privKey };
        } catch(e) {
            console.error('Invalid stored identity, regenerating', e);
        }
    }

    const keyPair = await window.crypto.subtle.generateKey(
        { name: 'Ed25519' }, true, ['sign', 'verify']
    );
    
    const pubRaw = await window.crypto.subtle.exportKey('raw', keyPair.publicKey);
    const privJwk = await window.crypto.subtle.exportKey('jwk', keyPair.privateKey);
    
    const hash = await window.crypto.subtle.digest('SHA-256', pubRaw);
    const deviceId = bufToHex(hash);
    
    const identity = {
        deviceId,
        publicKey: bufToB64Url(pubRaw),
        privateKeyJwk: privJwk
    };
    
    localStorage.setItem(DEVICE_KEY, JSON.stringify(identity));
    return { ...identity, pubKeyObj: keyPair.publicKey, privKeyObj: keyPair.privateKey };
}

async function signDeviceAuth(identity, params) {
    const parts = [
        params.version || (params.nonce ? 'v2' : 'v1'),
        params.deviceId,
        params.clientId,
        params.clientMode,
        params.role,
        params.scopes.join(','),
        String(params.signedAtMs),
        params.token || ''
    ];
    if (params.nonce || params.version === 'v2') {
        parts.push(params.nonce || '');
    }
    
    const payload = parts.join('|');
    const enc = new TextEncoder();
    const sig = await window.crypto.subtle.sign(
        { name: 'Ed25519' },
        identity.privKeyObj,
        enc.encode(payload)
    );
    return bufToB64Url(sig);
}

async function sendBotConnect(challenge) {
    if (!botSocket || botSocket.readyState !== WebSocket.OPEN) {
        throw new Error('WebSocket not connected');
    }
    if (botConnectSent) {
        return;
    }
    botConnectSent = true;
    if (botConnectTimer !== null) {
        clearTimeout(botConnectTimer);
        botConnectTimer = null;
    }
    setBotWsStatus(false, '鉴权中...');
    
    // Read token from UI input
    const tokenInput = document.getElementById('botTokenInput');
    const token = tokenInput ? tokenInput.value.trim() : botLastToken;
    
    const nonce = challenge && typeof challenge.nonce === 'string'
        ? challenge.nonce
        : (botConnectNonce || null);
    
    try {
        const isSecureContext = typeof window.crypto !== 'undefined' && window.crypto && window.crypto.subtle;
        const client = {
            id: "openclaw-control-ui",
            version: "dev",
            platform: navigator.platform || "web",
            mode: "webchat",
            instanceId: localStorage.getItem('bot_instance_id') || undefined
        };
        if (!client.instanceId) {
            client.instanceId = generateUUID();
            localStorage.setItem('bot_instance_id', client.instanceId);
        }
        const role = "operator";
        const scopes = ["operator.admin", "operator.approvals", "operator.pairing"];
        const signedAt = Date.now();

        let device = undefined;
        if (isSecureContext) {
            const identity = await getDeviceIdentity();
            console.log('Using Device ID:', identity.deviceId);
            const authPayloadParams = {
                deviceId: identity.deviceId,
                clientId: client.id,
                clientMode: client.mode,
                role: role,
                scopes: scopes,
                signedAtMs: signedAt,
                token: token,
                nonce: nonce,
                version: nonce ? 'v2' : 'v1'
            };
            const signature = await signDeviceAuth(identity, authPayloadParams);
            device = {
                id: identity.deviceId,
                publicKey: identity.publicKey,
                signature: signature,
                signedAt: signedAt,
                nonce: nonce || undefined
            };
        }
        
        const params = {
            minProtocol: 3,
            maxProtocol: 3,
            client: client,
            role: role,
            scopes: scopes,
            device: device,
            auth: { token },
            caps: [],
            userAgent: navigator.userAgent,
            locale: navigator.language
        };

        const res = await botRequest('connect', params);
        console.log('Bot Connected', res);
        botIsConnected = true;
        setBotWsStatus(true, '已连接');
        botReconnectBackoffMs = 800;
        botLastPairingRequestId = null;
        localStorage.removeItem('bot_pairing_request');
    } catch (err) {
        console.error('Connect Failed', err);
        let msg = (err && err.message) ? err.message : 'Unknown';
        if (err && err.code === 'NOT_PAIRED') {
            const details = err.details || {};
            const requestId = details.requestId || null;
            if (requestId) {
                botLastPairingRequestId = requestId;
                localStorage.setItem('bot_pairing_request', JSON.stringify({ requestId, ts: Date.now() }));
                msg = `需配对 (ReqID: ${requestId})`;
                showToast(`设备需配对。请在服务端批准请求: ${requestId}`, 'warning');
            } else {
                msg = '需配对';
                showToast('设备需配对。请在服务端批准请求。', 'warning');
            }
        } else if (msg === 'pairing required') {
            showToast('设备需配对。请在服务端批准请求。', 'warning');
        }
        setBotWsStatus(false, msg);
    }
}

function handleBotEvent(data) {
    const extractTextFromChatMessage = (message) => {
        if (!message) return null;
        if (typeof message === 'string') return message;
        if (typeof message.text === 'string') return message.text;
        const content = message.content;
        if (Array.isArray(content)) {
            const parts = [];
            for (const block of content) {
                if (block && block.type === 'text' && typeof block.text === 'string') {
                    parts.push(block.text);
                }
            }
            const merged = parts.join('');
            return merged ? merged : null;
        }
        return null;
    };

    const isForActiveSession = (payload) => {
        const active = getOrCreateSessionKey();
        if (!payload || typeof payload !== 'object') return true;
        const candidates = [
            payload.sessionKey,
            payload.sessionkey,
            payload.session_key,
            payload.sessionId,
            payload.session_id,
            payload.session && payload.session.key,
            payload.session && payload.session.sessionKey
        ];
        const found = candidates.find(v => typeof v === 'string' && v.trim());
        if (!found) return true;
        return String(found) === String(active);
    };

    if (data.event === 'chat' && data.payload) {
        const p = data.payload;
        if (!isForActiveSession(p)) return;
        const state = p.state;
        const msg = p.message;
        if (msg && typeof msg.role === 'string' && msg.role !== 'assistant') {
            return;
        }
        if (state === 'delta') {
            const next = extractTextFromChatMessage(msg);
            if (typeof next === 'string') {
                if (!currentBotResponse || next.length >= currentBotResponse.length) {
                    currentBotResponse = next;
                    updateBotResponseUI(currentBotResponse);
                }
            }
            return;
        }
        if (state === 'final') {
            const next = extractTextFromChatMessage(msg);
            if (typeof next === 'string' && next.length >= (currentBotResponse || '').length) {
                currentBotResponse = next;
            }
            if (currentBotResponse) {
                saveBotMessageToHistory(currentBotResponse);
            }
            currentBotResponse = '';
            currentRunId = null;
            return;
        }
        if (state === 'error') {
            showToast(p.errorMessage ? String(p.errorMessage) : '对话出错', 'error');
            currentBotResponse = '';
            currentRunId = null;
            return;
        }
        if (state === 'aborted') {
            currentBotResponse = '';
            currentRunId = null;
            return;
        }
    }

    if (data.event === 'agent' && data.payload) {
        const p = data.payload;
        if (!isForActiveSession(p)) return;
        if (p.stream === 'text_delta' && p.data && p.data.text) {
            currentBotResponse += p.data.text;
            updateBotResponseUI(currentBotResponse);
        } else if (p.stream === 'lifecycle' && p.data && p.data.phase === 'end') {
            if (currentBotResponse) {
                saveBotMessageToHistory(currentBotResponse);
            }
            currentBotResponse = '';
            currentRunId = null;
        }
        return;
    }

    if (data.event === 'chat.event' && data.payload) {
        if (!isForActiveSession(data.payload)) return;
        if (data.payload.delta) {
            currentBotResponse += String(data.payload.delta);
            updateBotResponseUI(currentBotResponse);
        }
        if (data.payload.state === 'final') {
            if (currentBotResponse) {
                saveBotMessageToHistory(currentBotResponse);
            }
            currentBotResponse = '';
            currentRunId = null;
        }
    }
}

function getOrCreateSessionKey() {
    let sessionKey = localStorage.getItem('bot_session_key');
    if (!sessionKey) {
        sessionKey = 'session-' + generateUUID();
        localStorage.setItem('bot_session_key', sessionKey);
    }
    return sessionKey;
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderMarkdownToHtml(text) {
    const src = String(text ?? '');
    const blocks = [];
    const fenceRe = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
    let last = 0;
    let m;
    while ((m = fenceRe.exec(src)) !== null) {
        const before = src.slice(last, m.index);
        blocks.push({ t: 'text', v: before });
        const lang = (m[1] || '').trim();
        const code = m[2] || '';
        blocks.push({ t: 'code', lang, v: code });
        last = m.index + m[0].length;
    }
    blocks.push({ t: 'text', v: src.slice(last) });

    const out = blocks.map((b) => {
        if (b.t === 'code') {
            const lang = b.lang ? escapeHtml(b.lang) : '';
            const codeEsc = escapeHtml(b.v);
            const langClass = b.lang ? 'language-' + escapeHtml(b.lang) : '';
            return (
                '<div class="bot-md-code" style="position:relative;margin:10px 0;">'
                + '<button type="button" class="bot-code-copy" style="position:absolute;right:8px;top:8px;z-index:2;border:1px solid #d0d7de;background:#ffffff;border-radius:6px;padding:6px 8px;font-size:12px;cursor:pointer;" aria-label="复制代码" title="复制代码">⧉</button>'
                + '<pre style="margin:0;overflow:auto;"><code class="' + langClass + '">' + codeEsc + '</code></pre>'
                + (lang ? '<div style="position:absolute;left:10px;top:8px;font-size:12px;color:#6e7781;">' + lang + '</div>' : '')
                + '</div>'
            );
        }
        let html = escapeHtml(b.v);
        html = html.replace(/`([^`]+)`/g, function(_, c) {
            return '<code>' + escapeHtml(c) + '</code>';
        });
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(_, label, url) {
            const u = String(url || '').trim();
            if (!u) return label;
            const safe = escapeHtml(u);
            return '<a href="' + safe + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(label) + '</a>';
        });
        html = html.replace(/\n/g, '<br>');
        return html;
    }).join('');

    return out;
}

function isNearBottom(container, thresholdPx) {
    const th = typeof thresholdPx === 'number' ? thresholdPx : 40;
    return (container.scrollHeight - container.scrollTop - container.clientHeight) <= th;
}

function setJumpLatestVisible(visible) {
    const btn = document.getElementById('botJumpLatestBtn');
    if (!btn) return;
    btn.style.display = visible ? 'block' : 'none';
}

function botScrollToBottom(smooth) {
    const box = document.getElementById('botChatBox');
    if (!box) return;
    const behavior = smooth ? 'smooth' : 'auto';
    try {
        box.scrollTo({ top: box.scrollHeight, behavior });
    } catch (e) {
        box.scrollTop = box.scrollHeight;
    }
}

function botJumpToLatest() {
    botAutoScrollEnabled = true;
    setJumpLatestVisible(false);
    botScrollToBottom(true);
}

function ensureBotUiBindings() {
    if (botUiBound) return;
    const box = document.getElementById('botChatBox');
    const list = document.getElementById('botHistoryList');
    if (!box || !list) return;
    botUiBound = true;

    box.addEventListener('scroll', function() {
        const atBottom = isNearBottom(box, 60);
        botAutoScrollEnabled = atBottom;
        setJumpLatestVisible(!atBottom);
    });

    list.addEventListener('click', function(e) {
        const t = e && e.target ? e.target : null;
        if (!t) return;
        const btn = t.closest ? t.closest('.bot-code-copy') : null;
        if (!btn) return;
        const wrapper = btn.closest ? btn.closest('.bot-md-code') : null;
        const codeEl = wrapper ? wrapper.querySelector('code') : null;
        const code = codeEl ? codeEl.textContent : '';
        if (!code) return;
        navigator.clipboard.writeText(code).then(function() {
            showToast('已复制', 'success');
        }).catch(function() {
            showToast('复制失败', 'error');
        });
    });

    window.botJumpToLatest = botJumpToLatest;
}

function renderBotTextInto(el, text) {
    if (!el) return;
    el.innerHTML = renderMarkdownToHtml(text);
    if (window.hljs && typeof window.hljs.highlightElement === 'function') {
        el.querySelectorAll('pre code').forEach(function(codeEl) {
            try { window.hljs.highlightElement(codeEl); } catch (e) {}
        });
    }
}

function updateBotResponseUI(text) {
    ensureBotUiBindings();
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
    } else {
        tempMsg = document.getElementById('bot-temp-response-text');
    }
    
    if (tempMsg) {
        renderBotTextInto(tempMsg, text);
        const box = document.getElementById('botChatBox');
        if (box && botAutoScrollEnabled) {
            botScrollToBottom(true);
        } else {
            setJumpLatestVisible(true);
        }
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
    ensureBotUiBindings();
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
                        <div class="bot-text"></div>
                    </div>
                `;
                list.appendChild(li);
                const textEl = li.querySelector('.bot-text');
                renderBotTextInto(textEl, item.text);
            });
            
            const box = document.getElementById('botChatBox');
            if (box && botAutoScrollEnabled) {
                botScrollToBottom(false);
            } else {
                setJumpLatestVisible(true);
            }
        });
}

function botSend() {
    const input = document.getElementById('botInput');
    if (!input) return;
    const val = input.value.trim();
    if (!val) return;
    
    if (!botIsConnected) {
        showToast('请先连接助手', 'error');
        const tokenInput = document.getElementById('botTokenInput');
        const token = tokenInput ? tokenInput.value.trim() : botLastToken;
        botConnect(token);
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
    let sessionKey = getOrCreateSessionKey();
    
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
    if (ws && ws.readyState === WebSocket.OPEN) {
        queueBotConnect();
    }
}

function initBot() {
    // Load history
    loadBotHistory();
    loadBotStats();

    try {
        const rawPair = localStorage.getItem('bot_pairing_request');
        if (rawPair) {
            const parsed = JSON.parse(rawPair);
            if (parsed && typeof parsed.requestId === 'string') {
                botLastPairingRequestId = parsed.requestId;
                setBotWsStatus(false, `需配对 (ReqID: ${botLastPairingRequestId})`);
            }
        }
    } catch (e) {
        console.error('Invalid pairing request cache', e);
    }
    
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
