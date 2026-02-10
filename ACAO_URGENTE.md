# 🚨 AÇÃO URGENTE - MERCADO INSIGHTS

**Data:** 09/02/2026 23:30

---

## 🎯 DESCOBRI A CAUSA RAIZ!

Analisei o PDF de configuração do seu app no Mercado Livre.

### **O PROBLEMA:**

Seu app está com **2 permissões FALTANDO**:

1. ❌ "**Publicação e sincronização**" → SEM ACESSO
2. ❌ Tópico "**Questions**" → NÃO ATIVADO

### **POR ISSO:**

- ❌ "Adicionar concorrente" retorna: **"Acesso negado ao anúncio MLB..."**
- ❌ Webhook de perguntas **não recebe** notificações do ML

---

## ✅ SOLUÇÃO (5 MINUTOS)

### 1. Acesse Portal ML

https://developers.mercadolivre.com.br/apps/home

### 2. Edite Seu App

Clique no app **ID: 6377184530089001**

### 3. Ative as Permissões

**Seção "Permissões":**
- Procure: "**Publicação e sincronização**"
- Status atual: "Sem acesso" ❌
- **Mude para: "Leitura"** ✅

**Seção "Tópicos":**
- Marque: "**Questions**" ✅

### 4. Salvar

Clique em "Salvar" no final da página.

### 5. Reconectar Conta ML

1. Acesse: https://www.mercadoinsights.online
2. Dashboard → "Conectar Mercado Livre"
3. Autorize novamente (para atualizar permissões do token)

---

## 🧪 TESTAR (COM NOVA PÁGINA DE CONFIG)

### 🆕 Teste 0: Usar Página de Configurações ML

1. Acesse: **Config. Mercado Livre** (novo link no menu)
2. Clique em **"Executar Diagnóstico"**
3. Veja quais testes falharam
4. Siga as recomendações

**Vantagem:** Diagnóstico preciso em 10 segundos!

### Teste 1: Adicionar Concorrente

1. Vá em **Concorrentes**
2. Cole um ID de produto do ML (ex: MLB4443868923)
3. Clique "Adicionar"

**Esperado DEPOIS de corrigir permissões:**
- ✅ "Concorrente adicionado" (se ID válido)
- OU "Anúncio não encontrado" (se ID inválido)
- **NÃO DEVE** mostrar "Acesso negado"

**Se ainda mostra "Acesso negado":**
→ Vá em **Config. ML** → Desconectar → Conectar → Diagnosticar

### Teste 2: Webhook de Perguntas

1. Faça uma pergunta em um anúncio seu (outra conta)
2. Aguarde 30s
3. Vá em **Perguntas nos anúncios**

**Esperado:**
- ✅ Pergunta aparece automaticamente
- ✅ Com resposta sugerida pela IA

---

## 📊 DEPOIS DE CORRIGIR

### TUDO funcionará:
- ✅ Adicionar concorrente por link/ID
- ✅ Listar concorrentes com preços atualizados
- ✅ Webhook de perguntas
- ✅ Busca de concorrentes (se app for certificado - opcional)

### Próximas melhorias (opcional):
- Polling de perguntas a cada 30min (ver `IMPLEMENTACAO_POLLING_PERGUNTAS.md`)
- Multiget para performance (ver `MELHORIAS_FUTURAS.md`)
- Cache para reduzir custos (ver `ESTRATEGIA_CONCORRENCIA.md`)

---

## 🎯 FAÇA AGORA

### 1. Fazer Deploy (PRIMEIRO)

```bash
git add .
git commit -m "Add: ML config page with disconnect, diagnostic and testing + fix error handling"
git push origin main
```

**Aguarde deploy (2-3min)**

### 2. Corrigir Permissões no Portal ML

1. https://developers.mercadolivre.com.br/apps/home
2. App 6377184530089001 → Editar
3. "Publicação e sincronização" → "Leitura" ✅
4. Tópico "Questions" → Marcar ✅
5. Salvar

### 3. Usar Nova Página de Config

1. Acesse: **Config. Mercado Livre** (novo link no menu)
2. Clique em **"Desconectar"**
3. Clique em **"Conectar Mercado Livre"**
4. Autorize no ML
5. Clique em **"Executar Diagnóstico"**

**Resultado esperado:**
```
✅ Todos os 4 testes passam
✅ "Tudo OK! Conexão e permissões corretas."
```

### 4. Testar Adicionar Concorrente

1. **Config. ML** → "Testar API" → Cole ID → Testar
2. Se ✅ OK → Vá em Concorrentes e adicione
3. Se ❌ Falha → Veja recomendação no diagnóstico

---

## 🎉 NOVA FUNCIONALIDADE

### ⚙️ Página de Configurações ML (criada agora!)

**O que tem:**
- ✅ Status da conexão (tempo real)
- ✅ Botão desconectar/conectar
- ✅ Diagnóstico automático (4 testes de API)
- ✅ Teste de produto específico
- ✅ Logs de debug visual

**Como usar:**
- Menu lateral → **"⚙️ Config. Mercado Livre"**

📖 **Detalhes:** `NOVA_PAGINA_CONFIG_ML.md`

---

**🎉 Após isso, seu sistema estará 100% funcional!** 🚀
