@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════════════════
echo  📦 GERAR HASH DO INSTALADOR (para publicação)
echo ═══════════════════════════════════════════════════════════
echo.

set "INSTALLER=dist\ManaToolsSetup_1.0.1.exe"

if not exist "%INSTALLER%" (
    echo ❌ Instalador não encontrado: %INSTALLER%
    echo.
    echo Compile o instalador primeiro!
    pause
    exit /b 1
)

echo Calculando SHA256 do instalador...
echo.

certutil -hashfile "%INSTALLER%" SHA256 > "%INSTALLER%.sha256"

echo ✅ Hash gerado com sucesso!
echo.
type "%INSTALLER%.sha256"
echo.
echo 📄 Arquivo salvo: %INSTALLER%.sha256
echo.
echo ═══════════════════════════════════════════════════════════
echo.
echo 📋 INSTRUÇÕES:
echo.
echo 1. Suba AMBOS os arquivos para seu servidor:
echo    - ManaToolsSetup_1.0.1.exe
echo    - ManaToolsSetup_1.0.1.exe.sha256
echo.
echo 2. No site, publique o hash para os usuários verificarem
echo.
echo 3. Usuários podem verificar com:
echo    certutil -hashfile ManaToolsSetup_1.0.1.exe SHA256
echo.
echo ═══════════════════════════════════════════════════════════
echo.
pause

