"""Custom widgets used by the settings window."""
import math
import os
import shutil
import uuid

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, QTimer,
                            Signal)
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtWidgets import (QAbstractButton, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from . import icons
from .config import ICON_DIR
from .keys import combo_text, is_modifier
from .wheel import Theme, paint_wheel, slot_index, ui_accent


class ToggleSwitch(QAbstractButton):
    """A pill-shaped on/off switch with a sliding knob."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self, duration=160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on):
        self._anim.stop()
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def setChecked(self, on):
        super().setChecked(on)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def _get(self):
        return self._pos

    def _set(self, v):
        self._pos = v
        self.update()

    knob = Property(float, _get, _set)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        dark = Theme().dark
        off = QColor(255, 255, 255, 40) if dark else QColor(0, 0, 0, 40)
        on = ui_accent()
        t = self._pos
        track = QColor(int(off.red() + (on.red() - off.red()) * t),
                       int(off.green() + (on.green() - off.green()) * t),
                       int(off.blue() + (on.blue() - off.blue()) * t),
                       int(off.alpha() + (255 - off.alpha()) * t))
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + (r.width() - d - 6) * t
        if self.underMouse():
            glow = QColor(on)
            glow.setAlpha(60)
            p.setBrush(glow)
            p.drawEllipse(QRectF(x - 3, r.top(), d + 6, d + 6))
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


class KeyRecorder(QPushButton):
    """Click it, press a key combo, done. Uses the global hook so even Win+Tab works."""

    combo_changed = Signal(list)

    def __init__(self, hooks, need_main_key=False, parent=None):
        super().__init__(parent)
        self.hooks = hooks
        self.need_main_key = need_main_key
        self.combo = []
        self.recording = False
        self.setObjectName("recorder")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.clicked.connect(self.start)
        self._timeout = QTimer(self, singleShot=True, interval=8000)
        self._timeout.timeout.connect(self.cancel)
        self._refresh()

    def set_combo(self, vks):
        self.combo = list(vks)
        self._refresh()

    def _refresh(self, text=None):
        self.setProperty("recording", self.recording)
        self.style().unpolish(self)
        self.style().polish(self)
        if text is None:
            text = combo_text(self.combo) if self.combo else "Click to set a shortcut"
        self.setText(text)

    def start(self):
        if self.recording:
            return self.cancel()
        self.recording = True
        self.hooks.record_progress.connect(self._progress)
        self.hooks.record_done.connect(self._done)
        self.hooks.start_recording()
        self._timeout.start()
        self._refresh("Press your keys now…")

    def _disconnect(self):
        try:
            self.hooks.record_progress.disconnect(self._progress)
            self.hooks.record_done.disconnect(self._done)
        except (RuntimeError, TypeError):
            pass

    def cancel(self):
        self.hooks.stop_recording()
        self._disconnect()
        self.recording = False
        self._timeout.stop()
        self._refresh()

    def _progress(self, vks):
        self._refresh(combo_text(vks) + " …")

    def _done(self, vks):
        self._disconnect()
        self.recording = False
        self._timeout.stop()
        if self.need_main_key and all(is_modifier(v) for v in vks):
            self._refresh("Needs a normal key too, e.g. Ctrl + Space")
            QTimer.singleShot(2200, self._refresh)
            return
        self.combo = vks
        self._refresh()
        self.combo_changed.emit(vks)

    def hideEvent(self, e):
        if self.recording:
            self.cancel()
        super().hideEvent(e)


class WheelPreview(QWidget):
    """Interactive wheel: click a slot to select, drag onto another to swap,
    double-click a folder to open it, click the centre to go back."""

    selected = Signal(int)
    swapped = Signal(int, int)
    open_folder = Signal(int)
    back = Signal()

    def __init__(self, interactive=True, parent=None):
        super().__init__(parent)
        self.interactive = interactive
        self.slots, self.title = [], ""
        self.sel, self.hover = -1, -1
        self.scale = 1.0
        self._press, self._drag_from, self._drop = None, -1, -1
        self.setMouseTracking(True)
        self.setMinimumSize(360, 360)

    def set_slots(self, slots, title="", selected=-1):
        self.slots, self.title, self.sel = slots, title, selected
        self.update()

    def _geom(self):
        side = min(self.width(), self.height())
        R = (side / 2 - 8) * self.scale
        return self.width() / 2, self.height() / 2, R, R * 0.35

    def _index_at(self, pos):
        cx, cy, R, hub = self._geom()
        dx, dy = pos.x() - cx, pos.y() - cy
        d = math.hypot(dx, dy)
        if d < hub:
            return "hub"
        if d > R or not self.slots:
            return -1
        return slot_index(dx, dy, len(self.slots))

    def mouseMoveEvent(self, e):
        if not self.interactive:
            return
        i = self._index_at(e.position())
        if self._press is not None and isinstance(self._drag_from, int) and self._drag_from >= 0:
            if (e.position() - self._press).manhattanLength() > 6:
                self._drop = i if isinstance(i, int) and i != self._drag_from else -1
                self.setCursor(Qt.ClosedHandCursor)
        hov = i if isinstance(i, int) else -1
        if hov != self.hover:
            self.hover = hov
            self.setCursor(Qt.PointingHandCursor if (hov >= 0 or (i == "hub" and self.title))
                           else Qt.ArrowCursor)
        self.update()

    def leaveEvent(self, _):
        self.hover = -1
        self.update()

    def mousePressEvent(self, e):
        if not self.interactive or e.button() != Qt.LeftButton:
            return
        i = self._index_at(e.position())
        self._press = e.position()
        self._drag_from = i if isinstance(i, int) else -1
        self._drop = -1

    def mouseReleaseEvent(self, e):
        if not self.interactive or self._press is None:
            return
        i = self._index_at(e.position())
        if self._drop >= 0 and self._drag_from >= 0:
            self.swapped.emit(self._drag_from, self._drop)
        elif i == "hub" and self.title:
            self.back.emit()
        elif isinstance(i, int) and i >= 0:
            self.selected.emit(i)
        self._press, self._drag_from, self._drop = None, -1, -1
        self.setCursor(Qt.PointingHandCursor)
        self.update()

    def mouseDoubleClickEvent(self, e):
        i = self._index_at(e.position())
        if isinstance(i, int) and i >= 0 and \
                self.slots[i].get("action", {}).get("type") == "folder":
            self.open_folder.emit(i)

    def paintEvent(self, _):
        p = QPainter(self)
        cx, cy, R, hub = self._geom()
        title = ("‹ " + self.title) if self.title else ""
        paint_wheel(p, cx, cy, R, hub, self.slots, Theme(),
                    hover=self.hover if self.hover != self.sel else -1,
                    selected=self.sel, title=title, fill_alpha=255,
                    dpr=self.devicePixelRatioF(), drop_target=self._drop)
        p.end()


class IconPicker(QDialog):
    """Pick a built-in icon, the automatic one, or your own picture."""

    def __init__(self, slot, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose an icon")
        self.resize(560, 470)
        self.result_icon = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)

        top = QHBoxLayout()
        auto_btn = QPushButton("  Automatic")
        auto_slot = dict(slot, icon={"kind": "auto"})
        auto_pm = icons.slot_pixmap(auto_slot, 20, Theme().fg, self.devicePixelRatioF())
        if auto_pm:
            auto_btn.setIcon(QIcon(auto_pm))
        auto_btn.setToolTip("Use the app's own icon, or a matching icon for the action")
        auto_btn.clicked.connect(lambda: self._pick({"kind": "auto"}))
        own_btn = QPushButton("Use my own image…")
        own_btn.clicked.connect(self._own)
        top.addWidget(auto_btn)
        top.addWidget(own_btn)
        top.addStretch()
        lay.addLayout(top)

        lay.addWidget(QLabel("Or pick one:"))
        grid = QListWidget()
        grid.setObjectName("iconGrid")
        grid.setViewMode(QListWidget.IconMode)
        grid.setIconSize(QSize(28, 28))
        grid.setGridSize(QSize(64, 64))
        grid.setResizeMode(QListWidget.Adjust)
        grid.setMovement(QListWidget.Static)
        color = Theme().fg
        for name in icons.ICONS:
            it = QListWidgetItem(QIcon(icons.svg_pixmap(name, 28, color, self.devicePixelRatioF())), "")
            it.setToolTip(name.replace("-", " "))
            it.setData(Qt.UserRole, name)
            grid.addItem(it)
        grid.itemClicked.connect(lambda it: self._pick({"kind": "builtin",
                                                        "name": it.data(Qt.UserRole)}))
        lay.addWidget(grid, 1)

    def _own(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose an image", "",
                                              "Images (*.png *.jpg *.jpeg *.ico *.svg *.bmp *.gif)")
        if not path:
            return
        os.makedirs(ICON_DIR, exist_ok=True)
        dest = os.path.join(ICON_DIR, uuid.uuid4().hex[:10] + os.path.splitext(path)[1].lower())
        shutil.copyfile(path, dest)
        self._pick({"kind": "file", "path": dest})

    def _pick(self, icon):
        self.result_icon = icon
        self.accept()
