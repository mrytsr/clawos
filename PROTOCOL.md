# ClawOS WebSocket Protocol Documentation

This document describes the WebSocket protocol used by the ClawOS Bot interface, based on the official client implementation (`openclaw/ui`) and traffic analysis (`ws.har`).

## 1. Connection

*   **URL**: `ws://<host>:<port>/` (e.g., `ws://179.utjx.cn:18789/`)
    *   *Note: Previous `/bot` path is deprecated/removed.*
*   **Transport**: Native WebSocket

## 2. Authentication (Handshake)

The authentication flow uses a Challenge-Response mechanism.

### Sequence:

1.  **Client** establishes WebSocket connection.
2.  **Server** sends `connect.challenge` event.
3.  **Client** sends `connect` request with credentials.
4.  **Server** responds with `hello-ok` (success) or error.

### Frame Details:

#### Step 2: Server Challenge
```json
{
  "type": "event",
  "event": "connect.challenge",
  "payload": {
    "nonce": "uuid-string",
    "ts": 1770276274822
  }
}
```

#### Step 3: Client Connect Request
```json
{
  "type": "req",
  "id": "uuid-request-id",
  "method": "connect",
  "params": {
    "minProtocol": 3,
    "maxProtocol": 3,
    "client": {
      "id": "webchat-ui", 
      "version": "1.0.0",
      "platform": "web",
      "mode": "webchat"
    },
    "auth": {
      "token": "your-gateway-token"
    },
    "caps": []
  }
}
```
*   `client.id`: Use `"webchat-ui"` for standard web chat.
*   `auth.token`: The Gateway Token.

#### Step 4: Server Response
```json
{
  "type": "res",
  "id": "uuid-request-id",
  "ok": true,
  "payload": {
    "type": "hello-ok",
    "protocol": 3,
    "server": { ... },
    "features": { "methods": [...], "events": [...] }
  }
}
```

## 3. Heartbeat / Health

The client should verify connection health.

*   **Method**: `health` or `last-heartbeat`
*   **Request**:
    ```json
    {
      "type": "req",
      "id": "uuid",
      "method": "health",
      "params": {}
    }
    ```
*   **Server Event**: The server may periodically send `heartbeat` events.

## 4. Chat Interaction

### Sending Messages

Use the `chat.send` method.

```json
{
  "type": "req",
  "id": "uuid-req",
  "method": "chat.send",
  "params": {
    "sessionKey": "session-uuid",
    "message": "User message content",
    "deliver": false,
    "idempotencyKey": "uuid-run-id",
    "attachments": [] 
  }
}
```
*   `sessionKey`: Unique identifier for the chat session (e.g., `session-<uuid>`).
*   `idempotencyKey`: Unique ID for this message turn (usually same as request ID or separate UUID).

### Receiving Messages

The server streams responses using `agent` events.

#### Lifecycle Events
```json
{
  "type": "event",
  "event": "agent",
  "payload": {
    "runId": "uuid-run-id",
    "stream": "lifecycle",
    "data": { "phase": "start" } // or "end"
  }
}
```

#### Text Streaming (Delta)
```json
{
  "type": "event",
  "event": "agent",
  "payload": {
    "runId": "uuid-run-id",
    "stream": "text_delta",
    "data": { "text": "Hello " }
  }
}
```

#### Chat Events
```json
{
  "type": "event",
  "event": "chat",
  "payload": { ... }
}
```
