@echo off
nuitka --onefile --standalone --enable-plugin=pyqt5 --remove-output --include-data-files=style.css=style.css --windows-icon-from-ico=ICON.ico --windows-console-mode=disable --output-dir=dist resmon.py
pause