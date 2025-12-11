# ManaTools

Extensão pyRevit para fluxos BIM ágeis focada em produtividade e automação de tarefas no Autodesk Revit.

## 🚀 Funcionalidades

### Gestão

- **Login**: Autenticação de usuários com sistema de licenças
- **Exportar PDFs**: Exportação em lote de pranchas com nomenclatura personalizada

### Modelagem

- **Criar Forro**: Geração automática de forros em ambientes
- **Criar Piso**: Criação automatizada de pisos
- **Criar Revestimento**: Aplicação de revestimentos em paredes
- **Criar Rodapé**: Geração de rodapés em ambientes
- **Criar Soleira**: Criação de soleiras em portas
- **Criar Pingadeira**: Geração inteligente de pingadeiras em janelas (com detecção de face externa)

### Esquadrias

- **Smart Renamer**: Renomeação inteligente de portas e janelas
- **Type Mark**: Atualização automática de marcas de tipo

### Modificações

- **Unir Elementos**: União automática de elementos sobrepostos

### Dev (Ferramentas de Desenvolvimento)

- **Inspector**: Visualização detalhada de parâmetros de elementos
- **Sobre**: Informações da versão instalada
- **Checar Update**: Verificação manual de atualizações disponíveis

## 📋 Requisitos

- **Revit**: 2025 ou superior (compatível com 2026)
- **pyRevit**: 5.0 ou superior ([Download](https://github.com/pyrevitlabs/pyRevit/releases))
- **Windows**: 10/11 (64-bit)
- **.NET Framework**: 4.8 ou superior

## 💿 Instalação

### Método 1: Instalador EXE (Recomendado)

1. Baixe `ManaToolsSetup.exe` do site oficial
2. Execute o instalador (requer privilégios de administrador)
3. Reinicie o Revit
4. A aba ManaTools aparecerá automaticamente

### Método 2: Manual

1. Baixe/clone este repositório
2. Copie a pasta `ManaTools.extension` para:
   - `C:\ProgramData\pyRevit\Extensions\` (recomendado), ou
   - Qualquer pasta → pyRevit Settings → Custom Extension Directories → Add
3. Reload pyRevit (pyRevit → Settings → Reload)
4. Reinicie o Revit

## 🔧 Configuração

### Licenciamento

1. Clique em **Login** no painel Gestão
2. Insira suas credenciais
3. O sistema valida automaticamente sua licença

### Atualização

- Clique em **Checar Update** (painel Dev) para verificar novas versões
- Se disponível, clique em "Baixar Atualização"
- Execute o novo instalador

## 🏗️ Desenvolvimento

### Estrutura do Projeto

```
ManaTools/
├── ManaTools.extension/
│   ├── ManaTools.tab/              # Ribbon principal
│   │   ├── 01-Gestao.panel/
│   │   ├── 02-Modelagem.panel/
│   │   ├── 03-Esquadrias.panel/
│   │   ├── 04-Modificacoes.panel/
│   │   └── 05-Dev.panel/
│   ├── lib/
│   │   └── manalib/                # Biblioteca compartilhada
│   │       ├── bim_utils.py        # Utilidades BIM + Auth
│   │       ├── revit_utils.py      # Utilidades Revit API
│   │       └── update_checker.py   # Sistema de updates
│   ├── hooks/
│   │   └── doc-opened.py           # Hook de abertura de documento
│   ├── startup.py                  # Script de inicialização
│   └── extension.json              # Metadados da extensão
├── ManaToolsSetup.iss              # Script Inno Setup
└── COMO_CRIAR_INSTALADOR.md        # Guia de build
```

### Compilar Instalador

Ver guia completo: [COMO_CRIAR_INSTALADOR.md](COMO_CRIAR_INSTALADOR.md)

Resumo:

```cmd
# Instale Inno Setup 6
# Depois:
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ManaToolsSetup.iss
```

Gera: `dist/ManaToolsSetup_1.0.1.exe`

### Atualizar Versão

1. `extension.json`: altere `"version"`
2. `ManaToolsSetup.iss`: altere `#define MyAppVersion`
3. Backend: atualize `latest_version` em `/api/version`

## 🔐 Sistema de Licenças

- **Trial**: 1 dia (automático no registro)
- **Pro**: Licença vitalícia ou por período
- **HWID Lock**: Cada licença vinculada a uma máquina
- Validação online no login e ao abrir documentos

## 🌐 Backend

O sistema requer um backend Node.js/Express para:

- Autenticação de usuários
- Validação de licenças
- Verificação de atualizações

Endpoint de versão pública: `GET /api/version`

## 📦 Distribuição

### Upload do Instalador

1. Compile o `.exe` com Inno Setup
2. Faça upload para servidor/CDN
3. Atualize `download_url` no backend

### Notificação de Updates

- Backend retorna `latest_version` e `download_url`
- Usuário clica em "Checar Update"
- Se nova versão, mostra toast/dialog com botão de download

## 🐛 Debug

- **Console pyRevit**: Shift + Click em qualquer botão do ManaTools
- **Logs**: `startup.py` e `doc-opened.py` geram logs no console
- **Linter**: Use VS Code com extensão Python

## 📄 Licença

© 2025 ManaTools - Lucas Rossetti. Todos os direitos reservados.

## 📞 Suporte

- **Site**: https://www.manatools.com.br
- **Email**: suporte@manatools.com.br
- **Versão**: 1.0.1
