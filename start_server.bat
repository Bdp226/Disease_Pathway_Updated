@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%Digitization-of-Disease-Pathways-main (1)"
set "FRONTEND_DIR=%APP_DIR%\frontend\disease-pathways"
set "PY_EXE=%ROOT_DIR%.venv\Scripts\python.exe"

echo ==============================================
echo Disease Pathways - Canonical Startup
echo ==============================================
echo Using updated app copy:
echo %APP_DIR%
echo.

if exist "%APP_DIR%\main.py" goto app_ok
echo [ERROR] Updated app folder not found:
echo %APP_DIR%
exit /b 1

:app_ok
if exist "%FRONTEND_DIR%\package.json" goto frontend_ok
echo [ERROR] Frontend folder not found:
echo %FRONTEND_DIR%
exit /b 1

:frontend_ok
if exist "%PY_EXE%" goto python_ok
echo [ERROR] Python virtual environment missing at:
echo %PY_EXE%
echo Create/restore the .venv folder, then retry.
exit /b 1

:python_ok

echo [1/4] Stopping stale processes on ports 8000 and 5173...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = 8000,5173; foreach ($p in $ports) { $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue; if ($conns) { $ids = $conns | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($id in $ids) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } } }"

echo [2/4] Checking Node dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
  echo node_modules not found. Installing frontend dependencies...
  pushd "%FRONTEND_DIR%"
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    popd
    exit /b 1
  )
  popd
)

echo [3/4] Starting backend (updated copy)...
start "Disease Backend (Updated)" cmd /k "cd /d \"%APP_DIR%\" && \"%PY_EXE%\" -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [4/4] Starting frontend (updated copy)...
start "Disease Frontend (Updated)" cmd /k "cd /d \"%FRONTEND_DIR%\" && npm run dev -- --host 0.0.0.0 --port 5173"

echo.
echo ==============================================
echo Startup complete.
echo Backend:  http://127.0.0.1:8000/docs
echo Frontend: http://127.0.0.1:5173/
echo ==============================================
echo.
echo IMPORTANT: Always use this file to start the project.
exit /b 0
