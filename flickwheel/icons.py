"""Built-in line icons (24x24 SVG, stroked in the current colour) and app icons."""
import os

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from . import winapi
from .actions import default_builtin_icon

ICONS = {
    # windows & system
    "windows": '<rect x="3" y="7" width="14" height="11" rx="2"/><path d="M7 7V5a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-3"/>',
    "desktop": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    "grid": '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
    "layout": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M12 4v16M12 12h9"/>',
    "snap-left": '<rect x="3" y="4" width="18" height="16" rx="2"/><rect x="6" y="7" width="5" height="10" rx="1" fill="currentColor" stroke="none"/>',
    "snap-right": '<rect x="3" y="4" width="18" height="16" rx="2"/><rect x="13" y="7" width="5" height="10" rx="1" fill="currentColor" stroke="none"/>',
    "maximize": '<path d="M9 4H4v5M15 4h5v5M9 20H4v-5M15 20h5v-5"/>',
    "minimize": '<path d="M5 18h14"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "switch": '<path d="M4 8h13M13 4l4 4-4 4M20 16H7M11 12l-4 4 4 4"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
    "zoom-in": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4M8 11h6M11 8v6"/>',
    "zoom-out": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4M8 11h6"/>',
    "camera": '<path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "folder-open": '<path d="M3 19V7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v1M3 19l2.6-7.3a1 1 0 0 1 1-.7H21l-2.6 7.3a1 1 0 0 1-1 .7z"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "bell": '<path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2.5" width="6" height="3.5" rx="1"/><path d="M9 11h6M9 15h4"/>',
    "smile": '<circle cx="12" cy="12" r="9"/><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0M9 9.5h.01M15 9.5h.01"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "power": '<path d="M12 3v9"/><path d="M6.3 7a8 8 0 1 0 11.4 0"/>',
    "moon": '<path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z"/>',
    # media
    "music": '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "next": '<path d="M5 5l10 7-10 7z"/><path d="M19 5v14"/>',
    "prev": '<path d="M19 5L9 12l10 7z"/><path d="M5 5v14"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
    "volume-up": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>',
    "volume-down": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>',
    "volume-mute": '<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16 9l5 6M21 9l-5 6"/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3z"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
    # general
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "file": '<path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5"/>',
    "keyboard": '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    "heart": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    "home": '<path d="M4 11l8-7 8 7v9H4z"/><path d="M10 20v-5h4v5"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4z"/>',
    "code": '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>',
    "calculator": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 12h.01M12 12h.01M16 12h.01M8 16h.01M12 16h.01M16 16h.01"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "game": '<path d="M6 8h12a4 4 0 0 1 4 4v1a3 3 0 0 1-5.4 1.8L15 13H9l-1.6 1.8A3 3 0 0 1 2 13v-1a4 4 0 0 1 4-4z"/><path d="M7 10v3M5.5 11.5h3M16 11h.01M18 12.5h.01"/>',
    "download": '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    "bolt": '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
    "pen": '<path d="M4 20l4-1 11-11-3-3L5 16z"/>',
    "bookmark": '<path d="M6 3h12v18l-6-4-6 4z"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    "undo": '<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    "redo": '<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>',
}

_svg_cache = {}
_shell_cache = {}


def svg_pixmap(name, size, color, dpr=1.0):
    color = QColor(color)
    key = (name, size, color.rgba(), dpr)
    if key in _svg_cache:
        return _svg_cache[key]
    body = ICONS.get(name, ICONS["star"]).replace("currentColor", color.name())
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color.name()}" stroke-width="2" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    px = int(size * dpr)
    img = QImage(px, px, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, px, px))
    p.end()
    pm = QPixmap.fromImage(img)
    pm.setDevicePixelRatio(dpr)
    _svg_cache[key] = pm
    return pm


def shell_pixmap(path, size, dpr=1.0):
    """Icon Windows shows for a file, folder, app or shell:AppsFolder item."""
    px = int(size * dpr)
    key = (path, px)
    if key in _shell_cache:
        return _shell_cache[key]
    pm = None
    try:
        res = winapi.shell_icon_bgra(path, max(px, 48))
        if res:
            w, h, data = res
            img = QImage(data, w, h, QImage.Format_ARGB32_Premultiplied).copy()
            pm = QPixmap.fromImage(img.scaled(px, px, Qt.KeepAspectRatio,
                                              Qt.SmoothTransformation))
            pm.setDevicePixelRatio(dpr)
    except Exception:
        pm = None
    _shell_cache[key] = pm
    return pm


def file_pixmap(path, size, dpr=1.0):
    img = QImage(path)
    if img.isNull():
        return None
    px = int(size * dpr)
    pm = QPixmap.fromImage(img.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    pm.setDevicePixelRatio(dpr)
    return pm


def slot_pixmap(slot, size, color, dpr=1.0):
    """The picture to draw for a wheel slot, or None for an empty slot."""
    icon = slot.get("icon") or {"kind": "auto"}
    action = slot.get("action", {})
    kind = icon.get("kind", "auto")
    if kind == "builtin" and icon.get("name"):
        return svg_pixmap(icon["name"], size, color, dpr)
    if kind == "file" and icon.get("path") and os.path.exists(icon["path"]):
        pm = file_pixmap(icon["path"], size, dpr)
        if pm:
            return pm
    if action.get("type") in ("app", "file") and action.get("target"):
        pm = shell_pixmap(action["target"], size, dpr)
        if pm:
            return pm
    name = default_builtin_icon(action)
    return svg_pixmap(name, size, color, dpr) if name else None
