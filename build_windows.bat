@echo off
chcp 65001 >nul
REM عرب لعبتك | Arabize Game — يبني ملف التشغيل لويندوز في مجلد dist\ArabizeGame
REM المتطلب: Python 3.11 أو 3.12 (64-bit) من python.org مع خيار "Add to PATH"
cd /d "%~dp0"
if not exist .venv ( py -3.12 -m venv .venv 2>nul || py -3.11 -m venv .venv 2>nul || python -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-dev.txt || goto :err
REM OCR على كرت الشاشة: نسخة onnxruntime التي تدعم DirectML
pip uninstall -y onnxruntime
pip install --no-deps onnxruntime-directml || goto :err
REM قارئ الإطارات FPS (PresentMon من Intel، رخصة MIT) — اختياري: يُبنى البرنامج بدونه إن تعذّر التحميل
if not exist vendor mkdir vendor
if not exist vendor\PresentMon.exe (
  powershell -NoProfile -Command "$r = Invoke-RestMethod https://api.github.com/repos/GameTechDev/PresentMon/releases/latest; $a = $r.assets | Where-Object { $_.name -like 'PresentMon-*-x64.exe' } | Select-Object -First 1; if ($a) { Invoke-WebRequest $a.browser_download_url -OutFile vendor\PresentMon.exe }"
)
echo.
echo === تشغيل الاختبارات ===
python -m pytest -q tests\test_core.py tests\test_ocr.py tests\test_looks.py tests\test_windows.py tests\test_v13.py tests\test_v14.py || goto :err
echo.
echo === بناء البرنامج ===
pyinstaller --noconfirm ArabizeGame.spec || goto :err
echo.
echo تم! شغّل: dist\ArabizeGame\ArabizeGame.exe
pause
exit /b 0
:err
echo حدث خطأ أثناء البناء — راجع الرسائل أعلاه.
pause
exit /b 1
