@echo off
chcp 65001 >nul
echo ========================================
echo Correção do Config do pyRevit
echo ========================================
echo.

set CONFIG_PATH=%APPDATA%\pyRevit\pyRevit_config.ini

if not exist "%CONFIG_PATH%" (
    echo [OK] Arquivo de config não existe ou já foi corrigido.
    echo O pyRevit criará um novo na próxima execução.
    pause
    exit /b 0
)

echo [!] Arquivo de config encontrado: %CONFIG_PATH%
echo.
echo Este script irá:
echo 1. Fazer backup do arquivo atual
echo 2. Deletar o arquivo corrompido
echo 3. O pyRevit criará um novo na próxima abertura
echo.

choice /C SN /M "Deseja continuar"
if errorlevel 2 goto :cancelado
if errorlevel 1 goto :continuar

:continuar
echo.
echo [1/3] Criando backup...
set BACKUP_PATH=%CONFIG_PATH%.backup_corrupto_%DATE:~-4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
copy "%CONFIG_PATH%" "%BACKUP_PATH%" >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Falha ao criar backup
    pause
    exit /b 1
)
echo [OK] Backup criado: %BACKUP_PATH%

echo.
echo [2/3] Deletando arquivo corrompido...
del "%CONFIG_PATH%" >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Falha ao deletar arquivo
    pause
    exit /b 1
)
echo [OK] Arquivo deletado

echo.
echo [3/3] Registrando extensão...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0registrar_extensao_instalador.ps1" -ExtensionPath "C:\ProgramData\pyRevit\Extensions"
if errorlevel 1 (
    echo [AVISO] Erro ao registrar extensão. Execute manualmente após abrir o pyRevit.
) else (
    echo [OK] Extensão registrada
)

echo.
echo ========================================
echo [CONCLUÍDO]
echo ========================================
echo.
echo Próximos passos:
echo 1. Abra o Revit
echo 2. O pyRevit criará um novo arquivo de config
echo 3. A aba ManaTools deve aparecer automaticamente
echo.
echo Se não aparecer, clique no ícone pyRevit e escolha "Reload"
echo.
pause
exit /b 0

:cancelado
echo.
echo Operação cancelada pelo usuário.
pause
exit /b 0

