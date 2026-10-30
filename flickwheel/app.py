"""Ties everything together: hooks, wheel, tray icon, settings window."""
import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import config, shortcuts, winapi
from .appcatalog import AppCatalog
from .hooks import InputHooks
from .wheel import WheelController, ui_accent

INSTANCE_KEY = "FlickWheel-single-instance"


def make_icon_pixmap(size=64):
    """A little wheel: ring with one highlighted wedge."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 64, size / 64)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(40, 40, 46))
    p.drawEllipse(QRectF(2, 2, 60, 60))
    wedge = QPainterPath()
    wedge.moveTo(32, 32)
    wedge.arcTo(QRectF(6, 6, 52, 52), 67.5, 45)
    wedge.closeSubpath()
    p.setBrush(ui_accent())
    p.drawPath(wedge)
    p.setBrush(QColor(40, 40, 46))
    p.drawEllipse(QPointF(32, 32), 11, 11)
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(QPointF(32, 32), 5, 5)
    p.end()
    return pm


def make_app_icon():
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 256):
        icon.addPixmap(make_icon_pixmap(s))
    return icon


class FlickWheelApp:
    def __init__(self, argv):
        self.qt = QApplication(argv)
        self.qt.setQuitOnLastWindowClosed(False)
        self.qt.setApplicationName("FlickWheel")
        self.icon = make_app_icon()
        self.qt.setWindowIcon(self.icon)

        first_run = not os.path.exists(config.CONFIG_PATH)
        self.cfg = config.load()
        self.settings = None
        self.catalog = AppCatalog()

        self.hooks = InputHooks()
        self.wheel = WheelController(self.hooks)
        self.wheel.error.connect(lambda m: self.tray.showMessage("FlickWheel", m, self.icon, 4000))
        self._apply()

        self._save_timer = QTimer(singleShot=True, interval=300)
        self._save_timer.timeout.connect(self._save)

        self._build_tray()
        self.server = QLocalServer()
        QLocalServer.removeServer(INSTANCE_KEY)
        self.server.listen(INSTANCE_KEY)
        self.server.newConnection.connect(self._other_instance)

        self._make_shortcuts()

        if first_run:
            config.save(self.cfg)
            try:
                winapi.set_start_with_windows(True)
            except OSError:
                pass
            self.show_settings()
            self.tray.showMessage("FlickWheel is running",
                                  "Hold Ctrl + Space anywhere to open your wheel.", self.icon, 5000)
        elif "--background" not in argv:
            self.show_settings()

    def _make_shortcuts(self):
        """Start menu shortcut always; Desktop one only once (so deleting it sticks)."""
        if not os.path.exists(shortcuts.ICON_PATH):
            shortcuts.save_icon(make_icon_pixmap(256))
        def done():
            self.cfg["desktop_shortcut_made"] = True  # saved with the next settings save
        shortcuts.ensure_shortcuts(desktop=not self.cfg.get("desktop_shortcut_made"),
                                   on_desktop_done=done)

    # ------------------------------------------------------------ config

    def _apply(self):
        self.hooks.apply_config(self.cfg)
        self.wheel.apply_config(self.cfg)

    def config_changed(self):
        self._apply()
        self._save_timer.start()

    def _save(self):
        try:
            config.save(self.cfg)
        except OSError as e:
            self.tray.showMessage("FlickWheel", f"Couldn't save settings: {e}", self.icon, 4000)

    def reset_config(self):
        self.cfg = config.default_config()
        self._save()
        self._apply()
        if self.settings:
            geo = self.settings.geometry()
            self.settings.close()
            self.settings.deleteLater()
            self.settings = None
            self.show_settings()
            self.settings.setGeometry(geo)

    def set_paused(self, paused):
        self.hooks.paused = paused
        self.pause_action.setChecked(paused)
        self.tray.setToolTip("FlickWheel (paused)" if paused else "FlickWheel")
        if self.settings:
            self.settings.sync_paused(paused)

    # ------------------------------------------------------------ ui

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.icon)
        self.tray.setToolTip("FlickWheel")
        menu = QMenu()
        open_act = QAction("Open settings", menu)
        open_act.triggered.connect(self.show_settings)
        self.pause_action = QAction("Pause wheel", menu, checkable=True)
        self.pause_action.toggled.connect(self.set_paused)
        quit_act = QAction("Quit FlickWheel", menu)
        quit_act.triggered.connect(self.quit)
        menu.addAction(open_act)
        menu.addAction(self.pause_action)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self._menu = menu
        self.tray.activated.connect(
            lambda r: self.show_settings() if r in (QSystemTrayIcon.Trigger,
                                                    QSystemTrayIcon.DoubleClick) else None)
        self.tray.show()

    def show_settings(self):
        if self.settings is None:
            from .settings import SettingsWindow
            self.settings = SettingsWindow(self)
        self.settings.showNormal()
        self.settings.raise_()
        self.settings.activateWindow()

    def _other_instance(self):
        sock = self.server.nextPendingConnection()
        if sock:
            sock.close()
        self.show_settings()

    def quit(self):
        self._save_timer.stop()
        self._save()
        self.hooks.stop()
        self.tray.hide()
        self.qt.quit()

    def run(self):
        return self.qt.exec()


def main():
    sys.setswitchinterval(0.001)  # keep the input-hook thread snappy
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_KEY)
    if sock.waitForConnected(300):
        # Already running: that instance opens its settings window.
        sock.disconnectFromServer()
        return 0
    return FlickWheelApp(sys.argv).run()
