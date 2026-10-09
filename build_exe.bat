@echo off
chcp 65001 >nul
py -m pip install --upgrade pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name DafanTikTokControl app.py
pause
