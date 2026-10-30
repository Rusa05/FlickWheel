"""Loading/saving settings (stored as JSON in %APPDATA%\\FlickWheel)."""
import copy
import json
import os

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "FlickWheel")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
ICON_DIR = os.path.join(CONFIG_DIR, "icons")

MIN_SLOTS, MAX_SLOTS = 4, 12


def slot(action, label=None, icon=None):
    from .actions import describe
    return {"label": label if label is not None else describe(action),
            "icon": icon or {"kind": "auto"},
            "action": action}


def empty_slot():
    return {"label": "", "icon": {"kind": "auto"}, "action": {"type": "none"}}


def _default_wheel():
    media = [slot({"type": "media", "id": i}) for i in
             ("play_pause", "next", "vol_up", "mute", "vol_down", "prev")]
    return [
        slot({"type": "system", "id": "task_view"}),
        slot({"type": "folder", "slots": media}, label="Media", icon={"kind": "builtin", "name": "music"}),
        slot({"type": "system", "id": "next_desktop"}, label="Next desktop"),
        slot({"type": "system", "id": "screenshot"}, label="Screenshot"),
        slot({"type": "system", "id": "show_desktop"}),
        slot({"type": "system", "id": "explorer"}),
        slot({"type": "system", "id": "prev_desktop"}, label="Prev desktop"),
        slot({"type": "url", "target": "https://www.google.com"}, label="Browser"),
    ]


def default_config():
    return {
        "version": 1,
        "trigger": {
            "keyboard_enabled": True,
            "keyboard": [0x11, 0x20],  # Ctrl + Space
            "mouse_enabled": False,
            "mouse": "middle",  # middle | x1 | x2
        },
        "flick_to_fire": True,
        "flick_distance": 40,   # px beyond the ring's edge before firing instantly
        "folder_hover_ms": 350,
        "size": 100,            # percent
        "blur": True,
        "excluded_apps": [],
        "pause_fullscreen": False,
        "slots": _default_wheel(),
    }


def _merge(defaults, loaded):
    out = copy.deepcopy(defaults)
    for k, v in loaded.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return _merge(default_config(), json.load(f))
    except (OSError, ValueError):
        return default_config()


def save(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_PATH)
