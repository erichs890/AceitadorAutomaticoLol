@echo off
setlocal
cd /d "%~dp0"

rem --- tenta achar o Python no PATH ---
where python >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw interface.py
    exit /b 0
)

rem --- tenta o launcher py ---
where py >nul 2>&1
if %errorlevel%==0 (
    start "" pyw interface.py
    exit /b 0
)

echo.
echo ==============================================================
echo   Python nao encontrado no seu computador.
echo.
echo   Baixe e instale o Python em: https://www.python.org/downloads/
echo   Na instalacao, MARQUE a caixa "Add Python to PATH".
echo ==============================================================
echo.
pause
exit /b 1
