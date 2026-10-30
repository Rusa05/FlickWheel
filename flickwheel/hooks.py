"""System-wide keyboard/mouse hooks running on their own thread.

The callbacks must return quickly (Windows drops slow hooks), so they only decide
whether to swallow an event and then emit a Qt signal for the GUI thread.
"""
import ctypes
import threading

from PySide6.QtCore import QObject, Signal

from . import winapi as w
from .keys import ALT, CTRL, MODIFIERS, SHIFT, WIN, is_modifier, normalise, sort_combo


def _mod_down(vk):
    if vk == WIN:
        return w.key_is_down(0x5B) or w.key_is_down(0x5C)
    return w.key_is_down(vk)


class InputHooks(QObject):
    trigger_down = Signal(str)        # "keyboard" or "mouse"
    trigger_up = Signal(str)
    cancel = Signal()                 # Esc / right click while the wheel is open
    record_progress = Signal(list)
    record_done = Signal(list)

    def __init__(self):
        super().__init__()
        self.kb_enabled = True
        self.kb_combo = [CTRL, 0x20]
        self.mouse_enabled = False
        self.mouse_button = "middle"
        self.excluded = set()
        self.pause_fullscreen = False
        self.paused = False
        self.wheel_open = False

        self._kb_active = False
        self._mouse_captured = False
        self._swallow_rclick_up = False
        self._recording = False
        self._rec_keys = []
        self._rec_down = set()
        self._swallow_ups = set()

        self._thread = None
        self._tid = None
        self._procs = []

    # ------------------------------------------------------------ config

    def apply_config(self, cfg):
        t = cfg["trigger"]
        self.kb_enabled = t["keyboard_enabled"] and bool(t["keyboard"])
        self.kb_combo = sort_combo(t["keyboard"])
        need_mouse = bool(t["mouse_enabled"])
        self.mouse_button = t["mouse"]
        self.excluded = {e.lower() for e in cfg["excluded_apps"]}
        self.pause_fullscreen = cfg["pause_fullscreen"]
        if self._thread is None or need_mouse != self.mouse_enabled:
            self.mouse_enabled = need_mouse
            self.restart()

    def blocked(self):
        if self.paused:
            return True
        fg = w.foreground_window()
        if self.excluded and w.window_process_name(fg) in self.excluded:
            return True
        return self.pause_fullscreen and w.is_fullscreen(fg)

    # ------------------------------------------------------------ recording

    def start_recording(self):
        self._rec_keys, self._rec_down = [], set()
        self._recording = True

    def stop_recording(self):
        self._recording = False

    def _record(self, vk, down):
        if down:
            if vk not in self._rec_down:
                self._rec_down.add(vk)
                if vk not in self._rec_keys:
                    self._rec_keys.append(vk)
                self.record_progress.emit(sort_combo(self._rec_keys))
                if not is_modifier(vk):
                    self._finish_record()
        else:
            self._rec_down.discard(vk)
            if not self._rec_down and self._rec_keys:
                self._finish_record()

    def _finish_record(self):
        self._recording = False
        self._swallow_ups = set(self._rec_down)
        self.record_done.emit(sort_combo(self._rec_keys))

    # ------------------------------------------------------------ callbacks

    def _on_key(self, vk, down):
        """Return True to swallow the event."""
        if self._recording:
            self._record(vk, down)
            return True
        if not down and vk in self._swallow_ups:
            self._swallow_ups.discard(vk)
            return True

        main = [k for k in self.kb_combo if not is_modifier(k)]
        main = main[-1] if main else None
        if main is not None and vk == main:
            if down:
                if self._kb_active:
                    return True  # auto-repeat while held
                if not self.kb_enabled:
                    return False
                wanted = set(self.kb_combo) - {main}
                held = {m for m in MODIFIERS if _mod_down(m)}
                if held != wanted or self.blocked():
                    return False
                self._kb_active = True
                self.trigger_down.emit("keyboard")
                return True
            if self._kb_active:
                self._kb_active = False
                self.trigger_up.emit("keyboard")
                return True
            return False

        if vk == 0x1B and down and self.wheel_open:
            self._swallow_ups.add(0x1B)
            self.cancel.emit()
            return True
        return False

    def _kb_proc(self, n, wparam, lparam):
        if n == 0:
            k = ctypes.cast(lparam, ctypes.POINTER(w.KBDLLHOOKSTRUCT)).contents
            if k.dwExtraInfo != w.INJECT_TAG:
                down = wparam in (w.WM_KEYDOWN, w.WM_SYSKEYDOWN)
                try:
                    if self._on_key(normalise(k.vkCode), down):
                        return 1
                except Exception:  # never let an exception kill input
                    pass
        return w.user32.CallNextHookEx(None, n, wparam, lparam)

    def _mouse_proc(self, n, wparam, lparam):
        if n == 0:
            m = ctypes.cast(lparam, ctypes.POINTER(w.MSLLHOOKSTRUCT)).contents
            if m.dwExtraInfo != w.INJECT_TAG:
                try:
                    if self._on_mouse(wparam, m.mouseData >> 16):
                        return 1
                except Exception:
                    pass
        return w.user32.CallNextHookEx(None, n, wparam, lparam)

    def _on_mouse(self, msg, xbutton):
        if msg == w.WM_RBUTTONDOWN and self.wheel_open:
            self._swallow_rclick_up = True
            self.cancel.emit()
            return True
        if msg == w.WM_RBUTTONUP and self._swallow_rclick_up:
            self._swallow_rclick_up = False
            return True
        if msg in (w.WM_MBUTTONDOWN, w.WM_MBUTTONUP):
            btn = "middle"
        elif msg in (w.WM_XBUTTONDOWN, w.WM_XBUTTONUP):
            btn = "x1" if xbutton == 1 else "x2"
        else:
            return False
        if btn != self.mouse_button:
            return False
        if msg in (w.WM_MBUTTONDOWN, w.WM_XBUTTONDOWN):
            if self.blocked() or self._recording:
                return False
            self._mouse_captured = True
            self.trigger_down.emit("mouse")
            return True
        if self._mouse_captured:
            self._mouse_captured = False
            self.trigger_up.emit("mouse")
            return True
        return False

    # ------------------------------------------------------------ thread

    def _run(self, with_mouse):
        self._tid = w.kernel32.GetCurrentThreadId()
        kb = w.HOOKPROC(self._kb_proc)
        procs = [kb]
        hooks = [w.user32.SetWindowsHookExW(w.WH_KEYBOARD_LL, kb, None, 0)]
        if with_mouse:
            ms = w.HOOKPROC(self._mouse_proc)
            procs.append(ms)
            hooks.append(w.user32.SetWindowsHookExW(w.WH_MOUSE_LL, ms, None, 0))
        self._procs = procs  # keep callbacks alive
        msg = w.wt.MSG()
        while w.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            pass
        for h in hooks:
            if h:
                w.user32.UnhookWindowsHookEx(h)

    def start(self):
        self._thread = threading.Thread(target=self._run, args=(self.mouse_enabled,),
                                        daemon=True, name="FlickWheelHooks")
        self._thread.start()

    def stop(self):
        if self._thread and self._tid:
            w.user32.PostThreadMessageW(self._tid, w.WM_QUIT, 0, 0)
            self._thread.join(1.0)
        self._thread, self._tid = None, None
        self._kb_active = self._mouse_captured = False

    def restart(self):
        self.stop()
        self.start()
