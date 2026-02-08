# ML Intelligence — Contexto do Projeto (para IA)

> **Uso:** Este arquivo serve como resumo executivo para sessões de IA. Leia-o ao iniciar um novo chat para recuperar o contexto completo do projeto.

---

## 1. O que é o projeto

**ML Intelligence** (também chamado **Mercado Insights**) é um backend FastAPI + frontend HTML para **vendedores do Mercado Livre**. Oferece:

- Calculadora de lucro (sempre gratuita)
- Painel financeiro (upload de planilha ML + custos)
- Anúncios, Performance, Concorrentes (recursos pagos)
- Assinaturas via **Mercado Pago**
- Login e admin via **Clerk**
- Integração **Mercado Livre OAuth** (em progresso)

**URL em produção:** https://www.mercadoinsights.online  
**Deploy:** Railway (Python 3.11, Procfile, railpack.json)

---

## 2. O que pretendemos

1. **Monetização:** Plano Pro Mensal via Mercado Pago (assinaturas)
2. **Integração ML:** Conectar conta do Mercado Livre via OAuth para buscar anúncios, vendas, métricas em tempo real
3. **Painéis com dados reais:** Substituir/suplementar upload manual por API do ML
4. **Certificação ML:** Possível certificação do app no ecossistema Mercado Livre

---

## 3. Arquitetura e principais arquivos

### Backend (`app/`)

| Arquivo | Função |
|---------|--------|
| `main.py` | Rotas FastAPI, guards, endpoints Stripe/MP/ML, mounts estáticos |
| `auth.py` | Clerk JWT, `get_current_user`, `is_admin`, `admin_guard`, `paid_guard`, `ADMIN_EMAILS`, extração de email |
| `models.py` | `User`, `Subscription`, `MlToken` (SQLAlchemy) |
| `database.py` | `SessionLocal`, `init_db`. **Produção:** definir `DATABASE_URL` (PostgreSQL) para persistir dados entre deploys; SQLite no servidor é efêmero. |
| `services/ml_api.py` | OAuth ML: `get_auth_url`, `exchange_code_for_tokens`, `refresh_access_token` |
| `services/mercado_pago_service.py` | Assinaturas MP: `create_checkout_url`, handlers webhook |
| `services/stripe_service.py` | (Legado) não usado — migrado para Mercado Pago |
| `services/user_service.py` | `get_or_create_user` (Clerk → banco) |
| `services/sheet_processor.py`, `ai_agent.py`, `llm_service.py` | Processamento de planilhas, IA |
| `models.py` → `ItemCost` | Custos por anúncio (embalagem, frete, imposto, custo) |

### Frontend (`frontend/`)

| Arquivo | Função |
|---------|--------|
| `clerk-auth.js` | Inicializa Clerk, `authFetch`, guards de login |
| `dashboard.html` | Resumo, CTA assinatura, CTA “Conectar Mercado Livre”, debug admin |
| `callback-ml.html` | Callback OAuth do ML: recebe `?code=`, envia ao backend, redireciona ao dashboard |
| `financeiro.html`, `anuncios.html`, `calculator.html`, etc. | Páginas de ferramentas |
| `admin.html` | Painel admin (usuários, assinaturas, logs) |

### Configuração

| Arquivo | Função |
|---------|--------|
| `Procfile` | `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `railpack.json` | `"secrets": []` — evita erro “secret FRONTEND_URL not found” no Railway |
| `requirements.txt` | Dependências Python |
| `MERCADO-PAGO.md` | Guia de config MP |
| `MERCADO-LIVRE.md` | Guia OAuth ML |

---

## 4. Variáveis de ambiente (Railway)

### Obrigatórias

- `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `CLERK_FRONTEND_API`
- `ADMIN_EMAILS` — e-mails admin separados por vírgula
- `MP_ACCESS_TOKEN` — Mercado Pago (assinaturas)
- `ML_APP_ID`, `ML_SECRET`, `ML_REDIRECT_URI` — Mercado Livre OAuth

### Opcionais

- `FRONTEND_URL`, `BACKEND_URL` — URLs base
- `MP_PLAN_VALUE`, `MP_PLAN_REASON` — valor e nome do plano
- `DATABASE_URL` — **Em produção, use PostgreSQL** (ex.: Railway Postgres) para persistir custos e dados entre deploys; sem isso, SQLite no servidor é apagado a cada deploy.
- `OPENAI_API_KEY` — IA (opcional)
- `ALLOWED_ORIGINS` — CORS

---

## 5. Fluxos principais

### Assinatura (Mercado Pago)

1. Usuário clica “Assinar agora” → `POST /api/create-checkout-session`
2. Backend cria `preapproval_plan` no MP e retorna `init_point`
3. Usuário paga no MP e volta para `?success=1`
4. Webhook `POST /api/mercado-pago-webhook` (topic `subscription_preapproval`) ativa o usuário

### OAuth Mercado Livre

1. Usuário clica “Conectar Mercado Livre” → `GET /api/ml-auth-url` retorna URL OAuth
2. Usuário autoriza no ML e volta para `callback-ml.html?code=xxx`
3. `callback-ml.html` chama `POST /api/ml-oauth-callback` com o `code`
4. Backend troca `code` por tokens, grava em `MlToken`

### Admin

- Admin definido por `ADMIN_EMAILS` (env)
- Clerk JWT deve enviar claim `email` (Customize session token → `{"email": "{{user.primary_email_address}}"}`)
- Endpoint debug: `GET /api/debug-admin` (via botão no dashboard)

---

## 6. Pontos de atenção

1. **railpack.json:** `"secrets": []` é necessário para o build no Railway; sem isso, erro “secret FRONTEND_URL not found”.
2. **MP_PLAN_VALUE:** Aceita vírgula (`109,90`) — conversão feita em `mercado_pago_service.py`.
3. **Email vazio:** Se `is_admin` retorna false, verificar se o Clerk envia `email` no session token (Sessions → Customize session token).
4. **Redirect ML:** `ML_REDIRECT_URI` deve ser exatamente `https://www.mercadoinsights.online/frontend/callback-ml.html`.
5. **stripe_service.py:** Não é usado; mantido por histórico.
6. **MlToken:** Armazena `access_token`, `refresh_token`, `seller_id` por usuário; API do ML ainda não chamada para dados reais.

---

## 7. Próximos passos prováveis

1. ~~Implementar chamadas à API do ML~~ ✅ Feito
2. Endpoint `POST /api/ml-webhook` para notificações (Orders, Items).
3. Implementar área **Concorrentes** (busca ML + comparação).
4. Customer Portal Mercado Pago (gerenciar assinatura).
5. Certificação do app no Mercado Livre.
6. Ver `SITUACAO-E-ROADMAP.md` para análise detalhada e prioridades.

---

## 8. Estrutura do banco (dados por usuário)

- `users` — clerk_user_id, email, plan (free|active)
- `subscriptions` — user_id, stripe_subscription_id (reutilizado para MP), status, started_at, ends_at
- `ml_tokens` — user_id, access_token, refresh_token, seller_id (um por usuário)
- `item_costs` — user_id, item_id (único por usuário+item), custo_produto, embalagem, frete, taxa_pct, imposto_pct
- `audit_logs` — user_id, event_type, message (logs de falhas IA, etc.)

Todas as tabelas de dados sensíveis são filtradas por `user_id`; custos e tokens não são compartilhados entre usuários.
