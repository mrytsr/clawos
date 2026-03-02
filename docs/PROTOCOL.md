# OpenClaw Gateway Protocol Documentation

This document describes the WebSocket communication protocol used by OpenClaw Gateway.

## 1. Connection

- **URL**: `ws://<host>:<port>` (e.g., `ws://127.0.0.1:18789`)
- **Path**: `/` (Root path, no specific endpoint required)

## 2. Handshake & Authentication

The connection establishment follows a Challenge-Response pattern.

### Step 1: Challenge (Server -> Client)
Upon connection, the server sends a challenge event containing a nonce.

```json
{
  "type": "event",
  "event": "connect.challenge",
  "payload": {
    "nonce": "89782023-a3a7-4bd2-a063-1577d6cc5675",
    "ts": 1770276274822
  }
}
```

### Step 2: Connect Request (Client -> Server)
The client must respond with a `connect` request, including device identity and signature.

```json
{
  "type": "req",
  "id": "uuid-v4",
  "method": "connect",
  "params": {
    "minProtocol": 3,
    "maxProtocol": 3,
    "client": {
      "id": "openclaw-control-ui",
      "version": "dev",
      "platform": "Win32",
      "mode": "webchat"
    },
    "role": "operator",
    "scopes": ["operator.admin", "operator.approvals", "operator.pairing"],
    "device": {
      "id": "<device_id_sha256_hex>",
      "publicKey": "<base64url_public_key>",
      "signature": "<base64url_signature>",
      "signedAt": 1770276275804,
      "nonce": "<nonce_from_challenge>"
    },
    "auth": {
      "token": "<gateway_token>"
    },
    "caps": [],
    "userAgent": "...",
    "locale": "zh-CN"
  }
}
```

### Step 3: Connect Response (Server -> Client)

**Success:**
```json
{
  "type": "res",
  "id": "uuid-v4",
  "ok": true,
  "payload": {
    "type": "hello-ok",
    "protocol": 3,
    "server": { ... },
    "features": { "methods": [...], "events": [...] }
  }
}
```

**Failure (Device Identity Required):**
```json
{
  "type": "res",
  "id": "uuid-v4",
  "ok": false,
  "error": {
    "code": "NOT_PAIRED",
    "message": "device identity required"
  }
}
```

**Failure (Pairing Required):**
```json
{
  "type": "res",
  "id": "uuid-v4",
  "ok": false,
  "error": {
    "code": "NOT_PAIRED",
    "message": "pairing required",
    "details": {
      "requestId": "<request_id>"
    }
  }
}
```

## 3. Device Identity

Device identity uses **Ed25519** key pairs.

- **Keys**: Ed25519 public/private key pair.
- **DeviceId**: SHA-256 hash of the raw public key bytes, converted to hex string.
- **Signature Payload**: Pipe-separated string (`|`).

**Payload Format:**
```
version|deviceId|clientId|clientMode|role|scopes|signedAtMs|token|nonce
```
*Note: `version` is "v2" if nonce is present, otherwise "v1".*

## 4. Message Protocol

### Request (Client -> Server)
```json
{
  "type": "req",
  "id": "uuid",
  "method": "method.name",
  "params": { ... }
}
```

### Response (Server -> Client)
```json
{
  "type": "res",
  "id": "uuid_of_request",
  "ok": true, // or false
  "payload": { ... }, // if ok=true
  "error": { "code": "...", "message": "..." } // if ok=false
}
```

### Event (Server -> Client)
```json
{
  "type": "event",
  "event": "event.name",
  "payload": { ... }
}
```

## 5. Chat Protocol

### Send Message
**Method**: `chat.send`

```json
{
  "type": "req",
  "id": "uuid",
  "method": "chat.send",
  "params": {
    "sessionKey": "session-uuid",
    "message": "Hello world",
    "deliver": false,
    "idempotencyKey": "uuid",
    "attachments": []
  }
}
```

### Receive Message
The server streams the response via `agent` events.

```json
{
  "type": "event",
  "event": "agent",
  "payload": {
    "stream": "text_delta",
    "data": {
      "text": "Hello! "
    }
  }
}
```

Lifecycle events:
```json
{
  "type": "event",
  "event": "agent",
  "payload": {
    "stream": "lifecycle",
    "data": {
      "phase": "end"
    }
  }
}
```

## 6. Heartbeat

The server defines a `tickIntervalMs` in the hello payload. Clients may receive `tick` events or be expected to maintain activity. The specific heartbeat frame is usually handled at the WebSocket level (Ping/Pong) or via periodic activity.

