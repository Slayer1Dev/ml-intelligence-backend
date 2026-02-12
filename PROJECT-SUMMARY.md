# Mercado Insights — Resumo do Projeto

> **Arquivo de contexto para IA:** Use este documento para entender o projeto e continuar o desenvolvimento.

---

## O que é o projeto

**Mercado Insights** é uma aplicação web para **vendedores do Mercado Livre**, oferecendo:

- **Dashboard** — Resumo, conectividade ML, CTA assinatura
- **Meus Anúncios** — Lista anúncios (ativos, pausados, inativos para revisar, fechados), custos por item, links Ver/Editar no ML
- **Painel Financeiro** — Indicadores, margem, custos, Insights de IA, gráfico Top 10
- **Calculadora de Lucro** — Custo, preço, despesas, lucro e margem
- **Performance** — Métricas e cards por anúncio
- **Concorrentes** — Busca por termo (limitada em apps não certificados) + adicionar por link/ID, comparação
- **Perguntas nos anúncios** — IA sugere respostas, aprovação/edição, publicação no ML, histórico
- **IA Assistente** — Perguntas sobre vendas e gerador de respostas para clientes
- **Notificações Telegram** — Avisos de novas perguntas no celular
- **Integração Mercado Pago** — Assinaturas Pro
- **Admin** — Métricas, usuários, planos, assinaturas, logs, audit logs

**Stack:** Backend FastAPI (Python), frontend HTML/JS estático, Clerk (auth), PostgreSQL, deploy Railway.

**Domínio:** https://www.mercadoinsights.online

---

## Estado atual (2026)

| Área | Status |
|------|--------|
| Auth (Clerk) | ✅ Funcional |
| OAuth Mercado Livre | ✅ Tokens em `ml_tokens`, refresh automático |
| Assinaturas (Mercado Pago) | ✅ Checkout, webhook, planos Pro/Free |
| Meus Anúncios | ✅ Todos status (active, paused, pending, closed), custos, multiget |
| Painel Financeiro | ✅ Dados ML + custos + Insights IA |
| Concorrentes | ✅ Adicionar por link/ID; busca por termo pode retornar 403 (app não certificado) |
| Perguntas | ✅ Webhook + polling 10 min + sync ao abrir página; histórico no banco |
| Telegram | ✅ Notificações; mensagem de teste; chat_id em `users` |
| Banco | ✅ PostgreSQL; `question_answer_feedback` para histórico Q&A |
| Admin | ✅ Métricas, usuários, planos, logs, audit_logs |
| Diagnóstico | ✅ Relatório completo baixável (.txt) com testes extremos |

---

## Estrutura principal

```
ml-intelligence-backend/
├── app/
│   ├── main.py              # Rotas, webhooks, diagnóstico
│   ├── auth.py              # Clerk JWT, guards, ADMIN_EMAILS
│   ├── database.py          # PostgreSQL, migrações
│   ├── models.py            # User, MlToken, PendingQuestion, QuestionAnswerFeedback, etc.
│   └── services/
│       ├── ml_api.py        # API ML (OAuth, search, items, questions)
│       ├── notification_service.py  # Telegram, e-mail
│       ├── mercado_pago_service.py  # Assinaturas
│       └── llm_service.py   # IA (OpenAI)
├── frontend/
│   ├── dashboard.html, anuncios.html, financeiro.html, ...
│   ├── config-ml.html       # Config ML + Telegram + diagnóstico
│   ├── perguntas-anuncios.html
│   ├── app.css               # Design system
│   └── favicon.png
├── IDENTIDADE_VISUAL.md      # Guia de marca
├── DEPLOY_INSTRUCOES.md      # Deploy Railway
└── requirements.txt
```

---

## Endpoints principais

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | /api/me | Plan, email, isAdmin, telegramLinked, telegramChatId |
| GET | /api/ml-status | Conectado, seller_id |
| GET | /api/ml/items | Anúncios (status, limit, offset) |
| GET | /api/ml/search | Busca por termo (403 comum em apps não certificados) |
| POST | /api/ml/competitors | Adicionar concorrente por ID/URL |
| GET | /api/ml/questions/pending | Perguntas aguardando aprovação |
| GET | /api/ml/questions/history | Histórico de perguntas respondidas |
| POST | /api/ml/questions/sync | Sincronizar perguntas do ML |
| POST | /api/telegram/test | Enviar mensagem de teste |
| GET | /api/diagnostic-report | Relatório de diagnóstico (.txt) |
| POST | /api/ml-webhook | Webhook ML (tópico questions) |

---

## Variáveis de ambiente (Railway)

| Variável | Descrição |
|----------|-----------|
| CLERK_* | Auth Clerk |
| ADMIN_EMAILS | Emails admin (vírgula) |
| ML_APP_ID, ML_SECRET, ML_REDIRECT_URI | Mercado Livre OAuth |
| TELEGRAM_BOT_TOKEN | Bot Telegram para notificações |
| MP_ACCESS_TOKEN, MP_PLAN_*, MP_WEBHOOK_SECRET | Mercado Pago |
| OPENAI_API_KEY | IA (perguntas, insights) |
| DATABASE_URL | PostgreSQL |
| FRONTEND_URL, ALLOWED_ORIGINS | URLs e CORS |

---

## Pontos de atenção

1. **Busca ML 403** — Apps não certificados recebem 403 em `/sites/MLB/search`. Use "Adicionar por link/ID".
2. **Telegram "chat not found"** — Usuário deve enviar /start ao bot antes de vincular.
3. **Webhook ML** — Configure tópico "Questions" no portal ML para notificações em tempo real.
4. **Polling** — APScheduler executa sync de perguntas a cada 10 min.
