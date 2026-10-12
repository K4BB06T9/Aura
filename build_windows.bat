@echo off
REM One-click build: creates dist\Aura.exe  (needs Python 3.10+ from python.org, with "Add to PATH" ticked)
python -m venv .venv || goto :err
call .venv\Scripts\activate || goto :err
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller || goto :err
python build.py || goto :err
echo.
echo Done! Your app is at: %cd%\dist\Aura.exe
pause
exit /b 0
:err
echo Build failed - see the messages above.
pause
exit /b 1
