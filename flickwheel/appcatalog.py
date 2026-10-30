"""List of installed apps (everything in the Start menu, including Store apps)."""
import json
import os
import subprocess
import threading

from PySide6.QtCore import QObject, Signal

from .config import CONFIG_DIR

CACHE = os.path.join(CONFIG_DIR, "apps.json")

_PS = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
       "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress")


class AppCatalog(QObject):
    updated = Signal(list)

    def __init__(self):
        super().__init__()
        self.apps = self._load_cache()
        self._loading = False

    @staticmethod
    def _load_cache():
        try:
            with open(CACHE, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS],
                                 capture_output=True, timeout=30,
                                 creationflags=subprocess.CREATE_NO_WINDOW).stdout
            data = json.loads(out.decode("utf-8-sig") or "[]")
            if isinstance(data, dict):
                data = [data]
            skip = ("uninstall", "readme", "help", "documentation", "release notes")
            apps, seen = [], set()
            for a in data:
                name, appid = a.get("Name") or "", a.get("AppID") or ""
                if not name or not appid or any(s in name.lower() for s in skip):
                    continue
                if appid.lower().startswith(("http://", "https://")):
                    continue
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                apps.append({"name": name, "target": "shell:AppsFolder\\" + appid})
            apps.sort(key=lambda x: x["name"].lower())
            self.apps = apps
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CACHE, "w", encoding="utf-8") as f:
                json.dump(apps, f)
            self.updated.emit(apps)
        except Exception:
            pass
        finally:
            self._loading = False
