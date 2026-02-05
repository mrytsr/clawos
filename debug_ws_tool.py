import asyncio
import websockets
import json
import sys

# Default Token
DEFAULT_TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"

async def debug_connection(token=DEFAULT_TOKEN):
    uri = "ws://179.utjx.cn:18789/bot"
    print(f"Connecting to {uri} with token {token[:6]}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # 1. Wait for Challenge
            msg = await websocket.recv()
            print(f"Received: {msg}")
            
            try:
                data = json.loads(msg)
                if data.get('event') == 'connect.challenge':
                    nonce = data.get('payload', {}).get('nonce')
                    
                    # 2. Send Auth
                    auth_payload = {
                        "type": "event", 
                        "event": "auth", 
                        "payload": {
                            "token": token,
                            "nonce": nonce
                        }
                    }
                    print(f"Sending Auth: {json.dumps(auth_payload)}")
                    await websocket.send(json.dumps(auth_payload))
                    
                    # 3. Wait for Response
                    while True:
                        resp = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        print(f"Received: {resp}")
                        
            except json.JSONDecodeError:
                print("Received non-JSON message")
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection Closed: Code={e.code}, Reason={e.reason}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    token = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOKEN
    asyncio.run(debug_connection(token))
