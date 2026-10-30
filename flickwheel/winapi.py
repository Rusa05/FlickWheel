"""Thin ctypes wrappers around the bits of the Windows API FlickWheel needs."""
import ctypes
import os
import sys
import winreg
from ctypes import wintypes as wt

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
ULONG_PTR = ctypes.c_size_t

# Tag put on every input event we inject so our own hooks can ignore it.
INJECT_TAG = 0xF11C_0001

# ---------------------------------------------------------------- structures


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wt.POINT), ("mouseData", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT),
                ("dwFlags", wt.DWORD)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetForegroundWindow.restype = wt.HWND
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.MonitorFromWindow.restype = wt.HMONITOR
user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.MapVirtualKeyW.argtypes = [wt.UINT, wt.UINT]
user32.GetKeyNameTextW.argtypes = [wt.LONG, wt.LPWSTR, ctypes.c_int]
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindow.argtypes = [wt.HWND, wt.UINT]
user32.GetWindow.restype = wt.HWND
user32.SetWindowRgn.argtypes = [wt.HWND, wt.HRGN, wt.BOOL]
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
user32.GetAncestor.restype = wt.HWND
user32.GetShellWindow.restype = wt.HWND
gdi32.CreateEllipticRgn.argtypes = [ctypes.c_int] * 4
gdi32.CreateEllipticRgn.restype = wt.HRGN
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR,
                                                ctypes.POINTER(wt.DWORD)]
kernel32.GetCurrentThreadId.restype = wt.DWORD

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_QUIT = 0x0012
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
WM_MBUTTONDOWN, WM_MBUTTONUP = 0x207, 0x208
WM_XBUTTONDOWN, WM_XBUTTONUP = 0x20B, 0x20C
WM_RBUTTONDOWN, WM_RBUTTONUP = 0x204, 0x205

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP = 0x1, 0x2
MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP = 0x20, 0x40
MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP = 0x80, 0x100

# Keys whose scan codes need the "extended" flag to be sent correctly.
EXTENDED_VKS = {0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E,
                0x6F, 0x90, 0x5B, 0x5C, 0x5D, 0xA3, 0xA5, 0x2C,
                0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF,
                0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7}


def key_is_down(vk):
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def _key_input(vk, up):
    flags = KEYEVENTF_KEYUP if up else 0
    if vk in EXTENDED_VKS:
        flags |= KEYEVENTF_EXTENDEDKEY
    scan = user32.MapVirtualKeyW(vk, 0) & 0xFF
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(vk, scan, flags, 0, INJECT_TAG)
    return inp


def send_keys(events):
    """events: list of (vk, is_up)."""
    if not events:
        return
    arr = (INPUT * len(events))(*[_key_input(vk, up) for vk, up in events])
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def send_combo(vks):
    """Press all keys in order, release in reverse order."""
    send_keys([(vk, False) for vk in vks] + [(vk, True) for vk in reversed(vks)])


def send_mouse_click(button):
    """Re-play a click for a mouse button we swallowed ('middle', 'x1', 'x2')."""
    if button == "middle":
        down, up, data = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP, 0
    else:
        down, up, data = MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP, 1 if button == "x1" else 2
    arr = (INPUT * 2)()
    for i, flag in enumerate((down, up)):
        arr[i].type = INPUT_MOUSE
        arr[i].mi = MOUSEINPUT(0, 0, data, flag, 0, INJECT_TAG)
    user32.SendInput(2, arr, ctypes.sizeof(INPUT))


# ----------------------------------------------------------- window/process


def foreground_window():
    return user32.GetForegroundWindow()


def window_process_name(hwnd):
    """Lower-case exe name (e.g. 'chrome.exe') of the process owning hwnd."""
    if not hwnd:
        return ""
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value).lower()
    finally:
        kernel32.CloseHandle(h)
    return ""


def window_process_path(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
    finally:
        kernel32.CloseHandle(h)
    return ""


def is_fullscreen(hwnd):
    """True if hwnd covers its whole monitor (games, full-screen video...)."""
    if not hwnd or hwnd == user32.GetShellWindow():
        return False
    cls = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, cls, 64)
    if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd"):
        return False
    rect = wt.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    mon = user32.MonitorFromWindow(hwnd, 2)
    mi = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
    if not user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
        return False
    m = mi.rcMonitor
    return (rect.left <= m.left and rect.top <= m.top and
            rect.right >= m.right and rect.bottom >= m.bottom)


EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def running_window_apps():
    """{exe_name: full_path} for every process that has a visible top-level window."""
    found = {}

    def cb(hwnd, _):
        if (user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0
                and not user32.GetWindow(hwnd, 4)):  # GW_OWNER
            path = window_process_path(hwnd)
            if path:
                found.setdefault(os.path.basename(path).lower(), path)
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def minimize_window(hwnd):
    user32.ShowWindow(hwnd, 6)


def lock_workstation():
    user32.LockWorkStation()


# ------------------------------------------------------------- appearance


def exclude_from_capture(hwnd):
    """Keep a window out of screenshots/screen grabs (WDA_EXCLUDEFROMCAPTURE)."""
    user32.SetWindowDisplayAffinity(wt.HWND(hwnd), 0x11)


def system_uses_light_theme():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            return winreg.QueryValueEx(k, "AppsUseLightTheme")[0] == 1
    except OSError:
        return False


def accent_color():
    """Windows accent colour as (r, g, b)."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM") as k:
            v = winreg.QueryValueEx(k, "AccentColor")[0]  # 0xAABBGGRR
            return (v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)
    except OSError:
        return (0, 120, 212)


# ------------------------------------------------------------- startup


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_NAME = "FlickWheel"


def pythonw_and_main():
    """(pythonw.exe path, main.py path): runs FlickWheel without a console window."""
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    main = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return exe, main


def startup_command():
    exe, main = pythonw_and_main()
    return f'"{exe}" "{main}" --background'


def set_start_with_windows(enabled):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, _RUN_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(k, _RUN_NAME)
            except FileNotFoundError:
                pass


def starts_with_windows():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _RUN_NAME)
            return True
    except OSError:
        return False


# ------------------------------------------------------------- shell icons


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wt.LONG), ("cy", wt.LONG)]


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD), ("Data3", wt.WORD),
                ("Data4", ctypes.c_ubyte * 8)]


def _guid(s):
    import uuid
    u = uuid.UUID(s)
    g = GUID()
    g.Data1, g.Data2, g.Data3 = u.fields[0], u.fields[1], u.fields[2]
    for i, b in enumerate(u.bytes[8:]):
        g.Data4[i] = b
    return g


_IID_IShellItemImageFactory = _guid("bcc18b79-ba16-442f-80c4-8a59c30c463b")


class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", wt.LONG), ("bmWidth", wt.LONG), ("bmHeight", wt.LONG),
                ("bmWidthBytes", wt.LONG), ("bmPlanes", wt.WORD), ("bmBitsPixel", wt.WORD),
                ("bmBits", ctypes.c_void_p)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


shell32.SHCreateItemFromParsingName.argtypes = [wt.LPCWSTR, ctypes.c_void_p,
                                                ctypes.POINTER(GUID),
                                                ctypes.POINTER(ctypes.c_void_p)]
gdi32.GetObjectW.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p]
gdi32.GetDIBits.argtypes = [wt.HDC, wt.HBITMAP, wt.UINT, wt.UINT, ctypes.c_void_p,
                            ctypes.c_void_p, wt.UINT]
gdi32.DeleteObject.argtypes = [wt.HANDLE]
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]

_GetImageProto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, SIZE, ctypes.c_int,
                                    ctypes.POINTER(wt.HBITMAP))
_ReleaseProto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)


def shell_icon_bgra(path, size=64):
    """Return (width, height, bytes BGRA premultiplied top-down) for any shell item
    (exe, lnk, file, folder or shell:AppsFolder\\<id>), or None."""
    ptr = ctypes.c_void_p()
    hr = shell32.SHCreateItemFromParsingName(path, None, ctypes.byref(_IID_IShellItemImageFactory),
                                             ctypes.byref(ptr))
    if hr != 0 or not ptr:
        return None
    try:
        vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        get_image = _GetImageProto(vtbl[3])
        hbmp = wt.HBITMAP()
        # SIIGBF_BIGGERSIZEOK (1) | SIIGBF_ICONONLY (4)
        if get_image(ptr, SIZE(size, size), 0x5, ctypes.byref(hbmp)) != 0:
            return None
        try:
            bm = BITMAP()
            gdi32.GetObjectW(hbmp, ctypes.sizeof(bm), ctypes.byref(bm))
            w, h = bm.bmWidth, bm.bmHeight
            bih = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
            buf = ctypes.create_string_buffer(w * h * 4)
            hdc = user32.GetDC(None)
            gdi32.GetDIBits(hdc, hbmp, 0, h, buf, ctypes.byref(bih), 0)
            user32.ReleaseDC(None, hdc)
            return w, h, buf.raw
        finally:
            gdi32.DeleteObject(hbmp)
    finally:
        _ReleaseProto(ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents[2])(ptr)
