@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Follow docs\WINDOWS_OFFLINE_DEPLOYMENT.md to install offline.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys, struct, sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 14) and struct.calcsize('P') == 8 and not sysconfig.get_config_var('Py_GIL_DISABLED') else 1)"
if errorlevel 1 (
  echo This delivery requires regular CPython 3.14 x64.
  pause
  exit /b 1
)
echo Open http://127.0.0.1:8000/ in this computer's browser. Press Ctrl+C to stop.
".venv\Scripts\python.exe" run.py
set "CONFIGM_EXIT=%ERRORLEVEL%"
if not "%CONFIGM_EXIT%"=="0" (
  echo ConfigM stopped with error %CONFIGM_EXIT%. Review the message above.
  pause
)
exit /b %CONFIGM_EXIT%
