# ManaTools - Extensão PyRevit

Suite de ferramentas de alta performance para a Maná Engenharia.

## Estrutura do Projeto

```
ManaTools.extension/
├── extension.json          # Configuração da extensão
├── hooks/                  # Event Listeners (OnStartup, OnSync, etc.)
│   └── doc-opened.py
├── lib/                    # Backend - Lógica pura, sem UI
│   └── manalib/
│       ├── __init__.py
│       ├── utils.py        # Utilitários gerais (get_all_walls, setup_transaction, etc.)
│       ├── bim_manager.py  # Gerenciador de operações BIM
│       └── sicro_integration.py
└── ManaTools.tab/          # Frontend/UI (A aba no Revit)
    ├── config.yaml
    ├── Gestão.panel/
    │   ├── Renamer.pushbutton/
    │   └── Auditoria.stack/
    └── Engenharia.panel/
```

## Instalação (Deploy Local)

### Pré-requisitos

1. PyRevit instalado e configurado
2. Terminal (CMD/Powershell) com permissões de Administrador

### Passo a Passo

1. Abra o terminal como Administrador
2. Execute o comando:

```bash
pyrevit extend ui ManaTools "C:\Caminho\Para\Seu\Repo\ManaTools.extension"
```

**Exemplo:**
```bash
pyrevit extend ui ManaTools "C:\Users\Mana02\manaTools\manaTools\ManaTools.extension"
```

Isso criará um link simbólico, não é necessário copiar pastas.

## Configuração do Ambiente de Desenvolvimento

### 1. Instalar Stubs da Revit API

Para ter Intellisense/Autosuggest no Cursor/VS Code:

- Clone o repositório: `gtwc/ironpython-stubs` ou pesquise por "Revit API Stubs"
- Atualize o caminho no arquivo `.vscode/settings.json`

### 2. Configurar Caminhos no settings.json

O arquivo `.vscode/settings.json` já está configurado, mas você precisa atualizar os caminhos:

```json
{
    "python.autoComplete.extraPaths": [
        "C:\\Caminho\\Para\\pyRevit-Master\\pyrevitlib",
        "C:\\Caminho\\Para\\RevitAPIStubs"
    ],
    "python.analysis.extraPaths": [
        "./ManaTools.extension/lib"
    ]
}
```

## Desenvolvimento

### Reload Rápido

No Revit, segure **ALT** e clique no botão "pyRevit" na aba Sys para dar reload sem fechar o software. Vital para desenvolvimento!

### Arquitetura

- **lib/manalib/**: Lógica de negócio pura, sem UI
- **script.py**: Apenas Controller - pega input, chama lib, mostra output
- **hooks/**: Event listeners automáticos

### Exemplo de Uso

O botão `Renamer` demonstra o padrão:
1. UI - Seleção de elementos
2. Lógica de Negócio (chamando a lib)
3. Feedback visual

## Próximos Comandos Sugeridos

1. **Auditor de Padrões**: Verificar se as famílias carregadas seguem a nomenclatura da Maná
2. **Exportador Batch**: Gerar PDFs/DWGs com nomes sanitizados automaticamente
3. **Sync View**: Sincronizar a View Template de todas as plantas baixas de uma vez

## Engine

O pyRevit roda por padrão em **IronPython 2.7** (legado, mas estável para interop com .NET).

Você pode forçar para **CPython 3.8+** se precisar de bibliotecas modernas (pandas, numpy, requests), mas perde um pouco de performance na interop com o Revit.

Recomendação: Comece com IronPython 2.7 pela estabilidade, a menos que precise de requests HTTP pesados.

## Autor

Lucas Rossetti - Maná Engenharia

