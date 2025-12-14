# 📥 Guia de Instalação - ManaTools

Siga este guia passo a passo para instalar o ManaTools no seu Revit.

---

## 📋 Requisitos do Sistema

Antes de iniciar, verifique se seu computador atende aos requisitos:

| Requisito                | Mínimo                              |
| ------------------------ | ----------------------------------- |
| **Sistema Operacional**  | Windows 10 ou 11 (64-bit)           |
| **Autodesk Revit**       | 2023, 2024, 2025 ou 2026            |
| **.NET Framework**       | 4.8 ou superior                     |
| **Conexão com Internet** | Necessária para ativação da licença |

---

## 🔧 Etapa 1: Instalar o pyRevit

O ManaTools é uma extensão do **pyRevit**, portanto é necessário instalá-lo primeiro.

### 1.1. Baixar o pyRevit

1. Acesse o site oficial: [github.com/pyrevitlabs/pyRevit/releases](https://github.com/pyrevitlabs/pyRevit/releases)
2. Na seção **Assets** da versão mais recente, clique em **`pyRevit_CLI_xxx_admin_signed.exe`**

   > ⚠️ **Importante:** Baixe a versão **"admin_signed"** para evitar bloqueios do Windows.

### 1.2. Executar o Instalador do pyRevit

1. **Feche o Revit** completamente (verifique se não há processos em segundo plano)
2. Clique com o botão direito no arquivo baixado e selecione **"Executar como administrador"**
3. Se aparecer um aviso do Windows Defender SmartScreen:
   - Clique em **"Mais informações"**
   - Clique em **"Executar assim mesmo"**
4. Siga as instruções do instalador:
   - Aceite os termos de uso
   - Mantenha o caminho de instalação padrão
   - Aguarde a conclusão

### 1.3. Verificar a Instalação do pyRevit

1. Abra o **Revit**
2. Procure pela aba **"pyRevit"** na faixa de opções (Ribbon)
3. Se a aba aparecer, o pyRevit foi instalado com sucesso ✅

> 💡 **Dica:** Se a aba não aparecer, reinicie o computador e abra o Revit novamente.

---

## 🚀 Etapa 2: Instalar o ManaTools

Agora que o pyRevit está instalado, vamos instalar o ManaTools.

### 2.1. Baixar o ManaTools

1. Acesse nosso site: [manatools.com.br](https://www.manatools.com.br)
2. Clique no botão **"Baixar ManaTools"**
3. O download do arquivo `ManaToolsSetup_x.x.x.exe` será iniciado

### 2.2. Executar o Instalador do ManaTools

1. **Feche o Revit** completamente
2. Localize o arquivo baixado (geralmente na pasta Downloads)
3. Clique com o botão direito no arquivo e selecione **"Executar como administrador"**
4. Se aparecer um aviso do Windows Defender SmartScreen:

   - Clique em **"Mais informações"**
   - Clique em **"Executar assim mesmo"**

   > ℹ️ Esse aviso aparece porque o instalador ainda não possui certificado digital de uma autoridade certificadora. O software é seguro.

5. Siga as instruções do instalador:
   - Selecione o idioma (Português)
   - Aceite os termos de uso
   - Clique em **"Instalar"**
   - Aguarde a conclusão
   - Clique em **"Concluir"**

### 2.3. Verificar a Instalação do ManaTools

1. Abra o **Revit**
2. Procure pela aba **"ManaTools"** na faixa de opções (Ribbon)
3. Se a aba aparecer, a instalação foi concluída com sucesso ✅

---

## 🔑 Etapa 3: Ativar sua Licença

O ManaTools requer ativação para funcionar.

### 3.1. Fazer Login

1. Na aba **ManaTools**, clique no botão **"Login"** (painel Gestão)
2. Insira seu **e-mail** e **senha** cadastrados
3. Clique em **"Entrar"**

### 3.2. Confirmação

Se suas credenciais estiverem corretas e sua licença ativa, você verá uma mensagem de sucesso.

> 🆕 **Primeira vez?** Entre em contato conosco para criar sua conta e ativar sua licença de teste.

---

## ❓ Solução de Problemas

### A aba pyRevit não aparece no Revit

1. Verifique se o Revit estava fechado durante a instalação
2. Reinicie o computador
3. Abra o Revit novamente
4. Se persistir, reinstale o pyRevit como administrador

### A aba ManaTools não aparece no Revit

1. Verifique se o pyRevit está instalado e funcionando (aba pyRevit visível)
2. Feche o Revit
3. Reinstale o ManaTools como administrador
4. Abra o Revit novamente

### O instalador é bloqueado pelo Windows

1. Clique em **"Mais informações"** no aviso do SmartScreen
2. Clique em **"Executar assim mesmo"**

Se o antivírus bloquear:

1. Adicione uma exceção temporária para o arquivo do instalador
2. Execute o instalador
3. Remova a exceção após a instalação

### Erro de licença ou login

1. Verifique sua conexão com a internet
2. Confirme se o e-mail e senha estão corretos
3. Entre em contato com o suporte se o problema persistir

---

## 🔄 Como Atualizar o ManaTools

Quando uma nova versão estiver disponível:

1. Na aba **ManaTools**, clique em **"Checar Update"** (painel Dev)
2. Se houver atualização, clique em **"Baixar Atualização"**
3. Feche o Revit
4. Execute o novo instalador
5. Siga os passos da Etapa 2

---

## 📞 Suporte

Precisa de ajuda? Entre em contato:

- 🌐 **Site:** [manatools.com.br](https://www.manatools.com.br)
- 📧 **E-mail:** suporte@manatools.com.br

---

© 2025 ManaTools - Todos os direitos reservados.
