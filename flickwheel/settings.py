"""The settings window."""
import os

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
                               QScrollArea, QSlider, QStackedWidget, QVBoxLayout, QWidget)

from . import actions, config, icons, winapi
from .actions import ACTION_TYPES, MEDIA_ACTIONS, SYSTEM_ACTIONS, describe
from .config import MAX_SLOTS, MIN_SLOTS, empty_slot
from .wheel import Theme, ui_accent
from .widgets import IconPicker, KeyRecorder, ToggleSwitch, WheelPreview

DIRECTIONS = ["Top", "Top right", "Right", "Bottom right", "Bottom", "Bottom left", "Left",
              "Top left"]


def direction_name(i, n):
    return DIRECTIONS[round(i * 360.0 / n / 45.0) % 8]


def stylesheet():
    t = Theme()
    a = ui_accent()
    acc, acc_h = a.name(), a.lighter(115).name()
    if t.dark:
        bg, side, card, card2, border, text, sub, field = (
            "#1c1c1f", "#202024", "#2a2a2f", "#323238", "#3a3a42", "#f2f2f5", "#a0a0aa", "#232328")
    else:
        bg, side, card, card2, border, text, sub, field = (
            "#f4f4f7", "#ececf1", "#ffffff", "#f6f6f9", "#dcdce3", "#1b1b1f", "#5f5f6b", "#ffffff")
    return f"""
    * {{ font-family: "Segoe UI Variable Text", "Segoe UI"; font-size: 14px; color: {text}; }}
    QWidget#root, QDialog {{ background: {bg}; }}
    QWidget#page {{ background: transparent; }}
    QListWidget#nav {{ background: {side}; border: none; padding: 14px 10px; outline: 0; }}
    QListWidget#nav::item {{ padding: 10px 12px; border-radius: 10px; margin: 2px 0; }}
    QListWidget#nav::item:hover {{ background: {card}; }}
    QListWidget#nav::item:selected {{ background: {card2}; color: {text};
        border-left: 3px solid {acc}; }}
    QLabel#h1 {{ font-size: 26px; font-weight: 600; }}
    QLabel#h2 {{ font-size: 16px; font-weight: 600; }}
    QLabel#sub, QLabel#hint {{ color: {sub}; }}
    QLabel#hint {{ font-size: 12px; }}
    QFrame#card {{ background: {card}; border: 1px solid {border}; border-radius: 14px; }}
    QPushButton {{ background: {card2}; border: 1px solid {border}; border-radius: 10px;
        padding: 8px 16px; }}
    QPushButton:hover {{ border-color: {acc}; background: {card}; }}
    QPushButton:pressed {{ background: {border}; }}
    QPushButton:disabled {{ color: {sub}; }}
    QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {acc_h}, stop:1 {acc});
        color: white; border: none; font-weight: 600; }}
    QPushButton#primary:hover {{ background: {acc_h}; }}
    QPushButton#danger:hover {{ border-color: #e5484d; color: #e5484d; }}
    QPushButton#round {{ border-radius: 17px; min-width: 34px; max-width: 34px; min-height: 34px;
        max-height: 34px; padding: 0; font-size: 18px; font-weight: 600; }}
    QPushButton#crumb {{ background: transparent; border: none; padding: 4px 6px; color: {sub}; }}
    QPushButton#crumb:hover {{ color: {acc}; }}
    QPushButton#crumbCurrent {{ background: transparent; border: none; padding: 4px 6px;
        font-weight: 600; }}
    QPushButton#recorder {{ background: {field}; border: 2px dashed {border}; border-radius: 12px;
        font-size: 15px; font-weight: 600; padding: 8px 18px; }}
    QPushButton#recorder:hover {{ border-color: {acc}; }}
    QPushButton#recorder[recording="true"] {{ border: 2px solid {acc}; color: {acc}; }}
    QLineEdit, QComboBox {{ background: {field}; border: 1px solid {border}; border-radius: 10px;
        padding: 8px 12px; selection-background-color: {acc}; }}
    QLineEdit:focus, QComboBox:focus {{ border: 2px solid {acc}; padding: 7px 11px; }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox QAbstractItemView {{ background: {card}; border: 1px solid {border};
        selection-background-color: {acc}; selection-color: white; padding: 4px; outline: 0; }}
    QListWidget {{ background: {field}; border: 1px solid {border}; border-radius: 12px;
        padding: 4px; outline: 0; }}
    QListWidget::item {{ padding: 7px 8px; border-radius: 8px; }}
    QListWidget::item:hover {{ background: {card2}; }}
    QListWidget::item:selected {{ background: {acc}; color: white; }}
    QListWidget#iconGrid::item {{ padding: 4px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {border}; border-radius: 3px; }}
    QSlider::sub-page:horizontal {{ background: {acc}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: white; border: 4px solid {acc}; width: 12px;
        height: 12px; margin: -7px 0; border-radius: 10px; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    QMenu {{ background: {card}; border: 1px solid {border}; border-radius: 10px; padding: 6px; }}
    QMenu::item {{ padding: 8px 18px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {acc}; color: white; }}
    QToolTip {{ background: {card}; color: {text}; border: 1px solid {border}; padding: 6px; }}
    """


def card(*rows, spacing=10):
    f = QFrame()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(20, 18, 20, 18)
    lay.setSpacing(spacing)
    for r in rows:
        if isinstance(r, QWidget):
            lay.addWidget(r)
        else:
            lay.addLayout(r)
    return f


def label(text, kind=None, wrap=True):
    l = QLabel(text)
    if kind:
        l.setObjectName(kind)
    l.setWordWrap(wrap)
    return l


def toggle_row(title, subtitle, checked, on_change):
    row = QHBoxLayout()
    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(label(title, "h2"))
    if subtitle:
        col.addWidget(label(subtitle, "sub"))
    row.addLayout(col, 1)
    sw = ToggleSwitch()
    sw.setChecked(checked)
    sw.toggled.connect(on_change)
    row.addWidget(sw, 0, Qt.AlignVCenter)
    return row, sw


def page_widget(title, subtitle):
    """Scrollable page with a heading. Returns (scroll_area, content_layout)."""
    inner = QWidget()
    inner.setObjectName("page")
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(36, 30, 36, 30)
    lay.setSpacing(16)
    lay.addWidget(label(title, "h1"))
    if subtitle:
        lay.addWidget(label(subtitle, "sub"))
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    sa.viewport().setAutoFillBackground(False)
    inner.setAutoFillBackground(False)
    return sa, lay


# ======================================================================= slot editor


class SlotEditor(QWidget):
    changed = Signal()
    open_folder = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.slot = None
        self._loading = False
        self._icon_queue = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        self.heading = label("", "h2")
        lay.addWidget(self.heading)

        lay.addWidget(label("What should this slot do?", "sub"))
        self.type_box = QComboBox()
        self.type_box.setIconSize(QSize(18, 18))
        for key, (name, _) in ACTION_TYPES.items():
            self.type_box.addItem(name, key)
        self.type_box.currentIndexChanged.connect(self._type_changed)
        lay.addWidget(self.type_box)
        self.type_hint = label("", "hint")
        lay.addWidget(self.type_hint)

        # needed by _build_app, which fills the app list straight away from the cache
        self._icon_timer = QTimer(self, interval=15)
        self._icon_timer.timeout.connect(self._load_some_icons)

        self.stack = QStackedWidget()
        self.pages = {}
        for key, builder in (("app", self._build_app), ("file", self._build_file),
                             ("url", self._build_url), ("system", self._build_system),
                             ("keys", self._build_keys), ("media", self._build_media),
                             ("folder", self._build_folder), ("none", self._build_none)):
            w = builder()
            self.pages[key] = w
            self.stack.addWidget(w)
        lay.addWidget(self.stack, 1)

        # name + icon
        row = QHBoxLayout()
        row.setSpacing(12)
        name_col = QVBoxLayout()
        name_col.addWidget(label("Name (shown in the middle of the wheel)", "sub"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Spotify")
        self.name_edit.textEdited.connect(self._name_edited)
        name_col.addWidget(self.name_edit)
        row.addLayout(name_col, 1)
        icon_col = QVBoxLayout()
        icon_col.addWidget(label("Icon", "sub"))
        self.icon_btn = QPushButton()
        self.icon_btn.setIconSize(QSize(26, 26))
        self.icon_btn.setFixedSize(QSize(64, 42))
        self.icon_btn.setToolTip("Change icon")
        self.icon_btn.setCursor(Qt.PointingHandCursor)
        self.icon_btn.clicked.connect(self._pick_icon)
        icon_col.addWidget(self.icon_btn)
        row.addLayout(icon_col)
        lay.addLayout(row)

        btns = QHBoxLayout()
        self.try_btn = QPushButton("▶  Try it")
        self.try_btn.setObjectName("primary")
        self.try_btn.setCursor(Qt.PointingHandCursor)
        self.try_btn.clicked.connect(self._try)
        self.clear_btn = QPushButton("Clear slot")
        self.clear_btn.setObjectName("danger")
        self.clear_btn.clicked.connect(self._clear)
        btns.addWidget(self.try_btn)
        btns.addWidget(self.clear_btn)
        btns.addStretch()
        lay.addLayout(btns)

        app.catalog.updated.connect(self._fill_apps)

    # ------------------------------------------------------------- pages

    def _build_app(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self.app_search = QLineEdit()
        self.app_search.setPlaceholderText("🔍  Search your apps…")
        self.app_search.textChanged.connect(self._filter_apps)
        lay.addWidget(self.app_search)
        self.app_list = QListWidget()
        self.app_list.setIconSize(QSize(24, 24))
        self.app_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.app_list.setMinimumHeight(180)
        self.app_list.itemClicked.connect(self._app_chosen)
        lay.addWidget(self.app_list, 1)
        b = QPushButton("Browse for a program (.exe)…")
        b.clicked.connect(self._browse_exe)
        lay.addWidget(b, 0, Qt.AlignLeft)
        self._fill_apps(self.app.catalog.apps)
        self.app.catalog.refresh()
        return w

    def _fill_apps(self, apps):
        self.app_list.clear()
        self._icon_queue = []
        if not apps:
            it = QListWidgetItem("Loading your apps…")
            it.setFlags(Qt.NoItemFlags)
            self.app_list.addItem(it)
            return
        for a in apps:
            it = QListWidgetItem(a["name"])
            it.setData(Qt.UserRole, a)
            self.app_list.addItem(it)
            self._icon_queue.append(it)
        self._icon_timer.start()
        self._filter_apps(self.app_search.text())
        self._select_current_app()

    def _load_some_icons(self):
        dpr = self.devicePixelRatioF()
        for _ in range(6):
            if not self._icon_queue:
                self._icon_timer.stop()
                return
            it = self._icon_queue.pop(0)
            pm = icons.shell_pixmap(it.data(Qt.UserRole)["target"], 24, dpr)
            if pm:
                it.setIcon(QIcon(pm))

    def _filter_apps(self, text):
        text = text.lower().strip()
        for i in range(self.app_list.count()):
            it = self.app_list.item(i)
            it.setHidden(bool(text) and text not in it.text().lower())

    def _select_current_app(self):
        if not self.slot:
            return
        target = self.slot["action"].get("target")
        for i in range(self.app_list.count()):
            it = self.app_list.item(i)
            a = it.data(Qt.UserRole)
            if a and a["target"] == target:
                self.app_list.setCurrentItem(it)
                self.app_list.scrollToItem(it)
                return
        self.app_list.clearSelection()

    def _app_chosen(self, it):
        a = it.data(Qt.UserRole)
        if a:
            self._set_action({"type": "app", "target": a["target"], "name": a["name"]})

    def _browse_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a program", "C:\\Program Files",
                                              "Programs (*.exe *.lnk *.bat *.cmd);;All files (*)")
        if path:
            path = os.path.normpath(path)
            name = os.path.splitext(os.path.basename(path))[0]
            self._set_action({"type": "app", "target": path, "name": name})

    def _build_file(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Choose a file or folder below")
        self.file_edit.editingFinished.connect(
            lambda: self._set_action({"type": "file", "target": self.file_edit.text().strip()}))
        lay.addWidget(self.file_edit)
        row = QHBoxLayout()
        b1 = QPushButton("Choose a file…")
        b1.clicked.connect(self._choose_file)
        b2 = QPushButton("Choose a folder…")
        b2.clicked.connect(self._choose_folder)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return w

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file")
        if path:
            self._set_action({"type": "file", "target": os.path.normpath(path)})

    def _choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if path:
            self._set_action({"type": "file", "target": os.path.normpath(path)})

    def _build_url(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("e.g. youtube.com")
        self.url_edit.textEdited.connect(
            lambda t: self._set_action({"type": "url", "target": t.strip()}, refresh=False))
        lay.addWidget(self.url_edit)
        lay.addStretch()
        return w

    def _build_list(self, entries, key):
        """entries: [(id, title, subtitle, icon_name)]"""
        lst = QListWidget()
        lst.setIconSize(QSize(22, 22))
        lst.setWordWrap(True)
        color = Theme().fg
        for ident, title, subtitle, icon in entries:
            it = QListWidgetItem(QIcon(icons.svg_pixmap(icon, 22, color, self.devicePixelRatioF())),
                                 f"{title}\n{subtitle}" if subtitle else title)
            it.setData(Qt.UserRole, ident)
            lst.addItem(it)
        lst.itemClicked.connect(lambda it: self._set_action({"type": key, "id": it.data(Qt.UserRole)}))
        return lst

    def _build_system(self):
        self.system_list = self._build_list(
            [(k, v[0], v[1], v[2]) for k, v in SYSTEM_ACTIONS.items()], "system")
        return self.system_list

    def _build_media(self):
        self.media_list = self._build_list(
            [(k, v[0], "", v[1]) for k, v in MEDIA_ACTIONS.items()], "media")
        return self.media_list

    def _build_keys(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self.key_rec = KeyRecorder(self.app.hooks)
        self.key_rec.combo_changed.connect(lambda v: self._set_action({"type": "keys", "vks": v}))
        lay.addWidget(self.key_rec)
        lay.addWidget(label("Click the box, then press the shortcut you want this slot to send "
                            "to the app you're using.", "hint"))
        lay.addStretch()
        return w

    def _build_folder(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        self.folder_info = label("", "sub")
        lay.addWidget(self.folder_info)
        b = QPushButton("Edit this folder's wheel  →")
        b.setObjectName("primary")
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(self.open_folder.emit)
        lay.addWidget(b, 0, Qt.AlignLeft)
        lay.addStretch()
        return w

    def _build_none(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(label("This slot is empty. Pick what it should do above.", "sub"))
        lay.addStretch()
        return w

    # ------------------------------------------------------------- binding

    def set_slot(self, slot, index, count):
        self.index, self.count = index, count
        self._rebind(slot)

    def _rebind(self, slot):
        self.slot = slot
        self._loading = True
        self.heading.setText(f"Slot {self.index + 1}  ·  {direction_name(self.index, self.count)}")
        a = slot["action"]
        t = a.get("type", "none")
        self.type_box.setCurrentIndex(list(ACTION_TYPES).index(t))
        self.type_hint.setText(ACTION_TYPES[t][1])
        self.stack.setCurrentWidget(self.pages[t])
        self.name_edit.setText(slot.get("label", ""))
        if t == "app":
            self._select_current_app()
        elif t == "file":
            self.file_edit.setText(a.get("target", ""))
        elif t == "url":
            self.url_edit.setText(a.get("target", ""))
        elif t in ("system", "media"):
            lst = self.system_list if t == "system" else self.media_list
            lst.clearSelection()
            for i in range(lst.count()):
                if lst.item(i).data(Qt.UserRole) == a.get("id"):
                    lst.setCurrentRow(i)
                    lst.scrollToItem(lst.item(i))
        elif t == "keys":
            self.key_rec.set_combo(a.get("vks", []))
        elif t == "folder":
            used = sum(1 for s in a.get("slots", []) if s["action"].get("type") != "none")
            self.folder_info.setText(
                f"Flick into this slot to open a second wheel. "
                f"It has {len(a.get('slots', []))} slots ({used} in use).")
        self.try_btn.setEnabled(actions.is_runnable(a))
        self.clear_btn.setEnabled(t != "none")
        self._refresh_icon()
        self._loading = False

    def _refresh_icon(self):
        pm = icons.slot_pixmap(self.slot, 26, Theme().fg, self.devicePixelRatioF())
        self.icon_btn.setIcon(QIcon(pm) if pm else QIcon())
        self.icon_btn.setText("" if pm else "+")

    def _set_action(self, action, refresh=True):
        old = self.slot["action"]
        auto_name = self.slot.get("label", "") in ("", describe(old))
        if old.get("type") == "folder" and action.get("type") == "folder":
            action["slots"] = old.get("slots", [])
        self.slot["action"] = action
        if auto_name:
            self.slot["label"] = describe(action) if action.get("type") != "none" else ""
            self.name_edit.setText(self.slot["label"])
        self.try_btn.setEnabled(actions.is_runnable(action))
        self.clear_btn.setEnabled(action.get("type") != "none")
        self._refresh_icon()
        self.changed.emit()

    def _type_changed(self, idx):
        if self._loading or not self.slot:
            return
        t = self.type_box.itemData(idx)
        old = self.slot["action"]
        if t == old.get("type"):
            return
        if old.get("type") == "folder" and any(
                s["action"].get("type") != "none" for s in old.get("slots", [])):
            if QMessageBox.question(self, "Remove folder?",
                                    "This folder has actions inside it. Change it anyway? "
                                    "Its contents will be removed.") != QMessageBox.Yes:
                self._loading = True
                self.type_box.setCurrentIndex(list(ACTION_TYPES).index("folder"))
                self._loading = False
                return
        new = {"type": t}
        if t == "folder":
            new["slots"] = [empty_slot() for _ in range(6)]
        self.slot["label"] = ""          # new purpose, so take the new default name
        self.slot["icon"] = {"kind": "auto"}
        self._set_action(new)
        self._rebind(self.slot)
        if t == "app":
            self.app_search.setFocus()
        elif t == "url":
            self.url_edit.setFocus()

    def _name_edited(self, text):
        if self.slot is not None:
            self.slot["label"] = text
            self.changed.emit()

    def _pick_icon(self):
        dlg = IconPicker(self.slot, self.window())
        if dlg.exec() and dlg.result_icon:
            self.slot["icon"] = dlg.result_icon
            self._refresh_icon()
            self.changed.emit()

    def _try(self):
        err = actions.run(self.slot["action"])
        if err:
            QMessageBox.warning(self, "Couldn't run it", err)

    def _clear(self):
        self.slot.clear()
        self.slot.update(empty_slot())
        self._rebind(self.slot)
        self.changed.emit()


# ======================================================================= main window


class SettingsWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.cfg = app.cfg
        self.setObjectName("root")
        self.setWindowTitle("FlickWheel")
        self.setWindowIcon(app.icon)
        self.resize(1100, 790)
        self.setMinimumSize(920, 640)
        self.setStyleSheet(stylesheet())

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(210)
        self.nav.setIconSize(QSize(20, 20))
        self.pages = QStackedWidget()
        lay.addWidget(self.nav)
        lay.addWidget(self.pages, 1)

        color = Theme().fg
        for title, icon, build in (("Wheel", "grid", self._wheel_page),
                                   ("Trigger", "keyboard", self._trigger_page),
                                   ("Paused in apps", "pause", self._paused_page),
                                   ("Look & feel", "image", self._look_page),
                                   ("General", "settings", self._general_page)):
            it = QListWidgetItem(QIcon(icons.svg_pixmap(icon, 20, color, self.devicePixelRatioF())),
                                 "  " + title)
            self.nav.addItem(it)
            self.pages.addWidget(build())
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(0)

    def changed(self):
        self.app.config_changed()

    # ------------------------------------------------------------- wheel page

    def _wheel_page(self):
        w = QWidget()
        w.setObjectName("page")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(36, 30, 36, 24)
        outer.setSpacing(14)
        outer.addWidget(label("Your wheel", "h1"))

        top = QHBoxLayout()
        self.crumbs = QHBoxLayout()
        self.crumbs.setSpacing(0)
        top.addLayout(self.crumbs)
        top.addStretch()
        top.addWidget(label("Slots", "sub", wrap=False))
        self.minus = QPushButton("−")
        self.minus.setObjectName("round")
        self.minus.setToolTip("Remove a slot")
        self.minus.clicked.connect(lambda: self._change_count(-1))
        self.count_lbl = label("8", "h2", wrap=False)
        self.count_lbl.setFixedWidth(30)
        self.count_lbl.setAlignment(Qt.AlignCenter)
        self.plus = QPushButton("+")
        self.plus.setObjectName("round")
        self.plus.setToolTip("Add a slot")
        self.plus.clicked.connect(lambda: self._change_count(1))
        for x in (self.minus, self.count_lbl, self.plus):
            top.addWidget(x)
        outer.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(28)
        left = QVBoxLayout()
        self.preview = WheelPreview()
        self.preview.setMinimumSize(400, 400)
        self.preview.selected.connect(self._select)
        self.preview.swapped.connect(self._swap)
        self.preview.open_folder.connect(self._enter_folder)
        self.preview.back.connect(lambda: self._go_level(len(self.path) - 1))
        left.addWidget(self.preview, 1)
        left.addWidget(label("Click a slot to edit it  ·  drag one onto another to swap",
                             "hint", wrap=False), 0, Qt.AlignHCenter)
        body.addLayout(left, 5)

        self.editor = SlotEditor(self.app)
        self.editor.changed.connect(self._slot_changed)
        self.editor.open_folder.connect(lambda: self._enter_folder(self.sel))
        body.addWidget(card(self.editor), 6)
        outer.addLayout(body, 1)

        self.path = [(self.cfg["slots"], "Main wheel")]   # [(slots list, title)]
        self.sel = 0
        self._refresh_wheel()
        return w

    def _current(self):
        return self.path[-1][0]

    def _refresh_wheel(self):
        slots = self._current()
        self.sel = min(self.sel, len(slots) - 1)
        title = self.path[-1][1] if len(self.path) > 1 else ""
        self.preview.set_slots(slots, title, self.sel)
        self.editor.set_slot(slots[self.sel], self.sel, len(slots))
        self.count_lbl.setText(str(len(slots)))
        self.minus.setEnabled(len(slots) > MIN_SLOTS)
        self.plus.setEnabled(len(slots) < MAX_SLOTS)
        # breadcrumbs
        while self.crumbs.count():
            item = self.crumbs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, (_, t) in enumerate(self.path):
            if i:
                self.crumbs.addWidget(label("›", "sub", wrap=False))
            b = QPushButton(t)
            b.setObjectName("crumbCurrent" if i == len(self.path) - 1 else "crumb")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, i=i: self._go_level(i))
            self.crumbs.addWidget(b)

    def _select(self, i):
        self.sel = i
        self._refresh_wheel()

    def _swap(self, a, b):
        s = self._current()
        s[a], s[b] = s[b], s[a]
        self.sel = b
        self._refresh_wheel()
        self.changed()

    def _enter_folder(self, i):
        s = self._current()[i]
        if s["action"].get("type") != "folder":
            return
        self.path.append((s["action"].setdefault("slots", [empty_slot() for _ in range(6)]),
                          s.get("label") or "Folder"))
        self.sel = 0
        self._refresh_wheel()

    def _go_level(self, level):
        self.path = self.path[:max(1, level + 1)]
        self.sel = 0
        self._refresh_wheel()

    def _change_count(self, delta):
        s = self._current()
        if delta > 0 and len(s) < MAX_SLOTS:
            s.append(empty_slot())
            self.sel = len(s) - 1
        elif delta < 0 and len(s) > MIN_SLOTS:
            # remove an empty slot if there is one, otherwise the last one (after asking)
            empties = [i for i, x in enumerate(s) if x["action"].get("type") == "none"]
            if empties:
                s.pop(empties[-1])
            else:
                last = s[-1]
                if QMessageBox.question(
                        self, "Remove slot?",
                        f"Every slot is in use. Remove “{last.get('label') or 'the last slot'}”?"
                ) != QMessageBox.Yes:
                    return
                s.pop()
        self._refresh_wheel()
        self.changed()

    def _slot_changed(self):
        self.preview.update()
        self.changed()

    # ------------------------------------------------------------- trigger page

    def _trigger_page(self):
        sa, lay = page_widget("Trigger", "How you open the wheel. Hold the trigger, flick "
                                         "toward an action, then let go.")
        t = self.cfg["trigger"]

        def kb_toggle(on):
            t["keyboard_enabled"] = on
            self.kb_rec.setEnabled(on)
            self.changed()
        row, _ = toggle_row("Keyboard shortcut", "Hold these keys to open the wheel at your cursor.",
                            t["keyboard_enabled"], kb_toggle)
        self.kb_rec = KeyRecorder(self.app.hooks, need_main_key=True)
        self.kb_rec.set_combo(t["keyboard"])
        self.kb_rec.setEnabled(t["keyboard_enabled"])

        def kb_set(v):
            t["keyboard"] = v
            self.changed()
        self.kb_rec.combo_changed.connect(kb_set)
        lay.addWidget(card(row, self.kb_rec))

        def ms_toggle(on):
            t["mouse_enabled"] = on
            self.mouse_box.setEnabled(on)
            self.changed()
        row, _ = toggle_row("Mouse button", "Hold a mouse button to open the wheel. "
                                            "A quick click still works like normal.",
                            t["mouse_enabled"], ms_toggle)
        self.mouse_box = QComboBox()
        for key, name in (("middle", "Middle button (click the scroll wheel)"),
                          ("x1", "Back side button"), ("x2", "Forward side button")):
            self.mouse_box.addItem(name, key)
        self.mouse_box.setCurrentIndex(["middle", "x1", "x2"].index(t["mouse"]))
        self.mouse_box.setEnabled(t["mouse_enabled"])

        def ms_set(i):
            t["mouse"] = self.mouse_box.itemData(i)
            self.changed()
        self.mouse_box.currentIndexChanged.connect(ms_set)
        lay.addWidget(card(row, self.mouse_box))

        def flick_toggle(on):
            self.cfg["flick_to_fire"] = on
            self.flick_slider.setEnabled(on)
            self.changed()
        row, _ = toggle_row("Flick to fire instantly",
                            "Throw the cursor past the edge of the wheel and the action runs "
                            "straight away, without letting go.",
                            self.cfg["flick_to_fire"], flick_toggle)
        self.flick_slider, srow = self._slider(20, 160, self.cfg["flick_distance"],
                                               lambda v: f"{v} px past the edge",
                                               "flick_distance", "Closer", "Further")
        self.flick_slider.setEnabled(self.cfg["flick_to_fire"])
        lay.addWidget(card(row, srow))

        _, frow = self._slider(150, 1000, self.cfg["folder_hover_ms"],
                               lambda v: f"{v / 1000:.2f} s", "folder_hover_ms", "Faster",
                               "Slower", step=50)
        lay.addWidget(card(label("Folders", "h2"),
                           label("A folder opens when you flick through it, or when you rest "
                                 "on it for this long.", "sub"), frow))
        lay.addStretch()
        return sa

    def _slider(self, lo, hi, value, fmt, key, left, right, step=10):
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setPageStep(step)
        s.setValue(value)
        val = label(fmt(value), "sub", wrap=False)
        val.setMinimumWidth(130)

        def changed(v):
            v = round(v / step) * step
            val.setText(fmt(v))
            self.cfg[key] = v
            self.changed()
        s.valueChanged.connect(changed)
        row = QHBoxLayout()
        row.addWidget(label(left, "hint", wrap=False))
        row.addWidget(s, 1)
        row.addWidget(label(right, "hint", wrap=False))
        row.addSpacing(10)
        row.addWidget(val)
        return s, row

    # ------------------------------------------------------------- paused apps

    def _paused_page(self):
        sa, lay = page_widget("Paused in apps",
                              "The wheel won't open while one of these apps is in front, so "
                              "your shortcut works normally there (great for games).")
        self.excl_list = QListWidget()
        self.excl_list.setIconSize(QSize(24, 24))
        self.excl_list.setMinimumHeight(240)
        self._fill_excluded()
        btns = QHBoxLayout()
        add_running = QPushButton("+  Add an app that's open")
        add_running.setObjectName("primary")
        add_running.setCursor(Qt.PointingHandCursor)
        add_running.clicked.connect(lambda: self._running_menu(add_running))
        browse = QPushButton("Browse for an app…")
        browse.clicked.connect(self._browse_excluded)
        self.remove_excl = QPushButton("Remove")
        self.remove_excl.setObjectName("danger")
        self.remove_excl.clicked.connect(self._remove_excluded)
        for b in (add_running, browse):
            btns.addWidget(b)
        btns.addStretch()
        btns.addWidget(self.remove_excl)
        self.excl_list.currentRowChanged.connect(
            lambda r: self.remove_excl.setEnabled(r >= 0))
        self.remove_excl.setEnabled(False)
        lay.addWidget(card(self.excl_list, btns))

        def fs(on):
            self.cfg["pause_fullscreen"] = on
            self.changed()
        row, _ = toggle_row("Also pause in any full-screen app",
                            "Covers most games and full-screen videos automatically.",
                            self.cfg["pause_fullscreen"], fs)
        lay.addWidget(card(row))
        lay.addStretch()
        return sa

    def _fill_excluded(self):
        self.excl_list.clear()
        paths = self.cfg.setdefault("excluded_paths", {})
        if not self.cfg["excluded_apps"]:
            it = QListWidgetItem("No apps yet. The wheel works everywhere.")
            it.setFlags(Qt.NoItemFlags)
            self.excl_list.addItem(it)
            return
        for name in self.cfg["excluded_apps"]:
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, name)
            p = paths.get(name)
            pm = icons.shell_pixmap(p, 24, self.devicePixelRatioF()) if p else None
            if pm:
                it.setIcon(QIcon(pm))
            self.excl_list.addItem(it)

    def _add_excluded(self, path):
        name = os.path.basename(path).lower()
        if name and name not in self.cfg["excluded_apps"]:
            self.cfg["excluded_apps"].append(name)
            self.cfg.setdefault("excluded_paths", {})[name] = path
            self._fill_excluded()
            self.changed()

    def _running_menu(self, btn):
        menu = QMenu(self)
        apps = winapi.running_window_apps()
        me = {"python.exe", "pythonw.exe", "explorer.exe", "applicationframehost.exe",
              "textinputhost.exe", "systemsettings.exe"}
        shown = 0
        for name, path in sorted(apps.items()):
            if name in me or name in self.cfg["excluded_apps"]:
                continue
            pm = icons.shell_pixmap(path, 20, self.devicePixelRatioF())
            act = menu.addAction(QIcon(pm) if pm else QIcon(), name)
            act.triggered.connect(lambda _=False, p=path: self._add_excluded(p))
            shown += 1
        if not shown:
            menu.addAction("No other apps are open right now").setEnabled(False)
        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _browse_excluded(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose an app", "C:\\Program Files",
                                              "Programs (*.exe)")
        if path:
            self._add_excluded(os.path.normpath(path))

    def _remove_excluded(self):
        it = self.excl_list.currentItem()
        name = it.data(Qt.UserRole) if it else None
        if name in self.cfg["excluded_apps"]:
            self.cfg["excluded_apps"].remove(name)
            self.cfg.get("excluded_paths", {}).pop(name, None)
            self._fill_excluded()
            self.changed()

    # ------------------------------------------------------------- look & feel

    def _look_page(self):
        sa, lay = page_widget("Look & feel", "")
        demo = WheelPreview(interactive=False)
        demo.setFixedSize(340, 340)
        demo.set_slots(self.cfg["slots"])
        demo.scale = self.cfg["size"] / 150

        slider, srow = self._slider(60, 150, self.cfg["size"], lambda v: f"{v}%", "size",
                                    "Smaller", "Bigger")

        def resize_demo():
            demo.scale = self.cfg["size"] / 150
            demo.update()
        # the slider writes cfg["size"] itself; just repaint the demo afterwards
        slider.valueChanged.connect(lambda _: resize_demo())

        def blur(on):
            self.cfg["blur"] = on
            self.changed()
        row, _ = toggle_row("Frosted glass", "Blur whatever is behind the wheel.",
                            self.cfg["blur"], blur)
        c = card(label("Wheel size", "h2"), srow, demo, row)
        c.layout().setAlignment(demo, Qt.AlignHCenter)
        lay.addWidget(c)
        lay.addStretch()
        return sa

    # ------------------------------------------------------------- general

    def _general_page(self):
        sa, lay = page_widget("General", "FlickWheel keeps running in the system tray (by the "
                                         "clock) after you close this window.")

        def startup(on):
            try:
                winapi.set_start_with_windows(on)
            except OSError as e:
                QMessageBox.warning(self, "Couldn't change that", str(e))
        row, _ = toggle_row("Start when I sign in to Windows", "", winapi.starts_with_windows(),
                            startup)
        lay.addWidget(card(row))

        row, self.pause_switch = toggle_row(
            "Pause the wheel", "Turn the wheel off until you switch this back on. "
                               "You can also do this from the tray icon.",
            self.app.hooks.paused, self.app.set_paused)
        lay.addWidget(card(row))

        open_folder = QPushButton("Open settings folder")
        open_folder.clicked.connect(lambda: os.startfile(config.CONFIG_DIR))
        reset = QPushButton("Reset everything to defaults")
        reset.setObjectName("danger")
        reset.clicked.connect(self._reset)
        brow = QHBoxLayout()
        brow.addWidget(open_folder)
        brow.addWidget(reset)
        brow.addStretch()
        lay.addWidget(card(label("Your settings", "h2"),
                           label(f"Saved automatically to {config.CONFIG_PATH}", "sub"), brow))
        lay.addStretch()
        return sa

    def _reset(self):
        if QMessageBox.question(self, "Reset everything?",
                                "This puts every slot and setting back to how it started.") \
                != QMessageBox.Yes:
            return
        self.app.reset_config()

    def sync_paused(self, paused):
        self.pause_switch.blockSignals(True)
        self.pause_switch.setChecked(paused)
        self.pause_switch.blockSignals(False)
