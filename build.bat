@echo off
REM Script para compilar instalador ManaTools
REM Requer Inno Setup 6 instalado

echo ========================================
echo   ManaTools - Build Instalador
echo ========================================
echo.

REM Caminho padrão do Inno Setup
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

REM Verifica se existe
if not exist %ISCC% (
    echo ERRO: Inno Setup nao encontrado em %ISCC%
    echo Instale o Inno Setup 6: https://jrsoftware.org/isdl.php
    pause
    exit /b 1
)

echo [1/3] Verificando arquivos...
if not exist "ManaTools.extension\" (
    echo ERRO: Pasta ManaTools.extension nao encontrada!
    pause
    exit /b 1
)

if not exist "ManaToolsSetup.iss" (
    echo ERRO: Script ManaToolsSetup.iss nao encontrado!
    pause
    exit /b 1
)

echo [2/3] Compilando instalador...
%ISCC% ManaToolsSetup.iss

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO: Falha na compilacao!
    pause
    exit /b 1
)

echo.
echo [3/3] Sucesso!
echo.
echo Instalador gerado em: .\dist\
dir /b dist\*.exe 2>nul

echo.
echo ========================================
echo   Build concluido com sucesso!
echo ========================================
pause

