# -*- coding: utf-8 -*-
# Script de registro da extensão ManaTools no pyRevit
# Executado automaticamente pelo instalador
# Usa UTF-8 para evitar corrupção do arquivo de config

param(
    [string]$ExtensionPath
)

$ErrorActionPreference = "Stop"

# Caminho do config do pyRevit
$ConfigPath = "$env:APPDATA\pyRevit\pyRevit_config.ini"

Write-Host "=== Registro ManaTools no pyRevit ===" -ForegroundColor Cyan
Write-Host "Config: $ConfigPath"
Write-Host "Extension: $ExtensionPath"

# Verifica se o arquivo de config existe
if (-not (Test-Path $ConfigPath)) {
    Write-Host "Config do pyRevit não encontrado. O pyRevit criará na primeira execução." -ForegroundColor Yellow
    exit 0
}

# Cria backup
$BackupPath = "$ConfigPath.backup_manatools_" + (Get-Date -Format "yyyyMMdd_HHmmss")
Copy-Item $ConfigPath $BackupPath -Force
Write-Host "Backup criado: $BackupPath" -ForegroundColor Green

try {
    # Lê o arquivo com UTF-8
    $ConfigContent = Get-Content $ConfigPath -Encoding UTF8 -Raw
    
    # Verifica se o caminho já está registrado
    if ($ConfigContent -match [regex]::Escape($ExtensionPath)) {
        Write-Host "Caminho já registrado no config. Nada a fazer." -ForegroundColor Green
        exit 0
    }
    
    # Divide em linhas para processar
    $Lines = Get-Content $ConfigPath -Encoding UTF8
    $Modified = $false
    
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^\s*userextensions\s*=') {
            Write-Host "Linha encontrada: $($Lines[$i])" -ForegroundColor Yellow
            
            # Detecta formato e adiciona o caminho
            if ($Lines[$i] -match '\[\s*\]') {
                # Lista vazia
                $Lines[$i] = "userextensions = [`"$ExtensionPath`"]"
            }
            elseif ($Lines[$i] -match '\[') {
                # Já tem itens, adiciona no início
                $Lines[$i] = $Lines[$i] -replace '\[', "[`"$ExtensionPath`", "
                $Lines[$i] = $Lines[$i] -replace '\[, ', '['
            }
            else {
                # Formato desconhecido, cria novo
                $Lines[$i] = "userextensions = [`"$ExtensionPath`"]"
            }
            
            Write-Host "Nova linha: $($Lines[$i])" -ForegroundColor Green
            $Modified = $true
            break
        }
    }
    
    if (-not $Modified) {
        Write-Host "Linha 'userextensions' não encontrada. Adicionando..." -ForegroundColor Yellow
        $Lines += "userextensions = [`"$ExtensionPath`"]"
    }
    
    # Salva com UTF-8 (sem BOM para compatibilidade)
    $Lines | Out-File -FilePath $ConfigPath -Encoding UTF8 -Force
    
    Write-Host "Extensão registrada com sucesso!" -ForegroundColor Green
    exit 0
}
catch {
    Write-Host "Erro ao processar config: $_" -ForegroundColor Red
    
    # Restaura backup em caso de erro
    if (Test-Path $BackupPath) {
        Copy-Item $BackupPath $ConfigPath -Force
        Write-Host "Backup restaurado devido ao erro." -ForegroundColor Yellow
    }
    
    exit 1
}

