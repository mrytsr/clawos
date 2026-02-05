import asyncio
import websockets
import json
import uuid

TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"
URI = "ws://179.utjx.cn:18789/bot"

async def test_handshake():
    print(f"Connecting to {URI}...")
    try:
        async with websockets.connect(URI) as ws:
            print("Connected!")
            
            # 1. Wait for Challenge
            msg = await ws.recv()
            print(f"Server: {msg}")
            
            # 2. Send Connect Request
            req_id = str(uuid.uuid4())
            connect_req = {
                "type": "req",
                "id": req_id,
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {
                        "id": "webchat-ui",  # Valid ID from client-info.ts
                        "version": "1.0.0",
                        "platform": "web",
                        "mode": "webchat"    # Valid Mode from client-info.ts
                    },
                    "auth": {
                        "token": TOKEN
                    },
                    "caps": []
                }
            }
            
            print(f"Sending Connect: {json.dumps(connect_req)}")
            await ws.send(json.dumps(connect_req))
            
            # 3. Wait for Response
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"Response: {msg}")
            
            resp = json.loads(msg)
            if resp.get("ok"):
                print("Handshake SUCCESS!")
                
                # 4. Try sending a chat message
                chat_req_id = str(uuid.uuid4())
                session_key = f"session-{str(uuid.uuid4())}" # Generate a random session key
                
                chat_req = {
                    "type": "req",
                    "id": chat_req_id,
                    "method": "chat.send",
                    "params": {
                        "sessionKey": session_key,
                        "message": "Hello from debug script",
                        "deliver": False,
                        "idempotencyKey": chat_req_id
                    }
                }
                print(f"Sending Chat: {json.dumps(chat_req)}")
                await ws.send(json.dumps(chat_req))
                
                # 5. Listen for events
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        print(f"Received: {msg}")
                    except asyncio.TimeoutError:
                        print("No more messages (timeout)")
                        break
            else:
                print("Handshake FAILED")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_handshake())
