# Deploy no Railway

## 1. Variáveis de ambiente

No painel do Railway → seu projeto → **Variables**, adicione:

| Variável | Valor |
|----------|-------|
| `CLERK_PUBLISHABLE_KEY` | pk_test_... |
| `CLERK_SECRET_KEY` | sk_test_... |
| `CLERK_FRONTEND_API` | https://xxx.clerk.accounts.dev |
| `CLERK_JWKS_URL` | https://xxx.clerk.accounts.dev/.well-known/jwks.json |
| `ALLOWED_ORIGINS` | https://seu-app.railway.app *(opcional)* |

## 2. Clerk — URLs permitidas

No [Clerk Dashboard](https://dashboard.clerk.com) → **Paths** → **Allowed redirect URLs**:

- Adicione a URL do seu app no Railway (ex: `https://ml-intelligence-backend-production.up.railway.app`)

## 3. Deploy

```bash
git add .
git commit -m "feat: Clerk auth, segurança e preparação Railway"
git push origin main
```

O Railway faz o build pelo `Procfile` e inicia com `uvicorn app.main:app`.

## 4. Testar

Após o deploy, acesse a URL do Railway. O redirect `/` leva para `/frontend/index.html`.  
O frontend usa `window.location.origin`, então as chamadas à API vão para o domínio correto.
