# ML Intelligence — Análise da Situação e Roadmap

> Documento atualizado para refletir o estado atual, bugs corrigidos e próximos passos.

---

## 1. Bugs Corrigidos (sessão atual)

| Bug | Correção |
|-----|----------|
| **Insights de IA — Method Not Allowed** | Frontend enviava GET; endpoint espera POST. Corrigido: `authFetch` com `method: 'POST'`. |
| **Botões sem coerência visual** | Padronizados: "Atualizar dados do ML" e "Insights de IA" com classe `btn-primary-actions`. |
| **Gráfico Top 10 ruim com 1 item** | Gráfico adaptável: eixo Y horizontal quando ≤4 itens, placeholder quando vazio, barras proporcionais. |
| **Admin sem logs visíveis** | Logs exibem últimas 500 linhas; mensagem amigável quando vazio ou inexistente. |
| **Admin sem alterar plano** | Endpoint `PATCH /api/admin/users/{id}/plan` + botões Pro/Free na tabela de usuários. |
| **Admin sem métricas** | Nova aba "Métricas": usuários totais, plano ativo, free, assinaturas, contas ML conectadas. |
| **Assinaturas sem expiração** | Coluna "Expira em" (ends_at) na tabela de assinaturas. |
| **Concorrentes falhando** | Fallback: se busca com token falhar (403), tenta busca pública. Mensagens de erro melhoradas. |
| **Funções de IA sem log** | Tabela `audit_logs` criada; falhas de Insights de IA são registradas. Admin: aba "Logs IA". |

---

## 2. O que está pronto

| Área | Status | Observação |
|------|--------|------------|
| Login (Clerk) | ✅ | Funcional |
| OAuth Mercado Livre | ✅ | Tokens salvos em `ml_tokens` |
| Meus Anúncios | ✅ | Lista todos os status; popup para editar custos; links Ver no ML, Editar no ML |
| Performance | ✅ | Cards clicáveis, links para anúncios |
| Concorrentes | ✅ | Busca (com fallback público) + comparar; botões estilizados |
| IA Assistente | ✅ | Perguntas sobre vendas/ML + gerador de respostas para clientes |
| Análise por anúncio | ✅ | Importar planilha ANALISE ANUNCIOS (CONTA 1 ML, CONTA 2 ML) — pesquisa, preços, ações propostas |
| Admin — Métricas | ✅ | Total usuários, plano ativo, assinaturas, contas ML |
| Admin — Usuários | ✅ | Lista + alterar plano (Pro/Free) |
| Admin — Assinaturas | ✅ | Início, expira em, status |
| Admin — Logs | ✅ | Arquivo `logs/backend.log` |
| Admin — Logs IA | ✅ | Tabela `audit_logs` com falhas de IA |
| Painel Financeiro | ✅ | API ML + custos + Insights IA (crítico: vendas, preço vs mercado) + gráfico + análise por anúncio |
| Calculadora de Lucro | ✅ | Funcional |
| Plano de pagamento filtrado | ✅ | Não aparece como produto |
| Anúncios inativos | ✅ | Status `under_review` incluído |

---

## 3. Pendências e próximos passos

### Prioridade alta — concluído ✅

1. ~~**Campo de perguntas + resposta IA**~~ — Página IA Assistente: usuário pergunta e recebe resposta gerada por IA.
2. ~~**Prompts para responder clientes**~~ — Gerador de respostas por situação (pedido atrasado, dúvida, reclamação, etc.) com contexto opcional.

### Prioridade média

3. **Busca** — Agora usa busca pública (sem token) primeiro; token gera 403 em apps não certificados.
4. **Logs de IA** — Expandir para registrar também sucessos (opcional) e outros eventos.
5. **Performance** — Melhorar layout e resumo conforme feedback.

### Melhorias futuras

6. **Cache ML** — Tabela `ml_cache` para reduzir chamadas à API.
7. **Editor de prompts** — Admin poder customizar prompts de IA.
8. **Integração ML Mensagens** — Responder clientes via API (se disponível).

---

## 4. Estrutura técnica

### Novos endpoints

- `GET /api/admin/metrics` — Métricas do sistema
- `PATCH /api/admin/users/{id}/plan` — Alterar plano do usuário
- `GET /api/admin/audit-logs` — Logs de auditoria (falhas IA)
- `POST /api/ia/perguntas` — Responde perguntas do vendedor (body: `{ pergunta }`)
- `POST /api/ia/resposta-cliente` — Gera sugestão de resposta (body: `{ tipo, contexto?, mensagem_cliente? }`)
- `POST /api/analise-anuncios` — Importa planilha ANALISE ANUNCIOS e retorna análise por anúncio

### Novos modelos

- `AuditLog` — event_type, message, extra, user_id, created_at

### Banco de dados

- Tabela `audit_logs` criada automaticamente no `init_db`.
- **Persistência em produção:** definir `DATABASE_URL` com PostgreSQL (ex.: Railway adiciona ao criar o plugin Postgres). Sem isso, o SQLite no servidor é efêmero e custos/dados somem a cada deploy.
- `item_costs`: constraint único `(user_id, item_id)`; dados sempre filtrados por `user_id`.

---

## 5. Resumo executivo

- **Correções:** Insights de IA (POST), botões coerentes, gráfico adaptável, admin completo (métricas, plano, logs, logs IA), concorrentes com fallback, logs de falhas de IA.
- **Pendente:** Campo de perguntas com IA, prompts para clientes, certificação ML para busca estável.
- **Roadmap:** Foco em perguntas/respostas IA e prompts para atendimento ao cliente.
