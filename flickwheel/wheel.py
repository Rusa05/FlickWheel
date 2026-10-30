"""The radial wheel: drawing, the on-screen overlay and the hold/flick/release logic."""
import math

from PySide6.QtCore import (QEasingCurve, QObject, QPoint, QPointF, QRectF, Qt, QTimer,
                            QVariantAnimation, Signal)
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QPainter, \
    QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from . import actions, icons, winapi
from .keys import ALT, WIN

BASE_R, BASE_HUB = 130, 46   # ring radius and centre hub radius at 100% size


def ui_accent():
    """The Windows accent colour, or a clear blue if the accent is grey-ish."""
    c = QColor(*winapi.accent_color())
    if c.hsvSaturation() < 60:
        c = QColor(76, 141, 255)
    return c


class Theme:
    def __init__(self):
        self.dark = not winapi.system_uses_light_theme()
        self.accent = ui_accent()
        if self.dark:
            self.fg = QColor(255, 255, 255)
            self.fg_dim = QColor(255, 255, 255, 150)
            self.base = QColor(32, 32, 32)
            self.hub = QColor(255, 255, 255, 14)
            self.border = QColor(255, 255, 255, 38)
        else:
            self.fg = QColor(28, 28, 28)
            self.fg_dim = QColor(0, 0, 0, 140)
            self.base = QColor(246, 246, 246)
            self.hub = QColor(0, 0, 0, 10)
            self.border = QColor(0, 0, 0, 30)

    def tint_abgr(self, alpha):
        c = self.base
        return (alpha << 24) | (c.blue() << 16) | (c.green() << 8) | c.red()


def slot_index(dx, dy, count):
    """Which slot a direction points at. Slot 0 is straight up, then clockwise."""
    step = 360.0 / count
    ang = (math.degrees(math.atan2(dy, dx)) + 90.0) % 360.0
    return int((ang + step / 2) // step) % count


def slot_angle(i, count):
    """Centre angle of slot i in Qt degrees (0 = right, counter-clockwise)."""
    return 90.0 - i * 360.0 / count


def _sector(cx, cy, r_out, r_in, start, span):
    path = QPainterPath()
    outer = QRectF(cx - r_out, cy - r_out, 2 * r_out, 2 * r_out)
    inner = QRectF(cx - r_in, cy - r_in, 2 * r_in, 2 * r_in)
    path.arcMoveTo(outer, start)
    path.arcTo(outer, start, span)
    path.arcTo(inner, start + span, -span)
    path.closeSubpath()
    return path


def paint_wheel(p, cx, cy, R, hub, slots, theme, hover=-1, selected=-1, title="",
                fill_alpha=235, dpr=1.0, drop_target=-1):
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    n = max(1, len(slots))
    step = 360.0 / n

    base = QColor(theme.base)
    base.setAlpha(fill_alpha)
    p.setPen(QPen(theme.border, 1))
    p.setBrush(base)
    p.drawEllipse(QPointF(cx, cy), R - 0.5, R - 0.5)

    # thin dividers between slots
    div = QColor(theme.border)
    div.setAlpha(int(div.alpha() * 0.6))
    p.setPen(QPen(div, 1))
    for i in range(n):
        a = math.radians(slot_angle(i, n) + step / 2)
        p.drawLine(QPointF(cx + math.cos(a) * (hub + 6), cy - math.sin(a) * (hub + 6)),
                   QPointF(cx + math.cos(a) * (R - 6), cy - math.sin(a) * (R - 6)))

    def wedge(i, color):
        start = slot_angle(i, n) - step / 2
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(_sector(cx, cy, R - 5, hub + 5, start + 0.8, step - 1.6))

    if selected >= 0:
        c = QColor(theme.accent)
        c.setAlpha(70)
        wedge(selected, c)
        p.setPen(QPen(theme.accent, 2))
        p.setBrush(Qt.NoBrush)
        start = slot_angle(selected, n) - step / 2
        p.drawPath(_sector(cx, cy, R - 5, hub + 5, start + 0.8, step - 1.6))
    if drop_target >= 0:
        c = QColor(theme.accent)
        c.setAlpha(120)
        wedge(drop_target, c)
    if hover >= 0:
        c = QColor(theme.accent)
        c.setAlpha(225 if selected < 0 else 110)
        wedge(hover, c)

    # hub
    p.setPen(QPen(theme.border, 1))
    p.setBrush(theme.hub)
    p.drawEllipse(QPointF(cx, cy), hub, hub)

    # icons
    icon_size = max(16, int(R * 0.23))
    mid = (R + hub) / 2 + 2
    for i, s in enumerate(slots):
        a = math.radians(slot_angle(i, n))
        x, y = cx + math.cos(a) * mid, cy - math.sin(a) * mid
        is_hot = i == hover and selected < 0
        color = QColor(255, 255, 255) if is_hot else theme.fg
        pm = icons.slot_pixmap(s, icon_size, color, dpr)
        if pm is None:
            p.setPen(Qt.NoPen)
            p.setBrush(theme.fg_dim)
            p.drawEllipse(QPointF(x, y), 2.5, 2.5)
        else:
            p.drawPixmap(QRectF(x - icon_size / 2, y - icon_size / 2, icon_size, icon_size),
                         pm, QRectF(pm.rect()))
        if s.get("action", {}).get("type") == "folder":
            fx, fy = cx + math.cos(a) * (R - 10), cy - math.sin(a) * (R - 10)
            p.setPen(Qt.NoPen)
            p.setBrush(color if is_hot else theme.fg_dim)
            for k in (-1, 0, 1):
                b = a + math.radians(k * 4.5)
                p.drawEllipse(QPointF(cx + math.cos(b) * (R - 10), cy - math.sin(b) * (R - 10)),
                              1.6, 1.6)

    # hub text
    text = ""
    if 0 <= hover < len(slots):
        text = slots[hover].get("label", "")
    elif title:
        text = title
    elif 0 <= selected < len(slots):
        text = slots[selected].get("label", "")
    if text:
        f = QFont("Segoe UI Variable Text", 1)
        f.setPixelSize(max(10, int(hub * 0.27)))
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.setPen(theme.fg)
        box = QRectF(cx - hub + 6, cy - hub + 6, 2 * hub - 12, 2 * hub - 12)
        fm = QFontMetrics(f)
        if fm.horizontalAdvance(text) > box.width() * 2:
            text = fm.elidedText(text, Qt.ElideRight, int(box.width() * 1.9))
        p.drawText(box, Qt.AlignCenter | Qt.TextWordWrap, text)


class WheelOverlay(QWidget):
    """Frameless, click-through, never-focused window that shows the wheel."""

    PAD = 3

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool |
                         Qt.WindowTransparentForInput | Qt.WindowDoesNotAcceptFocus |
                         Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.theme = Theme()
        self.slots, self.title, self.hover = [], "", -1
        self.blur = True
        self.scale = 1.0
        self.R, self.hub = BASE_R, BASE_HUB
        self._anim_t = 1.0
        self._backdrop = None
        self._anim =QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._anim_t = v
        self.update()

    def configure(self, size_pct, blur):
        self.scale = size_pct / 100.0
        self.R, self.hub = BASE_R * self.scale, BASE_HUB * self.scale
        self.blur = blur
        side = int(2 * (self.R + self.PAD))
        self.setFixedSize(side, side)

    def show_at(self, center, slots, title=""):
        self.theme = Theme()
        self.slots, self.title, self.hover = slots, title, -1
        side = self.width()
        top_left = QPoint(center.x() - side // 2, center.y() - side // 2)
        self._backdrop = self._frosted_backdrop(top_left, side) if self.blur else None
        self.move(top_left)
        if not self.isVisible():
            self.show()
            winapi.exclude_from_capture(int(self.winId()))
        self._anim_t = 0.0
        self._anim.stop()
        self._anim.start()
        self.raise_()

    def _frosted_backdrop(self, top_left, side):
        """Snapshot what's behind the wheel and blur it (our window is excluded
        from screen capture, so it never appears in its own backdrop)."""
        screen = QGuiApplication.screenAt(top_left + QPoint(side // 2, side // 2))
        if screen is None:
            return None
        g = screen.geometry()
        pm = screen.grabWindow(0, top_left.x() - g.x(), top_left.y() - g.y(), side, side)
        if pm.isNull():
            return None
        img = pm.toImage()
        small = max(8, side // 12)
        img = img.scaled(small, small, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        img = img.scaled(small * 3, small * 3, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        img = img.scaled(side, side, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return QPixmap.fromImage(img)

    def set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        c = self.width() / 2
        t = self._anim_t
        p.setOpacity(min(1.0, 0.2 + t))
        s = 0.88 + 0.12 * t
        p.translate(c, c)
        p.scale(s, s)
        p.translate(-c, -c)
        glass = self.blur and self._backdrop is not None
        if glass:
            p.setRenderHint(QPainter.Antialiasing)
            clip = QPainterPath()
            clip.addEllipse(QPointF(c, c), self.R - 0.5, self.R - 0.5)
            p.setClipPath(clip)
            p.drawPixmap(0, 0, self.width(), self.height(), self._backdrop)
            p.setClipping(False)
        paint_wheel(p, c, c, self.R, self.hub, self.slots, self.theme, hover=self.hover,
                    title=self.title, fill_alpha=175 if glass else 240,
                    dpr=self.devicePixelRatioF())
        p.end()


class WheelController(QObject):
    """Turns trigger press/release + cursor movement into wheel navigation."""

    error = Signal(str)

    HOLD_MS = 160      # mouse: hold this long (or move) before the wheel opens
    MOVE_PX = 8

    def __init__(self, hooks):
        super().__init__()
        self.hooks = hooks
        self.cfg = None
        self.overlay = WheelOverlay()
        self.state = "idle"     # idle | pending | open | done
        self.source = None
        self.stack = []         # [(slots, title)]
        self.center = QPoint()
        self.hover = -1
        self.press_pos = QPoint()
        self._hover_timer_ms = 0

        self.poll = QTimer(self, interval=8, timerType=Qt.PreciseTimer)
        self.poll.timeout.connect(self._tick)
        self.hold = QTimer(self, singleShot=True, interval=self.HOLD_MS)
        self.hold.timeout.connect(self._open_from_pending)

        hooks.trigger_down.connect(self._on_down)
        hooks.trigger_up.connect(self._on_up)
        hooks.cancel.connect(self._on_cancel)

    def apply_config(self, cfg):
        self.cfg = cfg
        self.overlay.configure(cfg["size"], cfg["blur"])

    # ----------------------------------------------------------- triggers

    def _on_down(self, source):
        if self.state != "idle":
            return
        self.source = source
        if source == "keyboard":
            combo = self.cfg["trigger"]["keyboard"]
            if ALT in combo or WIN in combo:
                winapi.send_keys([(0xE8, False), (0xE8, True)])  # stop menus/Start opening
            self._open()
        else:
            self.state = "pending"
            self.press_pos = QCursor.pos()
            self.hold.start()
            self.poll.start()

    def _on_up(self, source):
        if source != self.source:
            return
        self.hold.stop()
        if self.state == "pending":
            self._reset()
            winapi.send_mouse_click(self.cfg["trigger"]["mouse"])  # it was just a tap
        elif self.state == "open":
            slots = self.stack[-1][0]
            if 0 <= self.hover < len(slots):
                s = slots[self.hover]
                if actions.is_runnable(s.get("action", {})):
                    self._fire(s, released=True)
                    return
            self._reset()
        else:
            self._reset()

    def _on_cancel(self):
        if self.state == "open":
            self._close()
            self.state = "done"   # ignore everything until the trigger is released

    # ----------------------------------------------------------- wheel

    def _open_from_pending(self):
        if self.state == "pending":
            self._open(self.press_pos)

    def _clamped(self, pos):
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        g = screen.geometry()
        m = int(self.overlay.R) + 6
        x = min(max(pos.x(), g.left() + m), g.right() - m)
        y = min(max(pos.y(), g.top() + m), g.bottom() - m)
        return QPoint(x, y)

    def _show_level(self, pos):
        self.center = self._clamped(pos)
        if self.center != QCursor.pos():
            QCursor.setPos(self.center)
        slots, title = self.stack[-1]
        self.hover = -1
        self._hover_timer_ms = 0
        self.overlay.show_at(self.center, slots, title)

    def _open(self, pos=None):
        self.state = "open"
        self.hooks.wheel_open = True
        self.stack = [(self.cfg["slots"], "")]
        self._show_level(pos or QCursor.pos())
        self.poll.start()

    def _tick(self):
        pos = QCursor.pos()
        if self.state == "pending":
            d = pos - self.press_pos
            if abs(d.x()) + abs(d.y()) >= self.MOVE_PX:
                self.hold.stop()
                self._open(self.press_pos)
            return
        if self.state != "open":
            return
        slots, _ = self.stack[-1]
        if not slots:
            return
        dx, dy = pos.x() - self.center.x(), pos.y() - self.center.y()
        dist = math.hypot(dx, dy)
        hover = -1 if dist < self.overlay.hub * 0.75 else slot_index(dx, dy, len(slots))
        if hover != self.hover:
            self.hover = hover
            self._hover_timer_ms = 0
            self.overlay.set_hover(hover)
        else:
            self._hover_timer_ms += self.poll.interval()
        if hover < 0:
            return

        s = slots[hover]
        action = s.get("action", {})
        past_ring = dist >= self.overlay.R + self.cfg["flick_distance"]
        if action.get("type") == "folder":
            if past_ring or self._hover_timer_ms >= self.cfg["folder_hover_ms"]:
                self.stack.append((action.get("slots", []), s.get("label") or "Folder"))
                self._show_level(pos)
        elif past_ring and self.cfg["flick_to_fire"] and actions.is_runnable(action):
            self._fire(s, released=False)

    def _fire(self, slot, released):
        """Run a slot. If the trigger is still held we wait for its release."""
        if released:
            self._reset()
        else:
            self._close()
            self.state = "done"
        action = slot.get("action", {})

        def go():
            err = actions.run(action)
            if err:
                self.error.emit(f"Couldn't run “{slot.get('label', '')}”: {err}")
        QTimer.singleShot(20, go)  # let the overlay disappear first

    def _close(self):
        self.poll.stop()
        self.overlay.hide()
        self.hooks.wheel_open = False
        self.hover = -1

    def _reset(self):
        self._close()
        self.hold.stop()
        self.state = "idle"
        self.source = None
