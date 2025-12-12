@echo off
echo ========================================
echo   Adicionar ManaTools ao pyRevit
echo ========================================
echo.

set MANA_PATH=C:\ProgramData\pyRevit\Extensions\ManaTools.extension

echo Este script vai adicionar o caminho da extensao
echo nas configuracoes do pyRevit.
echo.
echo Caminho: %MANA_PATH%
echo.
pause

echo.
echo [1] Verificando pyRevit CLI...
where pyrevit >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] pyRevit CLI encontrado
    echo.
    echo [2] Adicionando extensao...
    pyrevit extend ui ManaTools "%MANA_PATH%"
    
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Extensao adicionada com sucesso!
        echo.
        echo Reinicie o Revit para ver a aba ManaTools
    ) else (
        echo [ERRO] Falha ao adicionar extensao
        echo Tente manualmente: pyRevit Settings -^> Custom Extension Directories
    )
) else (
    echo [AVISO] pyRevit CLI nao encontrado
    echo.
    echo SOLUCAO MANUAL:
    echo 1. Abra o Revit
    echo 2. Clique no icone pyRevit
    echo 3. Settings -^> Custom Extension Directories
    echo 4. Clique "Add folder"
    echo 5. Selecione: %MANA_PATH%
    echo 6. Clique "Save Settings and Reload"
)

echo.
pause

