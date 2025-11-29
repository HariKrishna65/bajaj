@echo off
echo ========================================
echo   Bill Extraction API - ngrok Tunnel
echo ========================================
echo.

REM Check if ngrok is installed
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] ngrok is not installed or not in PATH
    echo Please install ngrok from: https://ngrok.com/download
    echo.
    pause
    exit /b 1
)

echo [1/2] Starting FastAPI server on port 8000...
start "FastAPI Server" cmd /k "title FastAPI Server && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [2/2] Waiting 5 seconds for server to start...
timeout /t 5 /nobreak >nul

echo [3/3] Starting ngrok tunnel...
echo.
echo ========================================
echo   ngrok will display your public URL
echo   Check the ngrok window for the URL
echo ========================================
echo.
start "ngrok Tunnel" cmd /k "title ngrok Tunnel && ngrok http 8000"

echo.
echo Local API: http://localhost:8000
echo ngrok Web UI: http://127.0.0.1:4040
echo.
echo Press any key to stop servers...
pause >nul

REM Clean up - kill the processes
taskkill /FI "WINDOWTITLE eq FastAPI Server*" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq ngrok Tunnel*" /T /F >nul 2>nul

echo.
echo Servers stopped.

