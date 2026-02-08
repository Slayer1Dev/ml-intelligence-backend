# ML Intelligence — Análise da Situação e Alinhamento com o Roadmap

> Documento criado para alinhar o que temos, identificar bugs, e planejar próximos passos.

---

## 1. Bugs Identificados

### 1.1 Anúncios com dados vazios ("Sem título", R$ 0,00, status "unknown")

**Causa:** A API do Mercado Livre retorna os itens no formato:
```json
[
  { "code": 200, "body": { "id": "MLB123", "title": "...", "price": 100, ... } },
  ...
]
```

O backend repassa o array inteiro, mas o frontend espera cada item com `item.title`, `item.price` diretamente. Os dados reais estão em `item.body`.

**Correção:** No endpoint `/api/ml/items`, extrair `body` de cada objeto da resposta antes de enviar ao frontend.

---

### 1.2 "Conecte sua conta" ao recarregar (já estando conectado)

**Possíveis causas:**

| Causa | Explicação |
|-------|------------|
| **Race condition** | O `authFetch` pode ser chamado antes do Clerk carregar o token. Sem `Authorization`, o backend retorna 401. O `catch` interpreta como falha e `checkMLConnection()` retorna `false`. |
| **403 ambíguo** | Os endpoints `/api/ml/items` e `/api/ml/metrics` usam `paid_guard`. Se o usuário não tem plano pago, retorna 403. O frontend trata **qualquer 403** como "conta não conectada", mas pode ser "sem assinatura". |
| **Sessão Clerk** | Em reload, o Clerk pode demorar para restaurar a sessão. A chamada a `ml-status` pode ir sem token. |

**Correções sugeridas:**
1. Diferenciar erros: 403 com "Conta não conectada" vs 403 com "Assinatura necessária".
2. No frontend: aguardar Clerk estar pronto antes de chamar `checkMLConnection`.
3. Melhorar mensagens: se 403 por `paid_guard`, mostrar "Assine o plano para acessar" em vez de "Conecte o ML".

---

### 1.3 Banco de dados — persistência do MlToken

O `MlToken` é salvo corretamente no OAuth callback. Não há evidência de perda de dados no banco. O problema provável é na **recuperação** (auth/timing), não no armazenamento.

---

## 2. O que está pronto

| Área | Status | Observação |
|------|--------|------------|
| Login (Clerk) | ✅ | Funcional |
| OAuth Mercado Livre | ✅ | Tokens salvos em `ml_tokens` |
| Meus Anúncios | ✅ | Lista todos os status (ativo, pausado, fechado, inativo p/ revisar) |
| Performance | ✅ | Cards clicáveis, links para anúncios, resumo melhorado |
| Concorrentes | ✅ | Busca por termo + comparar meu anúncio |
| Admin — Usuários | ✅ | Lista usuários |
| Admin — Assinaturas | ✅ | Lista assinaturas |
| Admin — Logs | ✅ | Mostra arquivo `logs/backend.log` |
| Painel Financeiro | ✅ | Upload de planilha |
| Calculadora de Lucro | ✅ | Funcional |

---

## 3. O que falta (alinhado ao ROADMAP.md)

### Curto prazo (correções) — concluído

1. ~~Corrigir estrutura da resposta de `/api/ml/items`~~ ✅
2. ~~Tratar erros 403 de forma distinta~~ ✅
3. ~~Melhorar sincronização no frontend~~ ✅
4. ~~Melhorar Performance — layout, cards, links~~ ✅
5. ~~Filtro "Todos" em Meus Anúncios — inclui pausados/inativo para revisar~~ ✅

### Médio prazo (funcionalidades)

5. **Concorrentes** — buscar anúncios por termo/categoria na API do ML e comparar com os do usuário
6. **Logs estruturados no admin** — se desejar logs consultáveis por conta/evento (além do arquivo atual)
7. **Refresh token** — já implementado; garantir que funcione em produção

### Banco de dados — melhorias sugeridas

| Melhoria | Descrição |
|----------|-----------|
| **Tabela `audit_log`** | Registrar ações importantes (login, OAuth, erros de API) para debug |
| **Tabela `ml_cache`** (opcional) | Cache de dados do ML para reduzir chamadas à API |
| **Índices** | Garantir índices em `ml_tokens.user_id`, `subscriptions.user_id` |

---

## 4. Próximos passos sugeridos

### Fase 1 — Bugs (prioridade alta)

1. Corrigir parsing da resposta `get_multiple_items` no backend
2. Diferenciar 403 no frontend (ML vs plano)
3. Garantir que `checkMLConnection` rode apenas após Clerk pronto

### Fase 2 — Melhorias de UX

4. Melhorar tela de Performance (links, resumo mais rico)
5. Revisar mensagens de erro nas páginas

### Fase 3 — Concorrentes — concluído ✅

6. ~~Implementar busca na API ML~~ ✅
7. ~~Página Concorrentes com listagem e comparação~~ ✅

### Fase 4 — Admin e banco

8. Tabela `audit_log` para eventos importantes
9. Admin: abas de logs estruturados (opcional)

---

## 5. Resumo executivo

- **Principais bugs:** (1) Dados dos anúncios vazios por causa da estrutura da API ML; (2) Mensagem "Conecte sua conta" incorreta por mistura de 403 e timing do Clerk.
- **Banco:** Estrutura atual adequada; MlToken está persistindo. Melhorias opcionais: `audit_log` e índices.
- **Admin:** Já possui logs (arquivo). Logs estruturados em banco são evolução futura.
- **Roadmap:** Fases A e B do ROADMAP concluídas. Fase D (API ML) em andamento. Falta Concorrentes e polish nas telas.
