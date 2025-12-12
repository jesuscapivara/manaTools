# ⚠️ Windows Bloqueou o Instalador?

É normal o Windows SmartScreen bloquear instaladores novos. Isso acontece porque o arquivo ainda não tem "reputação" no sistema da Microsoft.

## ✅ **O ManaTools é Seguro?**

Sim! O bloqueio acontece porque:

- O instalador não tem assinatura digital (certificados custam caro)
- É um arquivo novo (Windows precisa de tempo para reconhecer)
- Poucos usuários baixaram ainda (sem "reputação")

**Não é vírus, é apenas um arquivo não reconhecido.**

---

## 🔓 **Como Desbloquear e Instalar**

### **Método 1: Desbloquear o Arquivo**

1. Clique com botão direito no `ManaToolsSetup_1.0.1.exe`
2. Selecione **Propriedades**
3. Na aba **Geral**, marque ☑️ **Desbloquear**
4. Clique em **OK**
5. Execute o instalador normalmente

### **Método 2: Ignorar o Aviso do SmartScreen**

Ao tentar executar o instalador:

1. Windows mostra: "O Windows protegeu seu computador"
2. Clique em **Mais informações**
3. Clique em **Executar assim mesmo**
4. O instalador abrirá normalmente

### **Método 3: Desabilitar Temporariamente o SmartScreen** (não recomendado)

Se os métodos acima não funcionarem:

1. Windows Security → App & browser control
2. Reputation-based protection settings
3. Desabilite "Check apps and files"
4. Execute o instalador
5. **RE-HABILITE a proteção** após instalar

---

## 🔍 **Verificar a Integridade do Arquivo**

Para garantir que o arquivo não foi adulterado durante o download:

```cmd
certutil -hashfile ManaToolsSetup_1.0.1.exe SHA256
```

Compare o resultado com o hash oficial publicado no site.

**Hash oficial:**

```
(O hash será exibido aqui após você gerar com gerar_hash_instalador.bat)
```

---

## 🛡️ **Por Que Não Tem Assinatura Digital?**

Certificados de assinatura de código custam entre $100-400/ano e exigem validação empresarial complexa.

Enquanto o ManaTools não tiver volume suficiente de usuários para justificar esse investimento, o instalador permanecerá sem assinatura.

**Alternativa:** Se você tem um certificado de assinatura de código, pode assinar o instalador você mesmo após baixar.

---

## 📞 **Ainda com Dúvidas?**

- **Site**: https://www.manatools.com.br
- **Email**: suporte@manatools.com.br
- **WhatsApp**: (coloque o contato aqui)

---

**🚀 Após instalar, o ManaTools aparecerá automaticamente na aba do Revit!**
