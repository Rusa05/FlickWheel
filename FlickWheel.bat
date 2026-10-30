@echo off
rem Starts FlickWheel without a console window. Run it again to open settings.
cd /d "%~dp0"
python -c "import PySide6" 2>nul || python -m pip install -r requirements.txt
start "" pythonw "%~dp0main.py"
