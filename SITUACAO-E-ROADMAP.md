# Mercado Insights — Situação e Roadmap

> Documento atualizado para refletir o estado atual, correções feitas e próximos passos.

---

## 1. Nome e domínio

- **Nome:** Mercado Insights (anteriormente ML Intelligence)
- **Domínio:** https://www.mercadoinsights.online

---

## 2. Bugs e melhorias recentes

| Item | Correção |
|------|----------|
| **Insights de IA — Method Not Allowed** | Frontend envia POST; endpoint ajustado |
| **Botões sem coerência** | Classe `btn-primary-actions` padronizada |
| **Gráfico Top 10 com 1 item** | Layout adaptável, placeholder quando vazio |
| **Admin sem logs visíveis** | Logs exibem últimas 500 linhas |
| **Admin sem alterar plano** | `PATCH /api/admin/users/{id}/plan` + botões Pro/Free |
| **Admin sem métricas** | Aba Métricas: usuários, planos, assinaturas |
| **Assinaturas sem expiração** | Coluna "Expira em" (ends_at) na tabela |
| **Concorrentes falhando** | Fallback busca pública; mensagens de erro melhoradas |
| **Funções de IA sem log** | Tabela `audit_logs`; Admin aba "Logs IA" |
| **Dados somem a cada deploy** | PostgreSQL via `DATABASE_URL`; `item_costs` com constraint único |
| **Perguntas sem histórico** | Tabela `question_answer_feedback`; histórico na interface |
| **Notificações Telegram** | Bot funcional; chat_id em `users`; mensagem de teste em config-ml |

---

## 3. Estado atual — o que está pronto

| Área | Status | Observação |
|------|--------|------------|
| Login (Clerk) | ✅ | Funcional |
| OAuth Mercado Livre | ✅ | Tokens em `ml_tokens`, refresh automático |
| Assinaturas (Mercado Pago) | ✅ | Checkout, webhook, planos Pro/Free |
| Meus Anúncios | ✅ | active, paused, pending, closed; custos; links ML |
| Painel Financeiro | ✅ | Dados ML + custos + Insights IA + Top 10 |
| Calculadora de Lucro | ✅ | Funcional |
| Performance | ✅ | Cards clicáveis, links para anúncios |
| Concorrentes | ✅ | Adicionar por link/ID; busca por termo (403 em apps não certificados) |
| Perguntas nos anúncios | ✅ | Webhook + polling 10 min + sync ao abrir; IA sugere respostas; histórico |
| IA Assistente | ✅ | Perguntas sobre vendas + gerador de respostas |
| Telegram | ✅ | Notificações de novas perguntas; mensagem de teste |
| Admin | ✅ | Métricas, usuários, planos, assinaturas, logs, Logs IA, audit_logs |
| Banco | ✅ | PostgreSQL; dados isolados por `user_id` |
| Diagnóstico | ✅ | Relatório .txt com testes extremos |

---

## 4. Implementações recentes (sessão 2026-02-12)

| Item | Status |
|------|--------|
| **P0: CORS** | ✅ Permite todas origens por padrão; restrição opcional via `ALLOWED_ORIGINS` |
| **P0: Isolamento de jobs** | ✅ `_owner` por usuário; filtro em `/jobs` e `/jobs/{job_id}` |
| **P0: Webhook ML idempotente** | ✅ Cache de question_ids processados (TTL 1h) |
| **Página Assinatura e Pagamentos** | ✅ `GET /api/billing/status`, `GET /api/billing/history`, `POST /api/billing/cancel` + frontend `assinatura.html` |
| **Identidade visual unificada** | ✅ Botões, tabs, favicon, design system em `app.css` |
| **Documentação reorganizada** | ✅ 15 arquivos consolidados; `DOCUMENTACAO.md` como índice |
| **Relatório Codex integrado** | ✅ `RELATORIO_REVISAO_TECNICA.md` |
| **Documento jurídico** | ✅ `DOCUMENTO_JURIDICO_TERMOS_E_ASSINATURA.md` |

---

## 5. Próximos passos (priorizados)

### Prioridade média

| # | Item | Descrição |
|---|------|------------|
| 1 | **Performance** | Refinar layout e resumo da tela Performance |
| 2 | **Termos e Privacidade** | Redigir textos legais (Termos de Uso, Política de Privacidade) e versionar no banco |
| 3 | **Logs IA** | Registrar sucessos; filtrar por tipo |
| 4 | **Certificação ML** | Solicitar certificação do app para busca autenticada estável |

### Backlog

| # | Item |
|---|------|
| 5 | **Cache ML** — Tabela `ml_cache` para reduzir chamadas |
| 6 | **Editor de prompts** — Admin customizar prompts de IA |
| 7 | **Integração ML Mensagens** — Responder clientes via API |
| 8 | **Health checks** — `/health`, `/ready`, `/live` |
| 9 | **Rate limiting** — Por usuário/endpoint |

---

## 6. Estrutura técnica

### Endpoints principais

- `GET /api/me`, `GET /api/ml-status`
- `GET /api/ml/items`, `GET /api/ml/search`, `POST /api/ml/competitors`
- `GET /api/ml/questions/pending`, `GET /api/ml/questions/history`, `POST /api/ml/questions/sync`
- `POST /api/telegram/test`
- `POST /api/ml-webhook` — Webhook ML (tópico questions, com idempotência)
- `GET /api/diagnostic-report`
- `GET /api/billing/status` — Status da assinatura do usuário
- `GET /api/billing/history` — Histórico de assinaturas
- `POST /api/billing/cancel` — Cancelar assinatura ativa

### Modelos principais

- `User`, `MlToken`, `Subscription`, `ItemCost`, `PendingQuestion`, `QuestionAnswerFeedback`, `AuditLog`

### Infraestrutura

- **Polling:** APScheduler sincroniza perguntas a cada 10 min
- **Webhook ML:** Tópico "Questions" configurado no portal ML
- **Telegram:** Usuário deve enviar /start ao bot antes de vincular

---

## 8. Revisão técnica (Codex)

O relatório **RELATORIO_REVISAO_TECNICA.md** documenta pontos de segurança e robustez:

- **P0 (corrigidos):** Isolamento de jobs por usuário ✅; CORS seguro ✅; idempotência do webhook ML ✅
- **P1:** Refatoração de `main.py`; persistência de `user_settings`; tratamento de exceções
