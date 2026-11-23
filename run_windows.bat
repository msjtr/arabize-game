@echo off
chcp 65001 >nul
REM تشغيل عرب لعبتك من الكود مباشرة (بدون بناء)
cd /d "%~dp0"
if not exist .venv ( py -3.12 -m venv .venv 2>nul || py -3.11 -m venv .venv 2>nul || python -m venv .venv
  call .venv\Scripts\activate.bat & pip install -r requirements.txt )
call .venv\Scripts\activate.bat
start "" pythonw main.py
