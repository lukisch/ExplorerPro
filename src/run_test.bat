@echo off
chcp 65001 >nul
cd /d "%~dp0"
python test_bug.py
echo.
echo Test beendet.
