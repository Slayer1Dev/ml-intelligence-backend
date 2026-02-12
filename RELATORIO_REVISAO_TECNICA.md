# Relatório de Revisão Técnica — Mercado Insights

**Data:** 2026-02-12  
**Origem:** Revisão Codex  
**Escopo:** backend FastAPI (`app/`), frontend estático (`frontend/`), testes e documentação.

---

## 1. Resumo Executivo

O projeto está funcional em sua base, porém há pontos críticos de **segurança, isolamento multiusuário, confiabilidade operacional e observabilidade** que merecem priorização.

### Estado geral

| Aspecto | Avaliação |
|---------|-----------|
| **Arquitetura** | Simples e direta, fácil de manter |
| **Qualidade de código** | Boa legibilidade, acoplamento elevado em `main.py` |
| **Testes** | Cobertura muito baixa (2 testes sem asserts efetivos) |
| **Risco para produção** | Médio-alto com múltiplos usuários |

---

## 2. Pontos Críticos (P0)

### C1) Vazamento de dados entre usuários em jobs

**Problema:** `JOB_STORE` global em memória; endpoints `/jobs` e `/jobs/{job_id}` não filtram por usuário.  
**Impacto:** Um usuário pode visualizar jobs de outros (status, nome de arquivo, resultados).  
**Recomendação:** Associar `owner_user_id` em cada job; filtrar leitura por `user.id`; ideal: mover para tabela no banco.

### C2) CORS com `allow_credentials=True` e origem `*`

**Problema:** Combinação inválida em CORS padrão; pode gerar falhas de autenticação no browser.  
**Recomendação:** Em produção, usar lista explícita de origens; manter `allow_credentials=True` apenas com origens específicas.

### C3) Webhook do Mercado Livre sem verificação de assinatura

**Problema:** Endpoint `/api/ml-webhook` aceita payload sem autenticação criptográfica.  
**Impacto:** Terceiros podem forjar eventos (spam, escrita no banco, custos de IA).  
**Recomendação:** Adicionar assinatura/secret; rate limit e idempotência por evento.

---

## 3. Pontos Altos (P1)

### A1) `main.py` monolítico

**Problema:** Arquivo grande concentra rotas, regras de negócio e integrações.  
**Recomendação:** Quebrar em routers (`routers/ml.py`, `routers/admin.py`, etc.) e extrair serviços por domínio.

### A2) Auth em dev ambígua

**Problema:** Comportamento de bypass sem Clerk não está claro.  
**Recomendação:** Definir explicitamente: OU bloqueia sempre, OU cria usuário de dev com flag `DEV_AUTH_BYPASS`.

### A3) `USER_SETTINGS` em memória

**Problema:** Dicionário global perde dados a cada restart/deploy.  
**Recomendação:** Persistir em tabela `user_settings` com defaults versionados.

### A4) Handler genérico de exceções

**Problema:** Retorna apenas "Internal Server Error"; oculta causa raiz.  
**Recomendação:** Incluir `request_id`, correlação e payload sanitizado em logs estruturados.

---

## 4. Pontos Médios (P2)

### M1) Cobertura de testes muito baixa

**Recomendação:** Priorizar testes de API com `TestClient` e cenários de autorização.

### M2) Polling pode escalar mal

**Problema:** Percorre todos os tokens em sequência; risco de timeout/rate limit.  
**Recomendação:** Paginação, backoff exponencial, batching, filas e métricas.

### M3) Upload sem limites robustos

**Recomendação:** Limite de tamanho, validação de MIME, saneamento de nome, validação de colunas obrigatórias.

### M4) Inconsistência em retorno de erros ML

**Problema:** Algumas funções retornam `None`, outras `{error: true, ...}`.  
**Recomendação:** Padronizar contrato (Result object) com `ok/data/error`.

---

## 5. Plano de Implementação Sugerido

### Fase 1 — Correções urgentes (1–3 dias)

1. Corrigir isolamento de jobs por usuário + persistência em banco.
2. Endurecer CORS para produção com allowlist explícita.
3. Implementar validação robusta no webhook ML (assinatura + idempotência).
4. Definir política de auth local.

### Fase 2 — Confiabilidade (3–7 dias)

1. Refatorar `main.py` em routers e serviços.
2. Persistir `user_settings` em banco.
3. Padronizar tratamento de erros.
4. Criar health checks detalhados (`/health`, `/ready`, `/live`).

### Fase 3 — Qualidade e escala (1–2 sprints)

1. Aumentar cobertura de testes.
2. Instrumentar métricas.
3. Introduzir fila para tarefas pesadas.
4. Rate limiting por usuário/endpoint.

---

## 6. Backlog Priorizado

| Prioridade | Item |
|------------|------|
| **P0** | Isolamento de jobs por usuário |
| **P0** | Segurança webhook ML |
| **P0** | CORS produção seguro |
| **P1** | Persistência de configurações do usuário |
| **P1** | Refatoração modular de rotas/serviços |
| **P1** | Padronização de erros de integração |
| **P2** | Logs estruturados + métricas |
| **P2** | Expansão da suíte de testes |
