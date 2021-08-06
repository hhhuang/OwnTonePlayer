import asyncio
import websockets
import json

async def hello(url):
    async with websockets.connect(url, subprotocols=["notify"]) as ws:
        r = { "notify": [ "player", "volume", "queue" ] }
        print(r.keys())
        await ws.send(json.dumps(r))
        print("Sent")
        while True:
            data = await ws.recv()
            print(data) 
        
asyncio.get_event_loop().run_until_complete(hello("ws://192.168.11.235:3688"))

	
