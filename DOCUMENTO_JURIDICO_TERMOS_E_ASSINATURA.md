# Documento Jurídico-Técnico: Termos, Contrato de Usuário e Página de Assinatura

**Data:** 2026-02-12  
**Destinatário:** Desenvolvedor Sênior / Produto / Jurídico  
**Projeto:** Mercado Insights (ML Intelligence Backend)

> **Importante:** Este material é técnico e orientativo. A versão final dos documentos jurídicos deve ser validada por advogado(a).

---

## 1. Objetivo

Base para:
1. **Termos de Uso** da plataforma.
2. **Contrato de Usuário (SaaS)** com regras de assinatura/pagamento.
3. **Política de Privacidade e Tratamento de Dados (LGPD)**.
4. **Página de acompanhamento de pagamento e assinatura** (especificação funcional e técnica).

---

## 2. Enquadramento legal no Brasil (resumo)

### 2.1 LGPD (Lei 13.709/2018)
- Definir base legal por tratamento; finalidades claras; compartilhamentos (ML, MP, OpenAI, Clerk, hospedagem).
- Direitos do titular (acesso, correção, eliminação, portabilidade, revogação).
- Retenção/descarte; canal de privacidade (DPO ou e-mail).

### 2.2 Marco Civil da Internet
- Logs de acesso e eventos; transparência; regras de suspensão/bloqueio.

### 2.3 CDC (B2C)
- Preço, periodicidade, renovação e cancelamento claros; reembolso; suporte; cláusulas não abusivas.

### 2.4 Pagamentos/assinatura
- Transparência de cobrança recorrente; data de renovação; histórico; cancelamento acessível.

---

## 3. Checklist — Termos de Uso

- Objeto do serviço; elegibilidade e cadastro; planos e limitações.
- Integrações de terceiros (ML, OpenAI etc.); disponibilidade/SLA.
- Uso aceitável (proibição de fraude, abuso de API, engenharia reversa, spam).
- Propriedade intelectual; suspensão e encerramento; limitação de responsabilidade.
- Atualizações dos termos; foro e lei aplicável (Brasil).
- **Recomendado:** plataforma não substitui consultoria jurídica/contábil; IA assistiva; responsabilidade do usuário sobre conteúdos em marketplaces; dependência de credenciais válidas.

---

## 4. Checklist — Contrato de Usuário (SaaS)

- Partes e definições; licença de uso limitada, revogável e não exclusiva.
- Plano, valor, recorrência e forma de pagamento; reajuste com aviso prévio.
- Inadimplência (suspensão, regularização, encerramento); cancelamento (usuário e plataforma).
- Reembolso/estorno (prazo e critérios); proteção de dados; responsabilidades; limitação de responsabilidade; vigência e rescisão.
- **Explícito:** quando cobra (mensal, data); teste grátis; efeito do cancelamento (imediato vs fim do ciclo); status `active`, `past_due`, `canceled`, `trialing`; reativação.

---

## 5. Checklist — Política de Privacidade (LGPD)

- **Inventário:** `clerk_user_id`, e-mail; status do plano/assinatura; logs; tokens OAuth ML, seller_id, perguntas/respostas.
- **Finalidades:** autenticação; execução do serviço; cobrança e antifraude; melhoria e suporte.
- **Texto:** compartilhamento com operadores; prazos de retenção e descarte; direitos do titular + canal; segurança (criptografia, acesso, logs).

---

## 6. Riscos atuais (priorização)

1. **Transparência de cobrança** — usuário deve ver histórico e situação em tela dedicada.
2. **Rastreabilidade de consentimento** — guardar aceite de Termos/Privacidade por versão e timestamp.
3. **Dependência de terceiros** — contrato deve prever indisponibilidade de APIs sem responsabilização integral.
4. **Dados em perguntas** — política deve explicar que o usuário é controlador e a plataforma opera em parte do fluxo.

---

## 7. Especificação da página “Assinatura e Pagamentos”

### 7.1 Objetivo
Acompanhamento em tempo real: plano atual, situação da assinatura, próxima cobrança, histórico, ações (gerenciar, cancelar, reativar).

### 7.2 UI mínima
- **Resumo:** plano, status (Ativa/Pendente/Atrasada/Cancelada), valor mensal, data de início, próxima cobrança.
- **Histórico:** lista de cobranças (data, valor, status, método, ID); filtros.
- **Ações:** Gerenciar assinatura; Cancelar; Reativar; link suporte financeiro.
- **Legais:** links para Termos, Contrato, Política de Privacidade.

### 7.3 Estados obrigatórios
- `active` — acesso completo + próxima cobrança.
- `pending` — aviso de processamento.
- `past_due` — banner de alerta + CTA regularizar.
- `canceled` — data final de acesso + CTA reativar.
- `no_subscription` — CTA assinar plano.

### 7.4 API (backend)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/billing/status` | Plano, status, valor, ciclo, próxima cobrança, cancelamento |
| GET | `/api/billing/history?from=&to=&status=` | Lista paginada de cobranças |
| POST | `/api/billing/cancel` | Solicitar cancelamento |
| POST | `/api/billing/reactivate` | Reativar quando permitido |
| GET | `/api/billing/legal-links` | URLs versionadas Termos/Contrato/Privacidade |

**Exemplo de resposta `/api/billing/status`:**
```json
{
  "plan": "pro_mensal",
  "status": "active",
  "amount": 29.90,
  "currency": "BRL",
  "started_at": "2026-02-01T10:00:00Z",
  "next_billing_at": "2026-03-01T10:00:00Z",
  "cancel_at_period_end": false,
  "provider": "mercado_pago",
  "subscription_id": "sub_xxx"
}
```

### 7.5 Auditoria e compliance
- Registrar mudanças de status de assinatura.
- Guardar `accepted_terms_version`, `accepted_privacy_version`, `accepted_at`, `ip`, `user_agent` no aceite.
- Exibir versão dos documentos vigentes na área da conta.

---

## 8. Dados (banco) para jurídico + billing

Sugestão:

1. **`legal_documents`** — `id`, `doc_type` (terms/privacy/contract), `version`, `content_url`, `published_at`, `active`.
2. **`user_legal_acceptances`** — `id`, `user_id`, `doc_type`, `version`, `accepted_at`, `ip`, `user_agent`.
3. **`billing_events`** — `id`, `user_id`, `provider`, `event_type`, `event_status`, `amount`, `currency`, `provider_event_id`, `created_at`, `raw_payload`.
4. **`subscriptions`** (evolução) — `provider`, `next_billing_at`, `cancel_at_period_end`, `canceled_at`, `trial_ends_at`.

---

## 9. Critérios de aceite

### Jurídico
- [ ] Termos de Uso redigidos e validados.
- [ ] Contrato com política de cobrança/cancelamento explícita.
- [ ] Política de Privacidade LGPD com inventário e direitos do titular.
- [ ] Versionamento e histórico de aceite por usuário.

### Produto/Engenharia
- [ ] Página “Assinatura e Pagamentos” no frontend autenticado.
- [ ] Endpoints status/histórico/cancelamento/reativação.
- [ ] Webhooks de pagamento idempotentes.
- [ ] Logs e auditoria de alterações de assinatura.

### UX e suporte
- [ ] Mensagens claras por status; fluxo de cancelamento sem ambiguidade; link de suporte e FAQ.

---

## 10. Plano de execução (curto prazo)

| Semana | Foco |
|--------|------|
| **1** | Escopo jurídico (Termos + Contrato + Privacidade v1); modelo de dados aceite + billing; endpoints `billing/status` e `billing/history`. |
| **2** | Página assinatura/pagamentos no frontend; cancelamento/reativação; links legais versionados e registro de aceite. |
| **3** | Hardening: auditoria, idempotência de webhook, testes E2E; revisão jurídica e publicação v1.0. |

---

## 11. Observações para desenvolvimento

- Pode ser tratado como **épico** em 3 frentes: Jurídico, Billing Core, Billing UI.
- Priorizar transparência de assinatura e histórico financeiro (suporte, churn, risco jurídico).
- Evitar novos fluxos de cobrança sem telas e textos legais versionados.
