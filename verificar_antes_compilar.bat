@echo off
echo ========================================
echo   Verificar Estrutura Antes de Compilar
echo ========================================
echo.

set ERROR_COUNT=0

echo [1/5] Verificando pasta ManaTools.extension...
if exist "ManaTools.extension\" (
    echo [OK] Pasta existe
) else (
    echo [ERRO] Pasta ManaTools.extension NAO encontrada!
    set /a ERROR_COUNT+=1
)

echo.
echo [2/5] Verificando extension.json...
if exist "ManaTools.extension\extension.json" (
    echo [OK] extension.json existe
    type "ManaTools.extension\extension.json"
) else (
    echo [ERRO] extension.json NAO encontrado!
    set /a ERROR_COUNT+=1
)

echo.
echo [3/5] Verificando estrutura de pastas...
if exist "ManaTools.extension\ManaTools.tab\" (
    echo [OK] ManaTools.tab existe
) else (
    echo [ERRO] ManaTools.tab NAO encontrado!
    set /a ERROR_COUNT+=1
)

if exist "ManaTools.extension\lib\" (
    echo [OK] lib existe
) else (
    echo [AVISO] lib NAO encontrado
)

echo.
echo [4/5] Listando conteudo da extensao...
dir /b /s "ManaTools.extension\*.py" 2>nul | find /c /v "" > temp_count.txt
set /p FILE_COUNT=<temp_count.txt
del temp_count.txt
echo Arquivos Python encontrados: %FILE_COUNT%

echo.
echo [5/5] Verificando script do instalador...
if exist "ManaToolsSetup.iss" (
    echo [OK] ManaToolsSetup.iss existe
) else (
    echo [ERRO] ManaToolsSetup.iss NAO encontrado!
    set /a ERROR_COUNT+=1
)

echo.
echo ========================================
if %ERROR_COUNT% EQU 0 (
    echo [SUCESSO] Tudo pronto para compilar!
    echo Execute: build.bat
) else (
    echo [FALHA] %ERROR_COUNT% erro(s) encontrado(s)
    echo Corrija os problemas antes de compilar
)
echo ========================================
echo.
pause

