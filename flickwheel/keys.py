"""Virtual-key helpers: names for display and normalising left/right modifiers."""
import ctypes

from . import winapi

SHIFT, CTRL, ALT, WIN = 0x10, 0x11, 0x12, 0x5B
MODIFIERS = (CTRL, ALT, SHIFT, WIN)  # display order

_NORMALISE = {0xA0: SHIFT, 0xA1: SHIFT, 0xA2: CTRL, 0xA3: CTRL,
              0xA4: ALT, 0xA5: ALT, 0x5C: WIN}

_NAMES = {
    SHIFT: "Shift", CTRL: "Ctrl", ALT: "Alt", WIN: "Win",
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x13: "Pause", 0x14: "Caps Lock",
    0x1B: "Esc", 0x20: "Space", 0x21: "Page Up", 0x22: "Page Down", 0x23: "End",
    0x24: "Home", 0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down",
    0x2C: "Print Screen", 0x2D: "Insert", 0x2E: "Delete", 0x5D: "Menu",
    0x6A: "Num *", 0x6B: "Num +", 0x6D: "Num -", 0x6E: "Num .", 0x6F: "Num /",
    0x90: "Num Lock", 0x91: "Scroll Lock",
    0xA6: "Browser Back", 0xA7: "Browser Forward", 0xA8: "Browser Refresh",
    0xAD: "Mute", 0xAE: "Volume Down", 0xAF: "Volume Up",
    0xB0: "Next Track", 0xB1: "Previous Track", 0xB2: "Stop", 0xB3: "Play/Pause",
    0xBA: ";", 0xBB: "=", 0xBC: ",", 0xBD: "-", 0xBE: ".", 0xBF: "/", 0xC0: "`",
    0xDB: "[", 0xDC: "\\", 0xDD: "]", 0xDE: "'",
}
for _i in range(24):
    _NAMES[0x70 + _i] = f"F{_i + 1}"
for _i in range(10):
    _NAMES[0x60 + _i] = f"Num {_i}"


def normalise(vk):
    return _NORMALISE.get(vk, vk)


def is_modifier(vk):
    return normalise(vk) in MODIFIERS


def key_name(vk):
    vk = normalise(vk)
    if vk in _NAMES:
        return _NAMES[vk]
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    scan = winapi.user32.MapVirtualKeyW(vk, 0)
    buf = ctypes.create_unicode_buffer(32)
    if scan and winapi.user32.GetKeyNameTextW(scan << 16, buf, 32):
        return buf.value
    return f"Key {vk:#04x}"


def sort_combo(vks):
    """Modifiers first (Ctrl, Alt, Shift, Win), then the rest in press order."""
    vks = [normalise(v) for v in vks]
    mods = [m for m in MODIFIERS if m in vks]
    rest = [v for v in vks if v not in MODIFIERS]
    out = []
    for v in mods + rest:
        if v not in out:
            out.append(v)
    return out


def combo_text(vks):
    if not vks:
        return "Not set"
    return " + ".join(key_name(v) for v in sort_combo(vks))
