import asyncio
import websockets
import time
from tornado.platform.asyncio import AnyThreadEventLoopPolicy


def status():
    return True


def extensions_main():
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    start = [None]
    previous_time = [None]

    async def geturl(websocket, path):
        print('websocket is running')
        while True:
            result = await websocket.recv()
            if start[0] is not None:
                end = time.time()
                previous_time[0] = end - start[0]
            if previous_time[0] is not None:
                print('time in tab: ' + str(previous_time[0]))
                print('')
            event, url = result.split(',')
            print('New Browser Event')
            if event is not 'false':
                print('event: ' + event)
            if url is not 'false':
                print('url: ' + url)
            start[0] = time.time()
    try:
        start_server = websockets.serve(geturl, '127.0.0.1', 5678)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except:
        pass


