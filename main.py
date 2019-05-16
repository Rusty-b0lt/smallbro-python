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
import Xlib
import Xlib.display
import time
import xprintidle

# Connect to the X server and get the root window
disp = Xlib.display.Display()
root = disp.screen().root

# Prepare the property names we use so they can be fed into X11 APIs
NET_ACTIVE_WINDOW = disp.intern_atom('_NET_ACTIVE_WINDOW')
NET_WM_NAME = disp.intern_atom('_NET_WM_NAME')  # UTF-8
WM_NAME = disp.intern_atom('WM_NAME')           # Legacy encoding

last_seen = {'xid': None, 'title': None}
app_list = []
start = [None]
idle = [None]


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
    if app_name not in app_list:
        app_list.append(app_name)
        return app_name
    else:
        return None


def idle_time():
    # Idle time count
    while True:
        wait = 10  # wait time in seconds before starting idle count
        while xprintidle.idle_time() < wait*1000: # waiting for idle to start
            pass
        else:
            # getting time in previous window
            end = time.time()
            time_length = (end - start[0] - wait)
            print('Time in app %s' % str(time_length))
            start[0] = None
            # starting idle
            print('Started idle')
            idle_start = time.time()
            while xprintidle.idle_time() >= 10*1000: # waiting for user action
                pass
            else:
                # ending idle
                idle_end = time.time()
                print('Ended idle')
                print('Time in idle: %s' % (idle_end - idle_start + wait))
                # getting window after idle end
                get_window_name(get_active_window()[0])
                handle_change(last_seen)


def handle_change(new_state):
    if start[0] is not None:
        end = time.time()
        time_length = (end - start[0])
        print('time in app: %s' % str(time_length))

    app_name = add_app(new_state)
    if app_name is not None:
        print('New app opened: %s' % app_name)

    print('New window active - xid: %d, title: %s' % (new_state['xid'], new_state['title']))
    start[0] = time.time()


def main_loop():
        while True:
            handle_xevent(disp.next_event())


if __name__ == '__main__':
    # Listen for _NET_ACTIVE_WINDOW changes
    root.change_attributes(event_mask=Xlib.X.PropertyChangeMask)

    # Prime last_seen with whatever window was active when we started this
    get_window_name(get_active_window()[0])
    handle_change(last_seen)

    t1 = Thread(target=main_loop)
    t2 = Thread(target=idle_time)
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()
    while True:
        pass
