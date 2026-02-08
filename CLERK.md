# Integração Clerk (Opção A)

Autenticação com **Clerk** no ML Intelligence — FastAPI + HTML estático.

## Configuração

### 1. Instalar dependência

```bash
pip install -r requirements.txt
```

### 2. Variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto (ou configure no Railway):

```
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
CLERK_FRONTEND_API=https://seu-dominio.clerk.accounts.dev
CLERK_JWKS_URL=https://seu-dominio.clerk.accounts.dev/.well-known/jwks.json
ADMIN_EMAILS=seu@email.com,outro@email.com
```

- **ADMIN_EMAILS**: e-mails (separados por vírgula) que têm acesso ao painel Admin.

Onde obter:
1. [Clerk Dashboard](https://dashboard.clerk.com) → sua aplicação
2. **API Keys** → copie Publishable Key e Secret Key
3. **Frontend API** → URL tipo `https://xxx.clerk.accounts.dev`
4. **JWKS** = Frontend API + `/.well-known/jwks.json`

### 3. URLs permitidas no Clerk

No Clerk Dashboard → **Paths** / **Allowed redirect URLs**, adicione:
- `http://127.0.0.1:8000/frontend/*` (local)
- `https://seu-app.railway.app/*` (produção)

## Como funciona

- **Frontend**: `clerk-auth.js` carrega o Clerk JS, monta SignIn/UserButton e fornece `authFetch()` para requisições com Bearer token.
- **Backend**: `fastapi-clerk-auth` valida o JWT do Clerk em rotas protegidas.
- **Sem Clerk configurado**: o app segue funcionando em modo dev (sem auth).

## Rotas protegidas

- `POST /api/calculate-profit`
- `POST /api/financial-dashboard`
- `POST /upload-planilha`
- `GET /jobs`
- `GET /jobs/{job_id}`

## Páginas com Clerk

- Dashboard, Calculadora, Painel Financeiro, Anúncios, Performance, Concorrentes.

---

## Segurança

- `.env` está no `.gitignore` — **nunca** faça commit de chaves.
- Em produção (Railway): configure as variáveis no painel, não use arquivo `.env` no repo.
- CORS: em produção, defina `ALLOWED_ORIGINS` (ex: `https://seu-app.railway.app`).
