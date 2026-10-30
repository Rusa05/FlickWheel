"""Start menu / Desktop shortcuts so FlickWheel opens like a regular app."""
import os
import subprocess
import threading

from .config import CONFIG_DIR
from .winapi import pythonw_and_main

ICON_PATH = os.path.join(CONFIG_DIR, "FlickWheel.ico")
START_MENU = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs",
                          "FlickWheel.lnk")
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop", "FlickWheel.lnk")


def save_icon(pixmap):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    pixmap.save(ICON_PATH, "ICO")


def _desktop_dir():
    # The Desktop may be redirected (e.g. into OneDrive).
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "[Environment]::GetFolderPath('Desktop')"],
                             capture_output=True, text=True, timeout=15,
                             creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
        return out or os.path.dirname(DESKTOP)
    except Exception:
        return os.path.dirname(DESKTOP)


def _create(lnk_path):
    exe, main = pythonw_and_main()
    args, workdir = f'"{main}"', os.path.dirname(main)
    ps =("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:FW_LNK);"
          "$s.TargetPath=$env:FW_EXE;$s.Arguments=$env:FW_ARGS;"
          "$s.WorkingDirectory=$env:FW_DIR;$s.IconLocation=$env:FW_ICO;"
          "$s.Description='FlickWheel - radial action wheel';$s.Save()")
    env = dict(os.environ, FW_LNK=lnk_path, FW_EXE=exe, FW_ARGS=args, FW_DIR=workdir,
               FW_ICO=ICON_PATH)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], env=env,
                   timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)


def ensure_shortcuts(desktop=False, on_desktop_done=None):
    """Create the Start menu shortcut (and optionally a Desktop one) in the background."""
    def work():
        try:
            if not os.path.exists(START_MENU):
                _create(START_MENU)
            if desktop:
                d = os.path.join(_desktop_dir(), "FlickWheel.lnk")
                if not os.path.exists(d):
                    _create(d)
                if os.path.exists(d) and on_desktop_done:
                    on_desktop_done()
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()
