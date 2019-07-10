import asyncio
import websockets
import time
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
import mysql.connector
import re
import datetime

# Mysql setup
cnx = mysql.connector.connect(user='root', password='LoveSosa1337', host='127.0.0.1', database='smallbro')
cursor = cnx.cursor()


def status():
    return True


def extensions_main():
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    start = [None]

    async def geturl(websocket, path):
        while True:
            try:
                result = await websocket.recv()
                if start[0] is not None:
                    end = time.time()
                    previous_time = int(round(end - start[0]))
                    cursor.execute("UPDATE sessions SET duration = {} WHERE user_id = 1 ORDER BY id DESC LIMIT 1".format(previous_time))
                    cnx.commit()
                    print('time in tab: ' + str(previous_time))
                    print('')
                event, url = result.split(',')
                print('New Browser Event')
                if event is not 'false' and url is not 'false':
                    search = re.search('^(https?://)?(w{3}\.)?([^/:]+)/?.*$', url)
                    if search:
                        url_re = search.group(3)
                        print(url_re)
                    else:
                        url_re = url

                    # Inserting into apps
                    cursor.execute("SELECT COUNT(1) FROM apps WHERE name = '{}'".format(url_re))
                    exists = cursor.fetchone()[0]
                    if exists == 0:
                        cursor.execute("INSERT INTO apps (name) VALUES ('{}')".format(url_re))
                        cnx.commit()
                    cursor.execute("SELECT id FROM apps WHERE name = '{}'".format(url_re))
                    app_id = cursor.fetchone()[0]
                    # Inserting into sessions
                    cursor.execute("INSERT INTO sessions (user_id, date, app_id) VALUES (1, '{}', '{}')".format(datetime.datetime.today(), app_id))
                    cnx.commit()
                    print('event: ' + event)
                    print('url: ' + url)
                start[0] = time.time()
            except websockets.ConnectionClosed:
                break

    start_server = websockets.serve(geturl, '127.0.0.1', 5678)

    asyncio.get_event_loop().run_until_complete(asyncio.gather(start_server))
    asyncio.get_event_loop().run_forever()
