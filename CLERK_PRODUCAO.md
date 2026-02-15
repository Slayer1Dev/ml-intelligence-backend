# Clerk — Migração para Produção

**Projeto:** Mercado Insights  
**Domínio:** https://www.mercadoinsights.online  
**Estado atual:** Clerk em modo **Development** (chaves `pk_test_` / `sk_test_`)

> Referência oficial: https://clerk.com/docs/deployments/overview

---

## Por que migrar?

| Development (atual) | Production |
|---------------------|-----------|
| Chaves `pk_test_` / `sk_test_` | Chaves `pk_live_` / `sk_live_` |
| Aceita HTTP | Exige HTTPS |
| OAuth compartilhado (Google, etc.) | OAuth com suas credenciais próprias |
| Login via `xxx.clerk.accounts.dev` | Login no **seu domínio** (`mercadoinsights.online`) |
| Sessão relaxada | Sessão segura |

---

## Passo a passo

### 1. Criar instância de produção no Clerk

1. Acesse https://dashboard.clerk.com
2. No topo, clique no toggle **"Development"**
3. Selecione **"Create production instance"**
4. O Clerk vai clonar as configurações do dev para produção (exceto SSO e integrações)

### 2. Configurar domínio próprio

Na aba **Domains** do Clerk Dashboard (produção):

1. Adicione o domínio: `mercadoinsights.online`
2. O Clerk vai pedir para adicionar **registros DNS** (CNAME/TXT)
3. Se usar **Cloudflare** como DNS (recomendado), adicione os registros no painel Cloudflare
4. Aguardar propagação (pode levar até 48h, geralmente minutos)

**Registros típicos que o Clerk pede:**

| Tipo | Nome | Valor |
|------|------|-------|
| CNAME | `clerk` | `frontend-api.clerk.services` |
| TXT | `_clerk` | (valor fornecido pelo Clerk) |

> O Clerk vai informar os valores exatos na aba Domains.

### 3. Configurar OAuth (Google) com suas credenciais

Em produção, o Clerk **não usa** credenciais compartilhadas. Você precisa criar as suas:

1. Acesse https://console.cloud.google.com/
2. Crie um projeto (ou use existente)
3. Vá em **APIs & Services → Credentials → Create OAuth Client ID**
4. Tipo: **Web Application**
5. Origens autorizadas:
   - `https://www.mercadoinsights.online`
   - `https://clerk.mercadoinsights.online` (se Clerk usar subdomínio)
6. URIs de redirecionamento:
   - `https://clerk.mercadoinsights.online/v1/oauth_callback` (o Clerk informa o valor exato)
7. Copie o **Client ID** e **Client Secret**
8. No Clerk Dashboard (produção) → **SSO Connections → Google** → cole as credenciais

### 4. Atualizar variáveis de ambiente no Railway

No painel do Railway, atualize as variáveis:

| Variável | Valor antigo (dev) | Valor novo (produção) |
|----------|--------------------|-----------------------|
| `CLERK_PUBLISHABLE_KEY` | `pk_test_...` | `pk_live_...` |
| `CLERK_SECRET_KEY` | `sk_test_...` | `sk_live_...` |
| `CLERK_FRONTEND_API` | `https://xxx.clerk.accounts.dev` | `https://clerk.mercadoinsights.online` (ou URL fornecida) |
| `CLERK_JWKS_URL` | `https://xxx.clerk.accounts.dev/.well-known/jwks.json` | `https://clerk.mercadoinsights.online/.well-known/jwks.json` |

> As chaves `pk_live_` e `sk_live_` estão em **API Keys** no Clerk Dashboard (produção).

### 5. Atualizar URLs permitidas no Clerk

No Clerk Dashboard (produção) → **Paths** → **Allowed redirect URLs**:

- `https://www.mercadoinsights.online/frontend/*`
- `https://www.mercadoinsights.online/frontend/dashboard.html`

### 6. Deploy

Após atualizar as variáveis no Railway:

```bash
git add . && git commit -m "feat: Clerk produção" && git push origin main
```

O Railway faz o deploy automaticamente.

### 7. Testar

1. Acesse https://www.mercadoinsights.online
2. O login deve aparecer no seu domínio (não em `clerk.accounts.dev`)
3. Faça login com Google — deve funcionar com suas credenciais OAuth
4. Verifique que o dashboard carrega e `authFetch` funciona

---

## Checklist

- [ ] Instância de produção criada no Clerk Dashboard
- [ ] Domínio `mercadoinsights.online` adicionado e verificado
- [ ] Registros DNS adicionados (CNAME/TXT)
- [ ] OAuth Google com credenciais próprias (Console Cloud)
- [ ] Variáveis de ambiente atualizadas no Railway (`pk_live_`, `sk_live_`, JWKS)
- [ ] URLs permitidas configuradas no Clerk
- [ ] Deploy feito
- [ ] Login testado em produção

---

## Problemas comuns

| Problema | Solução |
|----------|---------|
| **"Clerk não configurado"** | Verifique que `CLERK_PUBLISHABLE_KEY` e `CLERK_FRONTEND_API` estão corretos no Railway |
| **Login redireciona para `clerk.accounts.dev`** | O domínio próprio não está verificado; cheque DNS |
| **Google login falha** | Credenciais OAuth não configuradas na instância de produção |
| **401 em todas as rotas** | `CLERK_JWKS_URL` aponta para a instância errada; use a URL de produção |
| **DNS não propaga** | Aguarde até 48h; verifique com `nslookup clerk.mercadoinsights.online` |

---

## O que NÃO muda no código

O código do projeto (`clerk-auth.js`, `app/auth.py`) **não precisa de alteração**. Tudo é controlado pelas variáveis de ambiente. A migração é 100% configuração.
