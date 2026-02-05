import asyncio
import websockets
import json

TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"
URI = f"ws://179.utjx.cn:18789/bot?token={TOKEN}"

async def try_connect(name, payload_factory):
    print(f"\n--- Testing: {name} ---")
    try:
        async with websockets.connect(URI) as ws:
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
    # 1. Auth event, Nonce only
    await try_connect("Auth Event (Nonce Only)", 
        lambda n: {
            "type": "event", 
            "event": "auth", 
            "payload": {"nonce": n}
        }
    )
    
    # 2. connect.response, Nonce only
    await try_connect("connect.response (Nonce Only)", 
        lambda n: {
            "type": "event", 
            "event": "connect.response", 
            "payload": {"nonce": n}
        }
    )

    # 3. connect.response, Token + Nonce
    await try_connect("connect.response (Token + Nonce)", 
        lambda n: {
            "type": "event", 
            "event": "connect.response", 
            "payload": {"token": TOKEN, "nonce": n}
        }
    )
    
    # 4. Empty payload? (Just ack)
    await try_connect("Empty Ack", 
        lambda n: {
            "type": "event", 
            "event": "connect.ack", 
            "payload": {"nonce": n}
        }
    )

if __name__ == "__main__":
    asyncio.run(main())
