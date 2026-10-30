"""What each slot can do, and the code that does it."""
import os
import subprocess
import threading
import webbrowser

from . import winapi
from .keys import ALT, CTRL, SHIFT, WIN

# Action types, in the order shown in the settings window.
#   key: (label shown to the user, hint under the picker)
ACTION_TYPES = {
    "app": ("Open an app", "Pick any installed app."),
    "file": ("Open a file or folder", "Opens with its normal program."),
    "url": ("Open a website", "Opens in your default browser."),
    "system": ("Windows gesture", "Trackpad-style gestures and Windows features."),
    "keys": ("Press a keyboard shortcut", "Sends the keys to the app you're using."),
    "media": ("Media & volume", "Control music, videos and volume."),
    "folder": ("Folder (opens another wheel)", "Flick into it to open a second wheel."),
    "none": ("Nothing", "Leave this slot empty."),
}

V_LEFT, V_UP, V_RIGHT, V_DOWN, V_TAB = 0x25, 0x26, 0x27, 0x28, 0x09

# id: (name, description, icon, keys-or-callable)
SYSTEM_ACTIONS = {
    "task_view": ("Show all windows", "Like swiping up with three fingers", "windows",
                  [WIN, V_TAB]),
    "show_desktop": ("Show desktop", "Like swiping down with three fingers", "desktop",
                     [WIN, 0x44]),
    "next_desktop": ("Next virtual desktop", "Like swiping left with four fingers",
                     "arrow-right", [WIN, CTRL, V_RIGHT]),
    "prev_desktop": ("Previous virtual desktop", "Like swiping right with four fingers",
                     "arrow-left", [WIN, CTRL, V_LEFT]),
    "new_desktop": ("New virtual desktop", "Win + Ctrl + D", "plus", [WIN, CTRL, 0x44]),
    "close_desktop": ("Close virtual desktop", "Win + Ctrl + F4", "x", [WIN, CTRL, 0x73]),
    "last_app": ("Switch to last app", "Like a quick Alt + Tab", "switch", [ALT, V_TAB]),
    "app_switcher": ("App switcher", "Stays open so you can pick an app", "switch",
                     [CTRL, ALT, V_TAB]),
    "back": ("Back", "Like swiping right with two fingers (browsers, Explorer)",
             "arrow-left", [0xA6]),
    "forward": ("Forward", "Like swiping left with two fingers", "arrow-right", [0xA7]),
    "refresh": ("Refresh", "Reload the page or folder", "refresh", [0x74]),
    "zoom_in": ("Zoom in", "Like pinching out (Ctrl + Plus)", "zoom-in", [CTRL, 0xBB]),
    "zoom_out": ("Zoom out", "Like pinching in (Ctrl + Minus)", "zoom-out", [CTRL, 0xBD]),
    "snap_left": ("Snap window left", "Win + Left", "snap-left", [WIN, V_LEFT]),
    "snap_right": ("Snap window right", "Win + Right", "snap-right", [WIN, V_RIGHT]),
    "maximize": ("Maximise window", "Win + Up", "maximize", [WIN, V_UP]),
    "minimize": ("Minimise window", "Hide the window you're using", "minimize",
                 lambda: winapi.minimize_window(winapi.foreground_window())),
    "snap_layouts": ("Snap layouts", "Win + Z", "layout", [WIN, 0x5A]),
    "close_window": ("Close window", "Alt + F4", "x", [ALT, 0x73]),
    "screenshot": ("Screenshot (Snipping Tool)", "Win + Shift + S", "camera",
                   [WIN, SHIFT, 0x53]),
    "start": ("Start menu", "Win", "grid", [WIN]),
    "search": ("Search", "Win + S", "search", [WIN, 0x53]),
    "explorer": ("File Explorer", "Win + E", "folder", [WIN, 0x45]),
    "settings": ("Windows Settings", "Win + I", "settings", [WIN, 0x49]),
    "notifications": ("Notifications & calendar", "Like swiping in from the right edge",
                      "bell", [WIN, 0x4E]),
    "quick_settings": ("Quick settings (Wi-Fi, sound)", "Win + A", "sliders", [WIN, 0x41]),
    "widgets": ("Widgets", "Like swiping in from the left edge", "layout", [WIN, 0x57]),
    "clipboard": ("Clipboard history", "Win + V", "clipboard", [WIN, 0x56]),
    "emoji": ("Emoji panel", "Win + .", "smile", [WIN, 0xBE]),
    "task_manager": ("Task Manager", "Ctrl + Shift + Esc", "activity",
                     [CTRL, SHIFT, 0x1B]),
    "run": ("Run dialog", "Win + R", "terminal", [WIN, 0x52]),
    "lock": ("Lock PC", "Win + L", "lock", winapi.lock_workstation),
}

MEDIA_ACTIONS = {
    "play_pause": ("Play / pause", "play", 0xB3),
    "next": ("Next track", "next", 0xB0),
    "prev": ("Previous track", "prev", 0xB1),
    "stop": ("Stop", "stop", 0xB2),
    "vol_up": ("Volume up", "volume-up", 0xAF),
    "vol_down": ("Volume down", "volume-down", 0xAE),
    "mute": ("Mute", "volume-mute", 0xAD),
}


def describe(action):
    """Default label for an action."""
    t = action.get("type", "none")
    if t == "system":
        return SYSTEM_ACTIONS.get(action.get("id"), ("Gesture",))[0]
    if t == "media":
        return MEDIA_ACTIONS.get(action.get("id"), ("Media",))[0]
    if t == "app":
        return action.get("name") or "App"
    if t == "file":
        target = action.get("target", "").rstrip("\\/")
        return os.path.basename(target) or target or "File"
    if t == "url":
        u = action.get("target", "")
        for p in ("https://", "http://", "www."):
            if u.startswith(p):
                u = u[len(p):]
        return u.split("/")[0] or "Website"
    if t == "keys":
        from .keys import combo_text
        return combo_text(action.get("vks", []))
    if t == "folder":
        return "Folder"
    return ""


def default_builtin_icon(action):
    t = action.get("type", "none")
    if t == "system":
        return SYSTEM_ACTIONS.get(action.get("id"), (0, 0, "star"))[2]
    if t == "media":
        return MEDIA_ACTIONS.get(action.get("id"), (0, "music"))[1]
    return {"app": "grid", "file": "file", "url": "globe", "keys": "keyboard",
            "folder": "folder-open", "none": ""}.get(t, "star")


def is_runnable(action):
    t = action.get("type", "none")
    if t in ("app", "file", "url"):
        return bool(action.get("target"))
    if t == "keys":
        return bool(action.get("vks"))
    if t == "system":
        return action.get("id") in SYSTEM_ACTIONS
    if t == "media":
        return action.get("id") in MEDIA_ACTIONS
    return False


def release_held_modifiers():
    """If the user is still holding the trigger (e.g. Ctrl), let the OS think it's up
    so the action's own key combo isn't mixed with it."""
    ups = []
    for vk in (0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x5B, 0x5C):
        if winapi.key_is_down(vk):
            ups.append((vk, True))
    if ups:
        # A harmless key tap stops a lone Alt/Win release from opening menus/Start.
        winapi.send_keys([(0xE8, False), (0xE8, True)] + ups)


def run(action):
    """Execute an action. Never raises; returns an error string or None."""
    t = action.get("type", "none")
    try:
        if t in ("system", "keys", "media"):
            release_held_modifiers()
        if t == "system":
            what = SYSTEM_ACTIONS[action["id"]][3]
            if callable(what):
                what()
            else:
                winapi.send_combo(what)
        elif t == "media":
            winapi.send_combo([MEDIA_ACTIONS[action["id"]][2]])
        elif t == "keys":
            winapi.send_combo(action.get("vks", []))
        elif t in ("app", "file"):
            target = action.get("target", "")
            args = action.get("args", "").strip()
            if args:
                subprocess.Popen(f'"{target}" {args}', shell=False)
            else:
                os.startfile(target)  # releases the GIL, so hooks stay responsive
        elif t == "url":
            url = action.get("target", "").strip()
            if url and "://" not in url:
                url = "https://" + url
            threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    except Exception as e:  # noqa: BLE001 - surface any failure to the user
        return str(e)
    return None
