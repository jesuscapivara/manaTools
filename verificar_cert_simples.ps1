# Verifica certificado com senha como parametro

$CertPath = ".\LUCAS ROSSETTI DE SOUZA03047354006.pfx"
$Password = "160893"

Write-Host ""
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host " VERIFICAR CERTIFICADO - Lucas Rossetti" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $CertPath)) {
    Write-Host "ERRO: Certificado nao encontrado!" -ForegroundColor Red
    exit 1
}

Write-Host "OK: Certificado encontrado" -ForegroundColor Green
Write-Host ""

try {
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($CertPath, $SecurePassword)
    
    Write-Host "===================================================================" -ForegroundColor White
    Write-Host "INFORMACOES DO CERTIFICADO:" -ForegroundColor White
    Write-Host "===================================================================" -ForegroundColor White
    Write-Host ""
    Write-Host "Titular: " -NoNewline -ForegroundColor Cyan
    Write-Host $cert.Subject
    Write-Host ""
    Write-Host "Emissor: " -NoNewline -ForegroundColor Cyan
    Write-Host $cert.Issuer
    Write-Host ""
    Write-Host "Valido de: " -NoNewline -ForegroundColor Cyan
    Write-Host $cert.NotBefore.ToString("dd/MM/yyyy")
    Write-Host "Valido ate: " -NoNewline -ForegroundColor Cyan
    Write-Host $cert.NotAfter.ToString("dd/MM/yyyy")
    Write-Host ""
    
    # Verifica validade
    $now = Get-Date
    if ($cert.NotAfter -lt $now) {
        Write-Host "AVISO: CERTIFICADO EXPIRADO!" -ForegroundColor Red
        Write-Host ""
    } elseif ($cert.NotBefore -gt $now) {
        Write-Host "AVISO: Certificado ainda nao esta valido!" -ForegroundColor Yellow
        Write-Host ""
    } else {
        Write-Host "OK: Certificado VALIDO" -ForegroundColor Green
        Write-Host ""
    }
    
    Write-Host "===================================================================" -ForegroundColor White
    Write-Host "USO PERMITIDO (Enhanced Key Usage):" -ForegroundColor White
    Write-Host "===================================================================" -ForegroundColor White
    Write-Host ""
    
    $ekuExtension = $cert.Extensions | Where-Object { $_.Oid.FriendlyName -eq "Enhanced Key Usage" }
    
    $canSignCode = $false
    
    if ($ekuExtension) {
        $eku = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]$ekuExtension
        
        foreach ($usage in $eku.EnhancedKeyUsages) {
            Write-Host "  + $($usage.FriendlyName) ($($usage.Value))" -ForegroundColor White
            
            if ($usage.Value -eq "1.3.6.1.5.5.7.3.3") {
                $canSignCode = $true
            }
        }
    } else {
        Write-Host "  INFO: Nenhuma restricao de uso (aceita qualquer uso)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "===================================================================" -ForegroundColor White
    Write-Host "RESULTADO DA ANALISE:" -ForegroundColor White
    Write-Host "===================================================================" -ForegroundColor White
    Write-Host ""
    
    if ($canSignCode) {
        Write-Host "*** EXCELENTE! ***" -ForegroundColor Green
        Write-Host ""
        Write-Host "Este certificado PODE assinar codigo executavel!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Voce pode usar o script:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host '.\assinar_instalador.ps1 -CertificatePath ".\LUCAS ROSSETTI DE SOUZA03047354006.pfx"' -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "*** RESULTADO NEGATIVO ***" -ForegroundColor Red
        Write-Host ""
        Write-Host "Este certificado NAO pode assinar codigo executavel." -ForegroundColor Red
        Write-Host ""
        Write-Host "Este e um certificado e-CPF (ICP-Brasil), usado para:" -ForegroundColor Yellow
        Write-Host "  - Assinar documentos (PDF, XML)" -ForegroundColor White
        Write-Host "  - Autenticacao em sites governamentais" -ForegroundColor White
        Write-Host "  - Nota Fiscal Eletronica" -ForegroundColor White
        Write-Host ""
        Write-Host "Para assinar instaladores (.exe), voce precisa comprar um:" -ForegroundColor Yellow
        Write-Host "  Code Signing Certificate" -ForegroundColor White
        Write-Host ""
        Write-Host "Recomendacao: Certum (100 euros/ano)" -ForegroundColor Cyan
        Write-Host "https://www.certum.eu/en/code-signing-certificates/" -ForegroundColor Cyan
        Write-Host ""
    }
    
    $cert.Dispose()
}
catch {
    Write-Host ""
    Write-Host "ERRO ao ler certificado: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possiveis causas:" -ForegroundColor Yellow
    Write-Host "  - Senha incorreta" -ForegroundColor White
    Write-Host "  - Arquivo corrompido" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

