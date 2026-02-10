# 🚨 PROBLEMA DE CONFIGURAÇÃO - APP MERCADO LIVRE

**Data:** 09/02/2026  
**App ID:** 6377184530089001  
**Status:** ❌ Configuração INCORRETA - faltam permissões

---

## 🔍 ANÁLISE DA CONFIGURAÇÃO ATUAL

### ✅ O que está CORRETO:
- **URI de Redirect:** `https://www.mercadoinsights.online/frontend/callback-ml.html` ✅
- **Webhook URL:** `https://www.mercadoinsights.online/api/ml-webhook` ✅
- **Permissão "Usuários":** Leitura e escrita ✅
- **Permissão "Comunicações":** Leitura e escrita ✅
- **Permissão "Métricas":** Leitura ✅

### ❌ O que está INCORRETO:

#### 1. **SCOPE "Items" NÃO ESTÁ VISÍVEL/HABILITADO** 🔴 CRÍTICO
**Problema:** Sem este scope, você NÃO pode:
- ❌ Buscar produtos por ID (`/items/{ID}`)
- ❌ Adicionar concorrentes por link/ID
- ❌ Listar anúncios do usuário

**Sintoma nos prints:**
```
❌ "Acesso negado ao anúncio MLB4443868923. 
    Verifique se sua conta ML está conectada corretamente."
```

**Onde ativar:**
- No portal ML → Seu app → Seção "Permissões"
- Procure "**Publicação e sincronização**" (engloba Items)
- Status atual: "**Sem acesso**" ❌
- **Mude para: "Leitura"** ou "**Leitura e escrita**"

#### 2. **TÓPICO "Questions" NÃO ESTÁ ATIVADO** 🔴 CRÍTICO
**Problema:** Sem este tópico, o ML NÃO envia webhooks de perguntas.

**Sintoma:**
- Webhook configurado (`https://mercadoinsights.online/api/ml-webhook`) ✅
- Mas ML não envia notificações de perguntas ❌
- Polling manual funciona (botão "Buscar perguntas agora") ✅

**Onde ativar:**
- No portal ML → Seu app → Seção "**Tópicos**"
- Marque: "**Questions**" ✅

---

## 🔧 SOLUÇÃO: CORRIGIR CONFIGURAÇÃO DO APP ML

### Passo 1: Acessar Portal de Desenvolvedores

1. Acesse: https://developers.mercadolivre.com.br/apps/home
2. Clique no seu app (ID: 6377184530089001)
3. Vá em "**Editar aplicação**"

### Passo 2: Ativar Permissão "Items"

**Seção: Permissões**

Procure por: **"Publicação e sincronização"**

Descrição:
> Criar, atualizar, pausar e/ou excluir um ou todos os anúncios da loja.

**Status atual:** "Sem acesso" ❌  
**Mude para:** "**Leitura**" ✅

**Por que Leitura é suficiente:**
- Não vamos criar/editar anúncios
- Apenas ler dados de produtos (preço, título, vendidos)
- "Leitura e escrita" também funciona, mas não é necessário

### Passo 3: Ativar Tópico "Questions"

**Seção: Tópicos (Webhooks)**

Marque: **"Questions"** ✅

**Por que:**
- Permite receber webhooks quando comprador faz pergunta
- Sem isso, ML não envia notificações
- Polling manual continua funcionando, mas webhooks são mais eficientes

### Passo 4: Salvar e Testar

1. Clique em "**Salvar**" (no final da página)
2. Aguarde ~1 minuto para ML processar
3. **IMPORTANTE:** Reconecte sua conta ML no Mercado Insights:
   - Dashboard → "Conectar Mercado Livre"
   - Autorize novamente (para atualizar permissões)

---

## 🧪 VALIDAR SE FUNCIONOU

### Teste 1: Adicionar Concorrente por ID

1. Acesse: https://www.mercadoinsights.online/frontend/concorrentes.html
2. Campo "Adicionar concorrente por link ou ID"
3. Cole um ID válido (ex: pesquise "smartwatch" no ML e copie ID)
4. Clique "Adicionar"

**Esperado ANTES da correção:**
```
❌ "Acesso negado ao anúncio MLB123..."
```

**Esperado DEPOIS da correção:**
```
✅ "Concorrente adicionado." 
OU
❌ "Anúncio MLB123 não encontrado..." (se ID inválido)
```

### Teste 2: Webhook de Perguntas

1. Faça uma pergunta em um dos seus anúncios do ML (use outra conta ou peça a alguém)
2. Aguarde ~30 segundos
3. Acesse: https://www.mercadoinsights.online/frontend/perguntas-anuncios.html

**Esperado:**
```
✅ Pergunta aparece em "Aguardando sua aprovação"
✅ Com resposta sugerida pela IA
```

Se não aparecer:
- Use o botão "**Buscar perguntas agora**" (polling manual)
- Deve aparecer normalmente

---

## 📊 COMPARAÇÃO: ANTES vs DEPOIS

### ANTES (Configuração Incompleta)

```
Permissões:
  ❌ Publicação e sincronização: Sem acesso
  ✅ Usuários: Leitura e escrita
  ✅ Comunicações: Leitura e escrita

Tópicos (Webhooks):
  ❌ Questions: NÃO ativado
  ✅ Messages: Created, Read

Resultado:
  ❌ Adicionar concorrente: "Acesso negado"
  ❌ Webhook de perguntas: Não recebe
  ✅ OAuth: Funciona
  ✅ Polling de perguntas: Funciona
```

### DEPOIS (Configuração Correta)

```
Permissões:
  ✅ Publicação e sincronização: Leitura
  ✅ Usuários: Leitura e escrita
  ✅ Comunicações: Leitura e escrita

Tópicos (Webhooks):
  ✅ Questions: Ativado
  ✅ Messages: Created, Read

Resultado:
  ✅ Adicionar concorrente: Funciona
  ✅ Webhook de perguntas: Recebe automaticamente
  ✅ OAuth: Funciona
  ✅ Polling de perguntas: Funciona
```

---

## 🎯 RESUMO DO PROBLEMA

### Por que "Adicionar concorrente" estava falhando?

**Causa:** Permissão "Items" (dentro de "Publicação e sincronização") não estava habilitada.

**Efeito:** API ML retorna **403 Forbidden** ao tentar `GET /items/{ID}`.

**Solução:** Ativar "Publicação e sincronização" com "Leitura".

### Por que webhook de perguntas não funcionava?

**Causa:** Tópico "Questions" não estava ativado.

**Efeito:** ML não envia notificações ao webhook (mesmo com URL configurada).

**Solução:** Marcar "Questions" na seção de Tópicos.

---

## 🔄 APÓS CORRIGIR

### IMPORTANTE: Reconectar Conta ML

Depois de salvar as mudanças no portal ML:

1. Acesse: https://www.mercadoinsights.online
2. Dashboard → "**Desconectar Mercado Livre**" (se tiver opção)
3. Dashboard → "**Conectar Mercado Livre**"
4. Autorize novamente

**Por quê?**
- OAuth anterior foi com permissões antigas
- Reconectar atualiza o token com novas permissões
- Sem reconectar, o erro persiste

---

## 📚 REFERÊNCIA

### Scopes Necessários (Mínimo)

Para o Mercado Insights funcionar completamente:

| Permissão | Nível | O que permite |
|-----------|-------|--------------|
| **Usuários** | Leitura e escrita | OAuth, dados da conta |
| **Publicação e sincronização** | **Leitura** | Buscar produtos (`/items/{ID}`) |
| **Comunicações** | Leitura e escrita | Perguntas (ler/responder) |
| **Métricas** | Leitura | Vendas, desempenho |

### Tópicos de Webhook (Recomendados)

| Tópico | O que notifica |
|--------|---------------|
| **Questions** | Nova pergunta em anúncio |
| Messages | Novas mensagens pré/pós-venda |
| Orders | Novas vendas |
| Items | Mudanças em anúncios |

---

## ✅ CHECKLIST

Após configurar no portal ML:

- [ ] "Publicação e sincronização" → "Leitura" ✅
- [ ] Tópico "Questions" → Marcado ✅
- [ ] Salvar configurações
- [ ] Reconectar conta ML no Mercado Insights
- [ ] Testar adicionar concorrente
- [ ] Fazer pergunta de teste (validar webhook)

---

**🎯 ESTA É A CAUSA RAIZ DO PROBLEMA!**

Corrija isso no portal do ML e **tudo funcionará**. 🚀
