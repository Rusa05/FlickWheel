# FlickWheel

A radial action wheel for Windows. Hold a shortcut, flick toward an action, and let go.

## Start it

Double-click **`FlickWheel.bat`**. On first run it installs PySide6 if it's missing, then opens the settings window and puts an icon in the system tray. Run it again at any time to bring back settings.

## Using the wheel

| Do this | What happens |
|---|---|
| Hold **Ctrl + Space** (or your chosen mouse button) | The wheel opens at your cursor |
| Move toward a slot, then let go | That action runs |
| Flick past the edge of the wheel | It runs straight away, without letting go |
| Flick into (or rest on) a folder slot | Its second wheel opens |
| Let go in the middle, press **Esc**, or right-click | Cancel |
| Quick tap of the mouse trigger | A normal click, as usual |

Everything else (slots, actions, icons, trigger, paused apps, size, start with Windows) is in the settings window. Changes save automatically to `%APPDATA%\FlickWheel\config.json`.

## Good to know

- Ctrl + Space is swallowed while FlickWheel runs, so apps that use it (like VS Code's suggestions) won't see it. Pick another trigger, or add those apps to **Paused in apps**.
- Windows doesn't let normal apps see input while an **administrator** window is in front (e.g. Task Manager), so the wheel won't open there.
- The wheel is hidden from screenshots and screen recordings. That's how the frosted-glass blur works.

## Code layout

| File | What it does |
|---|---|
| `main.py` | Entry point |
| `flickwheel/app.py` | Tray icon, single instance, saving |
| `flickwheel/hooks.py` | System-wide keyboard/mouse hooks (trigger detection, shortcut recording) |
| `flickwheel/wheel.py` | Wheel drawing, overlay window, hold/flick/release logic |
| `flickwheel/actions.py` | Every action type, gesture, and media key; adding a new gesture is one line in `SYSTEM_ACTIONS` |
| `flickwheel/settings.py`, `widgets.py` | The settings window |
| `flickwheel/icons.py` | Built-in icon set and app-icon loading |
| `flickwheel/winapi.py` | Windows API helpers |
