import asyncio
import websockets
import json
import time

TOKEN = "48d6818aace0430b504d27a7c100669ed8f4694da9d6eb95"
URI = f"ws://179.utjx.cn:18789/bot?token={TOKEN}"

async def test_url_auth():
    print(f"Connecting to {URI}...")
    try:
        async with websockets.connect(URI) as ws:
            print("Connected! Waiting for challenge...")
            msg = await ws.recv()
            print(f"Received: {msg}")
            
            # Wait 5 seconds to see if it closes
            print("Waiting 5s to check connection stability...")
            await asyncio.sleep(5)
            
            if ws.open:
                print("Connection still OPEN! Trying to send message...")
                chat_msg = {
                    "type": "event",
                    "event": "bot.message",
                    "payload": {
                        "text": "Hello from debug script"
                    }
                }
                await ws.send(json.dumps(chat_msg))
                print("Message sent. Waiting for echo/response...")
                
                response = await ws.recv()
                print(f"Received response: {response}")
            else:
                print("Connection closed during wait.")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Closed: {e.code} {e.reason}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_url_auth())
