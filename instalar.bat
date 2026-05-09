@echo off
chcp 65001 >nul
echo ============================================
echo   Flight Alert Bot — Instalador
echo ============================================
echo.

set PYTHON="C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python39_64\python.exe"

echo [1/3] Instalando dependencias Python...
%PYTHON% -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERRO ao instalar dependencias!
    pause
    exit /b 1
)
echo OK

echo.
echo [2/3] Instalando navegador Chromium para o Playwright...
%PYTHON% -m playwright install chromium
if errorlevel 1 (
    echo ERRO ao instalar o Chromium!
    pause
    exit /b 1
)
echo OK

echo.
echo [3/3] Tudo instalado com sucesso!
echo.
echo Para iniciar o bot, execute:  iniciar.bat
echo ============================================
pause
