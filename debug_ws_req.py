import asyncio
import websockets
import json
import uuid

TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"
URI = "ws://179.utjx.cn:18789/bot"

async def test_req_connect():
    print(f"Connecting to {URI}...")
    try:
        async with websockets.connect(URI) as ws:
            print("Connected!")
            msg = await ws.recv()
            print(f"Received: {msg}")
            
            # We ignore challenge nonce for now, assuming token auth doesn't need it?
            # Or maybe we need to include it somewhere?
            
            req_id = str(uuid.uuid4())
            connect_req = {
                "type": "req",
                "id": req_id,
                "method": "connect",
                "params": {
                    "minProtocol": 1,
                    "maxProtocol": 1,
                    "client": {
                        "id": "bot-client",
                        "version": "1.0.0",
                        "platform": "web",
                        "mode": "backend"
                    },
                    "auth": {
                        "token": TOKEN
                    }
                }
            }
            
            print(f"Sending Connect Req: {json.dumps(connect_req)}")
            await ws.send(json.dumps(connect_req))
            
            # Wait for response
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"Response: {msg}")
            
            # If success, try sending a message
            # But wait, sending message also needs to be a "req" or "event"?
            # Client code has onEvent.
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_req_connect())
