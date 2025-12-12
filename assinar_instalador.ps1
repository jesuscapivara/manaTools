# Script para Assinar Digitalmente o Instalador ManaTools
# Requer: Windows SDK instalado (SignTool.exe)
# Requer: Certificado de Assinatura de Código (.pfx)

param(
    [string]$CertificatePath = ".\certificado.pfx",
    [string]$CertificatePassword = "",
    [string]$InstallerPath = ".\dist\ManaToolsSetup_1.0.1.exe"
)

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " 🔐 ASSINAR INSTALADOR MANATOOLS" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar se o instalador existe
if (-not (Test-Path $InstallerPath)) {
    Write-Host "❌ Instalador não encontrado: $InstallerPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Compile o instalador primeiro com Inno Setup!" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# 2. Verificar se o certificado existe
if (-not (Test-Path $CertificatePath)) {
    Write-Host "❌ Certificado não encontrado: $CertificatePath" -ForegroundColor Red
    Write-Host ""
    Write-Host "INSTRUÇÕES:" -ForegroundColor Yellow
    Write-Host "1. Coloque seu certificado .pfx na raiz do projeto" -ForegroundColor White
    Write-Host "2. Renomeie para 'certificado.pfx'" -ForegroundColor White
    Write-Host "3. Execute novamente este script" -ForegroundColor White
    Write-Host ""
    Write-Host "OU especifique o caminho:" -ForegroundColor Yellow
    Write-Host '.\assinar_instalador.ps1 -CertificatePath "C:\caminho\certificado.pfx"' -ForegroundColor White
    Write-Host ""
    exit 1
}

# 3. Solicitar senha se não foi fornecida
if ([string]::IsNullOrEmpty($CertificatePassword)) {
    $SecurePassword = Read-Host -AsSecureString "🔑 Digite a senha do certificado"
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
    $CertificatePassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# 4. Localizar SignTool.exe
$SignToolPaths = @(
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\bin\10.0.18362.0\x64\signtool.exe",
    "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\signtool.exe"
)

$SignTool = $null
foreach ($path in $SignToolPaths) {
    if (Test-Path $path) {
        $SignTool = $path
        break
    }
}

if ($null -eq $SignTool) {
    Write-Host "❌ SignTool.exe não encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "SOLUÇÃO:" -ForegroundColor Yellow
    Write-Host "Instale o Windows SDK:" -ForegroundColor White
    Write-Host "https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host "✓ Instalador encontrado: $InstallerPath" -ForegroundColor Green
Write-Host "✓ Certificado encontrado: $CertificatePath" -ForegroundColor Green
Write-Host "✓ SignTool encontrado: $SignTool" -ForegroundColor Green
Write-Host ""

# 5. Assinar o instalador
Write-Host "🔏 Assinando instalador..." -ForegroundColor Yellow
Write-Host ""

$Arguments = @(
    "sign",
    "/f", "`"$CertificatePath`"",
    "/p", "`"$CertificatePassword`"",
    "/t", "http://timestamp.sectigo.com",
    "/fd", "SHA256",
    "/d", "ManaTools - Extensão pyRevit para Revit",
    "/du", "https://www.manatools.com.br",
    "`"$InstallerPath`""
)

try {
    $Process = Start-Process -FilePath $SignTool -ArgumentList $Arguments -Wait -NoNewWindow -PassThru
    
    if ($Process.ExitCode -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host " ✅ INSTALADOR ASSINADO COM SUCESSO!" -ForegroundColor Green
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
        Write-Host ""
        Write-Host "📦 Arquivo: $InstallerPath" -ForegroundColor White
        Write-Host ""
        Write-Host "Agora o Windows não bloqueará mais este instalador!" -ForegroundColor Cyan
        Write-Host ""
        
        # Verificar assinatura
        Write-Host "🔍 Verificando assinatura..." -ForegroundColor Yellow
        & $SignTool verify /pa "`"$InstallerPath`""
        Write-Host ""
    }
    else {
        Write-Host ""
        Write-Host "❌ Erro ao assinar instalador (Código: $($Process.ExitCode))" -ForegroundColor Red
        Write-Host ""
        Write-Host "Possíveis causas:" -ForegroundColor Yellow
        Write-Host "- Senha incorreta" -ForegroundColor White
        Write-Host "- Certificado expirado" -ForegroundColor White
        Write-Host "- Certificado inválido para assinatura de código" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}
catch {
    Write-Host ""
    Write-Host "❌ Erro ao executar SignTool: $_" -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

