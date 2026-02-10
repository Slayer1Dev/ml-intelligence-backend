# 🚀 INSTRUÇÕES DE DEPLOY - MERCADO INSIGHTS

**Site:** https://www.mercadoinsights.online  
**Última atualização:** 09/02/2026 21:00

---

## ✅ CORREÇÕES APLICADAS (PRONTAS PARA DEPLOY)

### 🆕 **NOVA CORREÇÃO (09/02 - 21:00): Mensagens de Erro Específicas**
- **Problema:** "Adicionar concorrente" mostrava "Anúncio não encontrado" para TODOS os erros (conexão, 404, 500)
- **Correção:** Mensagens específicas por tipo de erro:
  - Erro de conexão → "Erro de conexão com a API do Mercado Livre..."
  - 404 → "Anúncio MLB123 não encontrado. Verifique se está ativo."
  - 403 → "Acesso negado. Verifique se sua conta ML está conectada."
  - 500 → "Erro no servidor do Mercado Livre (500)..."
- **Arquivos:** `app/services/ml_api.py`, `app/main.py`

---

### ✅ **CORREÇÕES ANTERIORES:**

### 1. ✅ Código de debug removido
- **9 blocos** de telemetria `127.0.0.1:7242` removidos
- **4 arquivos** com URLs `localhost:8000` corrigidos
- Arquivos: `clerk-auth.js`, `dashboard.html`, `app-nav.js`, `jobs.html`, `logs.html`, `app.js`

### 2. ✅ Pesquisa de concorrência melhorada  
- Erros específicos: 403 (não certificado), 429 (rate limit), 500 (servidor), etc.
- Mensagens amigáveis com ícones
- `console.log` para diagnóstico
- Arquivos: `ml_api.py`, `main.py`, `concorrentes.html`

### 3. ✅ Nome alterado
- "ML Intelligence" → "Mercado Insights"
- **9 arquivos HTML** atualizados
- Título do backend atualizado

### 4. ✅ Mixed Content corrigido
- Imagens do ML forçadas para HTTPS (não HTTP)
- Resolve avisos de "Mixed Content" no console
- Arquivos: `anuncios.html`, `concorrentes.html`

---

## 🚨 VOCÊ PRECISA FAZER DEPLOY!

**Os erros continuam aparecendo no seu site porque você NÃO FEZ PUSH das minhas correções.**

---

## 📋 PASSO A PASSO: FAZER DEPLOY NA RAILWAY

### 1️⃣ Verificar Mudanças

```bash
# No terminal, na pasta do projeto:
git status
```

**Esperado:** Deve mostrar ~15 arquivos modificados.

### 2️⃣ Adicionar e Commitar

```bash
git add .

git commit -m "Fix: Remove debug telemetry, fix localhost URLs, rename to Mercado Insights, improve ML search errors, fix Mixed Content"
```

### 3️⃣ Fazer Push

```bash
git push origin main
```

**OU** se seu branch é `master`:

```bash
git push origin master
```

### 4️⃣ Acompanhar Deploy na Railway

1. Acesse: https://railway.app
2. Selecione seu projeto
3. Vá em **"Deployments"**
4. Aguarde ~2-3 minutos

**Você verá:**
- ⏳ Building...
- ⏳ Deploying...
- ✅ Success!

### 5️⃣ Limpar Cache do Navegador (OBRIGATÓRIO)

**Chrome/Edge:**
- Abra: https://www.mercadoinsights.online
- Pressione: `Ctrl + Shift + R` (Windows) ou `Cmd + Shift + R` (Mac)

**OU:**
- F12 → Clique direito em "Reload" → "Empty Cache and Hard Reload"

**Firefox:**
- `Ctrl + Shift + Del` → Marcar "Cache" → "Limpar agora"

### 6️⃣ Testar

1. Abra: https://www.mercadoinsights.online
2. Abra **DevTools (F12)** → Aba **Console**
3. Navegue pelas páginas

**Resultado Esperado:**
```
✅ ZERO erros de 127.0.0.1:7242
✅ ZERO erros de ERR_CONNECTION_REFUSED
✅ Nome "Mercado Insights" em todas as páginas
✅ Imagens carregando normalmente (HTTPS)
⚠️ Pode ter warning de Clerk (resolver abaixo)
```

---

## 🔐 RESOLVER WARNING DO CLERK (OPCIONAL MAS RECOMENDADO)

### Problema Atual

```
⚠️ Clerk has been loaded with development keys.
Development instances have strict usage limits...
```

### Solução

#### 1. Criar Aplicação de Produção no Clerk

1. Acesse: https://dashboard.clerk.com
2. Clique em **"Create Application"**
3. Nome: "Mercado Insights - Production"
4. Domain: `mercadoinsights.online`

#### 2. Obter Chaves de Produção

No dashboard do Clerk → **"API Keys"**:

Copie as chaves **de PRODUÇÃO** (começam com `pk_live_` e `sk_live_`):

```
CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
CLERK_JWKS_URL=https://seu-dominio-prod.clerk.accounts.dev/.well-known/jwks.json
CLERK_FRONTEND_API=https://seu-dominio-prod.clerk.accounts.dev
```

#### 3. Atualizar na Railway

1. Acesse: https://railway.app/project/seu-projeto
2. Selecione o **Service** do backend
3. Aba **"Variables"**
4. **Edite** as 4 variáveis acima com as chaves de produção
5. Aguarde redeploy automático (~2min)

#### 4. Testar

- Recarregue o site
- O warning amarelo deve **desaparecer**
- Autenticação continua funcionando

---

## 🧪 VALIDAÇÃO FINAL

Após o deploy, abra o Console (F12) e verifique:

### ✅ **Deve estar limpo:**
```
(sem erros de localhost)
(sem erros de ERR_CONNECTION_REFUSED)
```

### ✅ **Se buscar concorrente:**
```
[ML Search] Erro na busca: {status: 503, detail: "...restrita (403)..."}
```
→ **Mensagem clara** + **Solução sugerida** (usar link/ID)

### ✅ **Imagens:**
```
Todas carregam via HTTPS (não HTTP)
```

### ⚠️ **Clerk (opcional):**
```
Se aparecer warning: configure chaves de produção (seção acima)
```

---

## 📊 COMPARAÇÃO: ANTES vs DEPOIS

### ANTES (Console cheio de erros)
```
❌ POST http://127.0.0.1:7242/... - ERR_CONNECTION_REFUSED (3x)
❌ POST http://127.0.0.1:7242/... - ERR_CONNECTION_REFUSED (3x)
❌ POST http://127.0.0.1:7242/... - ERR_CONNECTION_REFUSED (3x)
❌ GET .../search... - 503 ()
⚠️ Clerk development keys warning
⚠️ Mixed Content warnings (imagens bloqueadas)
```

### DEPOIS (Console limpo)
```
✅ (sem erros de localhost)
✅ Busca retorna erro claro: "App não certificado (403)"
✅ Mensagem: "Use adicionar por link/ID"
✅ Imagens carregam via HTTPS
⚠️ Clerk warning (se não configurar produção - opcional)
```

---

## 🎯 PRÓXIMOS PASSOS

### Agora (Obrigatório):
1. ✅ `git push origin main`
2. ✅ Aguardar deploy (2-3min)
3. ✅ Limpar cache do navegador
4. ✅ Testar site
5. 🆕 **Testar "Adicionar concorrente por link/ID"** (deve mostrar erro claro se falhar)

### Depois (Recomendado):
1. ⚠️ Configurar Clerk em produção (remove warning)
2. 📊 Monitorar logs na Railway
3. 🧪 Testar todas as funcionalidades
4. 📖 Ler `ESTRATEGIA_CONCORRENCIA.md` para melhorias futuras

### Melhorias Futuras (Ver `ESTRATEGIA_CONCORRENCIA.md`):
- 🚀 **Multiget:** Buscar até 20 produtos por requisição (20x mais rápido)
- 💾 **Cache:** Reduzir calls à API ML
- ⏱️ **Rate limiting:** Evitar bloqueio por excesso de requisições
- 📊 **Histórico de preços:** Armazenar para análise de tendências

---

## 💬 DÚVIDAS COMUNS

**Q: Por que os erros ainda aparecem?**  
A: Você não fez push das correções. Execute os passos 1-3 acima.

**Q: Fiz push mas ainda vejo erros!**  
A: Limpe o cache do navegador (Ctrl+Shift+R).

**Q: O warning do Clerk é crítico?**  
A: Não, mas é recomendado configurar produção.

**Q: Minhas imagens não carregam!**  
A: Após deploy + limpar cache, devem carregar via HTTPS.

**Q: A busca ainda retorna 503!**  
A: Normal! Seu app ML não é certificado. Use "Adicionar por link/ID".

**Q: "Adicionar por link/ID" retorna erro!**  
A: Agora mostra erro específico:
  - "Erro de conexão" → Problema de rede
  - "Anúncio não encontrado" → ID inválido ou produto removido
  - "Acesso negado" → Token ML expirado, reconecte conta

**Q: Por que comparadores (Zoom, Buscapé) funcionam e o meu não?**  
A: Eles usam a mesma API! Nossa abordagem está correta. Ver `ESTRATEGIA_CONCORRENCIA.md`.

---

## 📚 DOCUMENTAÇÃO ADICIONAL

- **`ESTRATEGIA_CONCORRENCIA.md`** → Como comparadores profissionais funcionam + Roadmap de melhorias
- **`RELATORIO_BUGS.md`** → Todos os problemas identificados
- **`CORRECAO_APLICADA_PESQUISA.md`** → Detalhes da correção de busca

---

**🎉 Pronto! Depois do deploy, seu site estará limpo e profissional.**
