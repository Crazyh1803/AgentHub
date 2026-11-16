@echo off
rem Double-click to start Agent Hub and open it in your default browser.
rem Close this window (or press Ctrl+C) to stop the server.
setlocal
rem Set HUB_PORT before running to use a different port.
set "HUB_HOST=127.0.0.1"
if not defined HUB_PORT set "HUB_PORT=8000"
set "HUB_URL=http://%HUB_HOST%:%HUB_PORT%/"

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo No virtual environment found in "%~dp0.venv".
    echo Create it once with:
    echo     py -3.12 -m venv .venv
    echo     .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

rem Wait in the background until the server answers, then open the browser.
start "" /b powershell -NoProfile -WindowStyle Hidden -Command ^
  "for ($i = 0; $i -lt 120; $i++) { try { Invoke-WebRequest '%HUB_URL%' -UseBasicParsing | Out-Null; break } catch { Start-Sleep -Milliseconds 500 } }; Start-Process '%HUB_URL%'"

echo Starting Agent Hub at %HUB_URL%
python -m uvicorn app.main:app --host %HUB_HOST% --port %HUB_PORT%

echo.
echo Agent Hub has stopped.
pause
