@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════════════════
echo  🔍 TESTAR CERTIFICADO e-CPF PARA ASSINATURA DE CÓDIGO
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

echo Este script tentará assinar o instalador com seu certificado e-CPF.
echo.
echo ⚠️  RESULTADO ESPERADO: FALHA (e-CPF não é válido para código)
echo.
pause

echo.
echo 📋 Certificados disponíveis no seu PC:
echo.

REM Lista certificados do repositório pessoal
certutil -store -user My

echo.
echo ═══════════════════════════════════════════════════════════
echo.
echo 🔍 ANÁLISE:
echo.
echo Procure seu certificado e-CPF na lista acima.
echo.
echo Se no campo "Enhanced Key Usage" NÃO aparecer:
echo   - "Code Signing (1.3.6.1.5.5.7.3.3)"
echo.
echo Então ele NÃO pode ser usado para assinar executáveis.
echo.
echo Certificados ICP-Brasil (e-CPF) geralmente têm:
echo   - "Secure Email (1.3.6.1.5.5.7.3.4)"
echo   - "Client Authentication (1.3.6.1.5.5.7.3.2)"
echo.
echo Mas NÃO têm "Code Signing".
echo.
echo ═══════════════════════════════════════════════════════════
echo.
pause

