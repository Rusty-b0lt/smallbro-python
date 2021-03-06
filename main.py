# Based on code by Stephan Sokolow
# Source: https://gist.github.com/ssokolow/e7c9aae63fb7973e4d64cff969a78ae8
# !/usr/bin/env python

"""python-xlib example which reacts to changing the active window/title.
Requires:
- Python
- python-xlib
Tested with Python 2.x because my Kubuntu 14.04 doesn't come with python-xlib
for Python 3.x.
Design:
-------
Any modern window manager that isn't horrendously broken maintains an X11
property on the root window named _NET_ACTIVE_WINDOW.
Any modern application toolkit presents the window title via a property
named _NET_WM_NAME.
This listens for changes to both of them and then hides duplicate events
so it only reacts to title changes once.
"""

from contextlib import contextmanager
from threading import Thread
from getpass import getpass
import extensions
import Xlib
import Xlib.display
import time
import xprintidle
import re
import datetime
import mysql_setup
import bcrypt

# Connect to the X server and get the root window
disp = Xlib.display.Display()
root = disp.screen().root

# Prepare the property names we use so they can be fed into X11 APIs
NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
NET_WM_NAME = disp.intern_atom('_NET_WM_NAME')  # UTF-8
WM_NAME = disp.intern_atom('WM_NAME')           # Legacy encoding

# Mysql
cnx = mysql_setup.setup()
cursor = cnx.cursor(buffered=True)

last_seen = {'xid': None, 'title': None}
app_list = []
previous = {
    'start': None,
    'app_name': None
}
idle = [None]
signin = [0]

@contextmanager
def window_obj(win_id):
    """Simplify dealing with BadWindow (make it either valid or None)"""
    window_obj = None
    if win_id:
        try:
            window_obj = disp.create_resource_object('window', win_id)
        except Xlib.error.XError:
            pass
    yield window_obj


def get_active_window():
    """Return a (window_obj, focus_has_changed) tuple for the active window."""
    win_id = root.get_full_property(NET_ACTIVE_WINDOW, Xlib.X.AnyPropertyType).value[0]

    focus_changed = (win_id != last_seen['xid'])
    if focus_changed:
        with window_obj(last_seen['xid']) as old_win:
            if old_win:
                old_win.change_attributes(event_mask=Xlib.X.NoEventMask)

        last_seen['xid'] = win_id
        with window_obj(win_id) as new_win:
            if new_win:
                new_win.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

    return win_id, focus_changed


def _get_window_name_inner(win_obj):
    """Simplify dealing with _NET_WM_NAME (UTF-8) vs. WM_NAME (legacy)"""
    for atom in (NET_WM_NAME, WM_NAME):
        try:
            window_name = win_obj.get_full_property(atom, 0)
        except UnicodeDecodeError:  # Apparently a Debian distro package bug
            title = "<could not decode characters>"
        else:
            if window_name:
                win_name = window_name.value
                if isinstance(win_name, bytes):
                    # Apparently COMPOUND_TEXT is so arcane that this is how
                    # tools like xprop deal with receiving it these days
                    win_name = win_name.decode('latin1', 'replace')
                return win_name
            else:
                title = u"<unnamed window>"

    return "{} (XID: {})".format(title, win_obj.id)


def get_window_name(win_id):
    """Look up the window name for a given X11 window ID"""
    if not win_id:
        last_seen['title'] = "<no window id>"
        return last_seen['title']

    title_changed = False
    with window_obj(win_id) as wobj:
        if wobj:
            win_title = _get_window_name_inner(wobj)
            title_changed = (win_title != last_seen['title'])
            last_seen['title'] = win_title

    return last_seen['title'], title_changed


def handle_xevent(event):
    # Loop through, ignoring events until we're notified of focus/title change
    if event.type != Xlib.X.PropertyNotify:
        return

    changed = False
    if event.atom == NET_ACTIVE_WINDOW:
        if get_active_window()[1]:
            changed = changed or get_window_name(last_seen['xid'])[1]
    elif event.atom in (NET_WM_NAME, WM_NAME):
        changed = changed or get_window_name(last_seen['xid'])[1]

    if changed:
        handle_change(last_seen)


def add_app(window):
    # Gets app name from window title
    title = window['title']
    app_name = title.split(' - ')[-1]

    # Telegram
    telegram = re.compile('Telegram \(\d*\)')
    if re.match(telegram, app_name):
        app_name = 'Telegram'

    # Inserting into db
    cursor.execute("SELECT COUNT(1) FROM apps WHERE name = '{}'".format(app_name))
    exists = cursor.fetchone()[0]
    if exists == 0:
        cursor.execute("INSERT INTO apps (name) VALUES ('{}')".format(app_name))
        cnx.commit()
    else:
        pass

    return app_name


def idle_time():
    # Idle time count
    while True:
        wait = 5*60  # wait time in seconds before starting idle count
        done = 0
        while xprintidle.idle_time() > wait*1000:
            # getting time in previous window
            if done == 0:
                if previous['start'] is not None:
                    end = time.time()
                    time_length = (end - previous['start'] - wait)
                    print('Time in app/tab %s' % str(time_length))
                    previous['start'] = None
                    previous['app_name'] = None
                # starting idle
                print('Started idle')
                idle_start = time.time()
                done = 1
            while xprintidle.idle_time() < wait*1000:
                # ending idle
                idle_end = time.time()
                print('Ended idle')
                print('Time in idle: %s' % (idle_end - idle_start + wait))
                # getting window after idle end
                get_window_name(get_active_window()[0])
                handle_change(last_seen)
                done = 0
                break


def handle_change(new_state):
    app_name = add_app(new_state)
    if previous['start'] is not None and previous['app_name'] is not None:
        end = time.time()
        time_length = int(round(end - previous['start']))
        if extensions.status():
            if previous['app_name'] != 'Google Chrome' or (previous['app_name'] == 'Google Chrome' and app_name != 'Google Chrome'):
                cursor.execute("UPDATE sessions SET duration = {} WHERE user_id = 1 ORDER BY id DESC LIMIT 1".format(time_length))
                cnx.commit()
                print('time in %s: %s' % (str(previous['app_name']), str(time_length)))
        else:
            print('time in app: %s' % str(time_length))

    cursor.execute("SELECT id FROM apps WHERE name = '{}'".format(app_name))
    app_id = cursor.fetchone()[0]
    if extensions.status():
        if app_name != 'Google Chrome':
            cursor.execute("INSERT INTO sessions (user_id, date, app_id) VALUES (1, '{}', '{}')".format(datetime.datetime.today(), app_id))
            cnx.commit()
            print('New window active - xid: %d, title: %s' % (new_state['xid'], new_state['title']))
    else:
        print('New window active - xid: %d, title: %s' % (new_state['xid'], new_state['title']))

    previous['start'] = time.time()
    previous['app_name'] = app_name


def main_loop():
    while True:
        handle_xevent(disp.next_event())


def checkpw(email, password):
    cursor.execute("SELECT pwd_hash FROM users WHERE email = '{}'".format(email))
    if cursor.rowcount != 0:
        pwd_hash = cursor.fetchone()[0]
        password_bytes = bytes(password, encoding='utf-8')
        pwd_hash = bytes(pwd_hash, encoding='utf-8')
        check = bcrypt.checkpw(password_bytes, pwd_hash)
        return check
    else:
        return False


if __name__ == '__main__':
    while signin[0] == 0:
        email = input('Email: ')
        password = getpass()
        if checkpw(email, password):
            # Listen for _NET_ACTIVE_WINDOW changes
            root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

            # Prime last_seen with whatever window was active when we started this
            get_window_name(get_active_window()[0])
            handle_change(last_seen)

            t1 = Thread(target=main_loop)
            t2 = Thread(target=idle_time)
            t3 = Thread(target=extensions.extensions_main)
            t1.setDaemon(True)
            t2.setDaemon(True)
            t3.setDaemon(True)
            t1.start()
            t2.start()
            t3.start()
            signin[0] = 1
        else:
            print('Invalid email or password, try again')

    while True:
        pass

