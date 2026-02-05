import asyncio
import websockets
import json

TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"
URI = f"ws://179.utjx.cn:18789/bot?token={TOKEN}"

async def test_url_challenge():
    print(f"Connecting to {URI}...")
    try:
        async with websockets.connect(URI) as ws:
            print("Connected!")
            msg = await ws.recv()
            print(f"Received: {msg}")
            
            challenge = json.loads(msg)
            nonce = challenge.get('payload', {}).get('nonce')
            
            # Respond to challenge
            # Try 1: Full auth with token and nonce
            auth_msg = {
                "type": "event",
                "event": "auth",
                "payload": {
                    "token": TOKEN,
                    "nonce": nonce
                }
            }
            print(f"Sending Auth: {json.dumps(auth_msg)}")
            await ws.send(json.dumps(auth_msg))
            
            # Wait for result
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"Response: {msg}")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_url_challenge())
