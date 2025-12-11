# Como Criar o Instalador ManaTools

Este guia explica como compilar o instalador `.exe` do ManaTools usando Inno Setup.

## Pré-requisitos

1. **Inno Setup 6** (gratuito)
   - Download: https://jrsoftware.org/isdl.php
   - Instale a versão completa (recomendado: Unicode)

## Passo a Passo

### 1. Instalar Inno Setup

- Baixe e instale o Inno Setup 6
- Durante instalação, marque "Add context menu entries" (opcional)

### 2. Preparar o Projeto

Certifique-se que a estrutura está assim:

```
C:\Users\Mana02\manaTools\manaTools\
├── ManaTools.extension\
│   ├── ManaTools.tab\
│   ├── lib\
│   ├── hooks\
│   └── extension.json
├── ManaToolsSetup.iss  (script do instalador)
└── dist\               (será criada automaticamente)
```

### 3. Compilar o Instalador

**Opção A - Interface Gráfica:**

1. Abra o Inno Setup Compiler
2. File → Open → Selecione `ManaToolsSetup.iss`
3. Build → Compile (ou F9)
4. O instalador será gerado em `.\dist\ManaToolsSetup_1.0.1.exe`

**Opção B - Linha de Comando:**

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ManaToolsSetup.iss
```

### 4. Testar o Instalador

1. Execute `dist\ManaToolsSetup_1.0.1.exe`
2. Siga o assistente de instalação
3. Abra o Revit → Aba ManaTools deve aparecer

## Customizações

### Alterar Versão

Edite no `ManaToolsSetup.iss`:

```iss
#define MyAppVersion "1.0.2"  ; <-- Aqui
```

### Adicionar Ícone

1. Coloque um arquivo `icon.ico` na raiz do projeto
2. Descomente no `.iss`:

```iss
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\icon.ico
```

### Onde a Extensão é Instalada

O instalador copia automaticamente para:

```
C:\ProgramData\pyRevit\Extensions\ManaTools.extension\
```

## Distribuição

### Upload para Site

Suba `ManaToolsSetup_1.0.1.exe` para:

- Seu site: `https://www.manatools.com.br/downloads/`
- Google Drive (público)
- GitHub Releases

### Atualizar Link de Download

No backend (`server/src/controllers/appController.js`), atualize:

```javascript
download_url: "https://www.manatools.com.br/downloads/ManaToolsSetup_1.0.2.exe";
```

## Fluxo de Atualização

1. Altere código → Atualize `extension.json` (versão)
2. Compile novo instalador com Inno Setup
3. Suba o `.exe` para o servidor
4. Atualize backend (`latest_version` e `download_url`)
5. Usuários clicam em "Checar Update" → Baixam e instalam

## Solução de Problemas

### "pyRevit não encontrado"

- O instalador bloqueia se pyRevit não estiver instalado
- Usuário deve instalar pyRevit primeiro: https://github.com/pyrevitlabs/pyRevit/releases

### Extensão não aparece no Revit

1. Verifique se foi instalada em: `C:\ProgramData\pyRevit\Extensions\`
2. Abra pyRevit Settings → Extensions → Reload
3. Reinicie o Revit

### Permissões

- O instalador requer **Admin** (copia para ProgramData)
- Se der erro, execute como Administrador

## Desinstalação

- Painel de Controle → Programas → Desinstalar ManaTools
- Remove completamente a extensão
