# ML Intelligence / Mercado Insights — Resumo do Projeto

> **Arquivo de contexto para IA:** Use este documento para entender o projeto e continuar o desenvolvimento na próxima sessão.

---

## O que é o projeto

**ML Intelligence** (Mercado Insights) é uma aplicação web para **vendedores do Mercado Livre**, oferecendo:

- Calculadora de lucro
- Painel financeiro (indicadores, margem, top lucros)
- Análise de anúncios com IA
- Performance e métricas
- Análise de concorrentes
- Integração com Mercado Pago (assinaturas)
- Integração com Mercado Livre OAuth (em andamento)

**Stack:** Backend FastAPI (Python), frontend HTML/JS estático, Clerk (auth), SQLite/PostgreSQL, deploy no Railway.

**Domínio:** `https://www.mercadoinsights.online`

---

## O que pretendemos

1. **Integração Mercado Livre** — Usuários conectam a conta ML via OAuth; backend busca anúncios, vendas e métricas via API.
2. **Webhook ML** — Endpoint `/api/ml-webhook` para notificações (Orders, Items).
3. **Dados reais nos painéis** — Alimentar Painel Financeiro, Anúncios, Performance com dados da API do ML.
4. **Fluxo completo** — OAuth implementado; falta consumir APIs do ML e popular os painéis.

---

## Estrutura principal

```
ml-intelligence-backend/
├── app/
│   ├── main.py              # Rotas FastAPI, guards, endpoints
│   ├── auth.py              # Clerk JWT, get_current_user, is_admin, ADMIN_EMAILS
│   ├── database.py          # SQLite/PostgreSQL, SessionLocal, init_db
│   ├── models.py            # User, Subscription, MlToken
│   └── services/
│       ├── ml_api.py        # OAuth ML: get_auth_url, exchange_code_for_tokens
│       ├── mercado_pago_service.py  # Assinaturas Mercado Pago
│       ├── stripe_service.py        # (legado, não usado)
│       └── ...
├── frontend/
│   ├── dashboard.html       # Resumo, CTA assinar, CTA conectar ML
│   ├── callback-ml.html     # Callback OAuth ML (recebe ?code=)
│   ├── clerk-auth.js        # Init Clerk, authFetch
│   └── ...
├── MERCADO-LIVRE.md         # Doc integração ML
├── MERCADO-PAGO.md          # Doc Mercado Pago
└── railpack.json            # secrets: [] para build
```

---

## Principais arquivos e funções

### `app/main.py`
- `GET /api/me` — Plan, email, isAdmin
- `GET /api/ml-auth-url` — URL OAuth ML
- `POST /api/ml-oauth-callback` — Troca code por tokens, salva MlToken
- `GET /api/ml-status` — Verifica se conta ML conectada
- `POST /api/create-checkout-session` — Mercado Pago checkout
- `POST /api/mercado-pago-webhook` — Webhook MP
- `paid_guard` — Requer plan=active ou is_admin
- `admin_guard` — Requer email em ADMIN_EMAILS

### `app/auth.py`
- `get_current_user` — JWT Clerk → User do banco
- `_extract_email_from_claims` — Extrai email de vários formatos (string, dict, primary_email)
- `is_admin(email)` — Verifica se email está em ADMIN_EMAILS
- `ADMIN_EMAILS` — Lista de emails admin (env ADMIN_EMAILS)

### `app/models.py`
- **User** — clerk_user_id, email, plan (free|active)
- **Subscription** — user_id, stripe_subscription_id (reusado para MP preapproval id)
- **MlToken** — user_id, access_token, refresh_token, seller_id

### `app/services/ml_api.py`
- `get_auth_url()` — URL OAuth ML
- `exchange_code_for_tokens(code)` — Troca code por access_token, refresh_token
- `refresh_access_token(refresh_token)` — Renova access_token
- Variáveis: ML_APP_ID, ML_SECRET, ML_REDIRECT_URI

### `app/services/mercado_pago_service.py`
- `create_checkout_url(...)` — Cria preapproval_plan, retorna init_point
- `handle_preapproval_created`, `handle_preapproval_updated` — Webhook
- Variáveis: MP_ACCESS_TOKEN, MP_PLAN_VALUE, MP_PLAN_REASON

---

## Variáveis de ambiente (Railway)

| Variável | Descrição |
|----------|-----------|
| CLERK_PUBLISHABLE_KEY, CLERK_SECRET_KEY, CLERK_JWKS_URL, CLERK_FRONTEND_API | Clerk auth |
| ADMIN_EMAILS | Emails admin (separados por vírgula) |
| ML_APP_ID, ML_SECRET, ML_REDIRECT_URI | Mercado Livre OAuth |
| MP_ACCESS_TOKEN, MP_PLAN_VALUE, MP_PLAN_REASON | Mercado Pago assinaturas |
| FRONTEND_URL, BACKEND_URL | URLs base |
| DATABASE_URL | SQLite ou PostgreSQL |

---

## Pontos de atenção

1. **Clerk JWT** — O session token precisa do claim `email`. Configurar em **Sessions** (não JWT Templates) → Customize session token → `{"email": "{{user.primary_email_address}}"}`.
2. **railpack.json** — `"secrets": []` evita erro "secret FRONTEND_URL: not found" no build Railway.
3. **MP_PLAN_VALUE** — Aceita vírgula ou ponto (`109,90` ou `109.90`).
4. **MlToken** — Tabela nova; migração automática via `init_db()`.
5. **ML Redirect URI** — Deve ser exatamente `https://www.mercadoinsights.online/frontend/callback-ml.html` (cadastrado no app ML).

---

## O que falta implementar

1. **Endpoint `/api/ml-webhook`** — Receber notificações ML (Orders, Items).
2. **Chamadas à API do ML** — Usar access_token para buscar anúncios, vendas, métricas.
3. **Atualizar painéis** — Financeiro, Anúncios, Performance com dados reais do ML.
4. **Refresh token** — Renovar access_token quando expirar (ML expira em ~6h).
5. **Customer Portal Mercado Pago** — Link para usuário gerenciar assinatura (opcional).

---

## Última sessão — O que foi feito

- Integração Mercado Livre OAuth: modelo MlToken, endpoints ml-auth-url, ml-oauth-callback, ml-status.
- Página callback-ml.html e botão "Conectar Mercado Livre" no dashboard.
- Usuário criou app no ML Developers, configurou credenciais no Railway, fluxo pronto para testar.
- Doc MERCADO-LIVRE.md criada.
- User ID do app ML: 6377184530089001.
