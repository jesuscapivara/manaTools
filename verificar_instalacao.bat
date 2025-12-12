@echo off
echo ========================================
echo   ManaTools - Verificar Instalacao
echo ========================================
echo.

set INSTALL_PATH=%ProgramData%\pyRevit\Extensions\ManaTools.extension

echo Verificando pasta de instalacao...
echo Caminho: %INSTALL_PATH%
echo.

if exist "%INSTALL_PATH%" (
    echo [OK] Pasta de instalacao existe!
    echo.
    echo Conteudo:
    dir /b "%INSTALL_PATH%"
    echo.
    
    if exist "%INSTALL_PATH%\extension.json" (
        echo [OK] extension.json encontrado
        type "%INSTALL_PATH%\extension.json"
    ) else (
        echo [ERRO] extension.json NAO encontrado!
    )
    
    echo.
    echo Abrindo pasta...
    explorer "%INSTALL_PATH%"
) else (
    echo [ERRO] Pasta de instalacao NAO existe!
    echo.
    echo A extensao nao foi copiada corretamente.
    echo Reinstale o ManaTools ou copie manualmente para:
    echo %INSTALL_PATH%
)

echo.
pause

