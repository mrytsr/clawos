import asyncio
import websockets
import json
import sys

TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"
URI = "ws://179.utjx.cn:18789/bot"

async def try_connect(name, payload_factory, headers=None):
    print(f"\n--- Testing: {name} ---")
    try:
        async with websockets.connect(URI, extra_headers=headers) as ws:
            print("Connected")
            msg = await ws.recv()
            print(f"Server: {msg}")
            
            challenge = json.loads(msg)
            nonce = challenge.get('payload', {}).get('nonce')
            
            payload = payload_factory(nonce)
            print(f"Sending: {json.dumps(payload)}")
            await ws.send(json.dumps(payload))
            
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                print(f"SUCCESS RESPONSE: {resp}")
                return True
            except asyncio.TimeoutError:
                print("Timeout (connection stayed open?)")
                return True
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Closed: {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

async def main():
    # 1. Try with Origin
    headers = {"Origin": "http://179.utjx.cn:18789"}
    
    # Factory 1: Current attempt (with nonce)
    await try_connect("With Origin + Nonce", 
        lambda n: {
            "type": "event", 
            "event": "auth", 
            "payload": {"token": TOKEN, "nonce": n}
        }, 
        headers
    )
    
    # Factory 2: No nonce
    await try_connect("With Origin + No Nonce", 
        lambda n: {
            "type": "event", 
            "event": "auth", 
            "payload": {"token": TOKEN}
        }, 
        headers
    )

    # Factory 3: connect.response
    await try_connect("connect.response event", 
        lambda n: {
            "type": "event", 
            "event": "connect.response", 
            "payload": {"token": TOKEN, "nonce": n}
        }, 
        headers
    )

    # Factory 4: Flat token
    await try_connect("Flat Token", 
        lambda n: {"token": TOKEN, "nonce": n}, 
        headers
    )
    
    # Factory 5: 'authorization' event
    await try_connect("Authorization Event", 
        lambda n: {
            "type": "event", 
            "event": "authorization", 
            "payload": {"token": TOKEN}
        }, 
        headers
    )

if __name__ == "__main__":
    asyncio.run(main())
