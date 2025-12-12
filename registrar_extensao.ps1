# Script PowerShell para registrar ManaTools no pyRevit
# Adiciona o caminho da extensão no arquivo de configuração

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Registrar ManaTools no pyRevit" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$manaPath = "C:\ProgramData\pyRevit\Extensions\ManaTools.extension"
$parentPath = "C:\ProgramData\pyRevit\Extensions"
$configPath = "$env:APPDATA\pyRevit\pyRevit_config.ini"

# Verifica se extensão existe
if (-not (Test-Path $manaPath)) {
    Write-Host "[ERRO] ManaTools não encontrado em: $manaPath" -ForegroundColor Red
    Write-Host "Execute o instalador primeiro." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[OK] ManaTools encontrado" -ForegroundColor Green

# Verifica se arquivo de config existe
if (-not (Test-Path $configPath)) {
    Write-Host "[AVISO] Config do pyRevit não encontrado" -ForegroundColor Yellow
    Write-Host "O pyRevit precisa ser executado ao menos uma vez." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Execute o Revit com pyRevit e tente novamente." -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "[OK] Config do pyRevit encontrado" -ForegroundColor Green
Write-Host ""

# Lê o arquivo de configuração
$config = Get-Content $configPath -Raw

# Verifica se já está registrado
if ($config -match [regex]::Escape($parentPath)) {
    Write-Host "[INFO] Caminho já está registrado!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Se a extensão não aparece, tente:" -ForegroundColor Yellow
    Write-Host "1. Fechar TODOS os Revit abertos" -ForegroundColor Yellow
    Write-Host "2. Abrir Revit novamente" -ForegroundColor Yellow
    Write-Host "3. pyRevit -> Settings -> Reload" -ForegroundColor Yellow
    pause
    exit 0
}

# Backup do config
$backupPath = "$configPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $configPath $backupPath
Write-Host "[OK] Backup criado: $backupPath" -ForegroundColor Green

# Adiciona o caminho ao config
$newConfig = $config -replace '(userextensions\s*=\s*\[)([^\]]*)', "`$1`$2, `"$parentPath`""
$newConfig = $newConfig -replace '\[\s*,', '['  # Remove vírgula inicial se existir

# Salva
$newConfig | Out-File -FilePath $configPath -Encoding UTF8 -NoNewline

Write-Host "[OK] Caminho adicionado ao config!" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. FECHE todos os Revit abertos" -ForegroundColor Yellow
Write-Host "2. Abra o Revit novamente" -ForegroundColor Yellow
Write-Host "3. A aba ManaTools deve aparecer!" -ForegroundColor Green
Write-Host ""
Write-Host "Se nao aparecer:" -ForegroundColor Yellow
Write-Host "- Clique no icone pyRevit e escolha Reload" -ForegroundColor Yellow
Write-Host ""
pause

