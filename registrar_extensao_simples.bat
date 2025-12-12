@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Registrar ManaTools no pyRevit
echo ========================================
echo.

set "PARENT_PATH=C:\ProgramData\pyRevit\Extensions"
set "MANA_PATH=%PARENT_PATH%\ManaTools.extension"
set "CONFIG_PATH=%APPDATA%\pyRevit\pyRevit_config.ini"

echo [1/4] Verificando instalacao...
if not exist "%MANA_PATH%" (
    echo [ERRO] ManaTools nao encontrado em: %MANA_PATH%
    pause
    exit /b 1
)
echo [OK] ManaTools encontrado

echo.
echo [2/4] Verificando config do pyRevit...
if not exist "%CONFIG_PATH%" (
    echo [ERRO] Config do pyRevit nao encontrado
    echo Execute o Revit com pyRevit ao menos uma vez
    pause
    exit /b 1
)
echo [OK] Config encontrado

echo.
echo [3/4] Verificando se ja esta registrado...
findstr /C:"%PARENT_PATH%" "%CONFIG_PATH%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Caminho ja esta registrado!
    echo.
    echo Tente:
    echo 1. Feche TODOS os Revit
    echo 2. Abra o Revit novamente
    echo 3. pyRevit -^> Reload
    pause
    exit /b 0
)

echo [INFO] Caminho nao encontrado, adicionando...

echo.
echo [4/4] Criando backup e atualizando config...
copy "%CONFIG_PATH%" "%CONFIG_PATH%.backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%" >nul
echo [OK] Backup criado

echo.
echo IMPORTANTE: Feche o Revit antes de continuar!
pause

powershell -Command "(Get-Content '%CONFIG_PATH%') -replace 'userextensions\s*=\s*\[([^\]]*)', 'userextensions = [$1, \"%PARENT_PATH:\=\\%\"' -replace '\[\s*,', '[' | Set-Content '%CONFIG_PATH%' -Encoding UTF8"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Config atualizado!
    echo.
    echo ========================================
    echo   SUCESSO!
    echo ========================================
    echo.
    echo PROXIMOS PASSOS:
    echo 1. Abra o Revit
    echo 2. A aba ManaTools deve aparecer
    echo.
    echo Se nao aparecer, clique em pyRevit e Reload
) else (
    echo [ERRO] Falha ao atualizar config
    echo Adicione manualmente via pyRevit Settings
)

echo.
pause

