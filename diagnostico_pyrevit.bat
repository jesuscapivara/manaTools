@echo off
echo ========================================
echo   Diagnostico pyRevit - ManaTools
echo ========================================
echo.

echo [1] Verificando instalacao do pyRevit...
if exist "C:\Program Files\pyRevit-Master\" (
    echo [OK] pyRevit encontrado em: C:\Program Files\pyRevit-Master\
) else (
    echo [AVISO] pyRevit nao encontrado no caminho padrao
)

echo.
echo [2] Verificando pastas de extensoes do pyRevit...
echo.
echo Pasta oficial de extensoes:
if exist "%ProgramData%\pyRevit\Extensions\" (
    echo [OK] %ProgramData%\pyRevit\Extensions\
    echo Conteudo:
    dir /b "%ProgramData%\pyRevit\Extensions\"
) else (
    echo [ERRO] Pasta nao existe!
)

echo.
echo Pasta de usuario (AppData):
if exist "%AppData%\pyRevit\Extensions\" (
    echo [OK] %AppData%\pyRevit\Extensions\
    echo Conteudo:
    dir /b "%AppData%\pyRevit\Extensions\"
) else (
    echo [INFO] Pasta de usuario nao existe (normal)
)

echo.
echo [3] Verificando arquivo de configuracao do pyRevit...
set PYREVIT_CONFIG=%AppData%\pyRevit\pyRevit_config.ini
if exist "%PYREVIT_CONFIG%" (
    echo [OK] Configuracao encontrada
    echo.
    echo === TRECHO DO CONFIG ===
    findstr /i "extension" "%PYREVIT_CONFIG%" 2>nul
    echo ========================
) else (
    echo [INFO] Config nao encontrado (usara defaults)
)

echo.
echo [4] Verificando se ManaTools esta instalado corretamente...
set MANA_PATH=%ProgramData%\pyRevit\Extensions\ManaTools.extension
if exist "%MANA_PATH%\extension.json" (
    echo [OK] ManaTools instalado em: %MANA_PATH%
    echo.
    echo Estrutura:
    dir /b "%MANA_PATH%"
) else (
    echo [ERRO] ManaTools nao encontrado ou incompleto!
)

echo.
echo [5] Logs do pyRevit...
set PYREVIT_LOGS=%AppData%\pyRevit\pyRevit_*
if exist "%AppData%\pyRevit\" (
    echo Pasta de logs: %AppData%\pyRevit\
    echo Arquivos de log recentes:
    dir /b /o-d "%AppData%\pyRevit\*.log" 2>nul | findstr /i "pyRevit" | more
) else (
    echo [INFO] Sem logs encontrados
)

echo.
echo ========================================
echo   PROXIMOS PASSOS:
echo ========================================
echo.
echo 1. Abra o Revit
echo 2. Clique no icone pyRevit (canto superior direito)
echo 3. Settings -^> Core Settings
echo 4. Em "Custom Extension Directories", adicione:
echo    %MANA_PATH%
echo 5. Clique "Save Settings and Reload"
echo.
echo OU rode: pyrevit_add_path.bat (vou criar agora)
echo.
pause

