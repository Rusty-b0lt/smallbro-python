import asyncio
import websockets
import time
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
start = [None]
previous_time = [None]
stop = asyncio.Future


def status():
    return True


def get_start():
    return start[0]


async def geturl(websocket, path):
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


async def geturl_server(stop):
    async with websockets.serve(geturl, '127.0.0.1', 5678):
        await stop


def start_server():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(geturl_server(stop))


def stop_server():
    stop.set_result('Finished')



