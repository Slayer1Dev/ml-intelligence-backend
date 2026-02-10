# Análise do sistema e solução coerente

## 1. O que o código faz hoje

### Integração Mercado Livre
- **OAuth**: usuário conecta conta ML (scope `offline_access read`). Token e refresh salvos em `MlToken`.
- **Webhook de perguntas**: `POST /api/ml-webhook` recebe notificações do ML (tópico `questions`). Responde 200 rápido e processa em background: busca detalhe da pergunta, gera resposta com IA, salva em `PendingQuestion`, envia Telegram/e-mail.
- **Busca pública** (`/sites/MLB/search`): tentamos primeiro **sem token**, depois com token. Em produção o ML costuma retornar **403** para ambos quando o app não é certificado.
- **Comparação**: usa a mesma busca para achar a posição do anúncio do usuário; falha com o mesmo 403.
- **Adicionar concorrente por link**: extrai `MLB-?\d+` da URL, chama `GET /items/{id}` (com token; se 403, tentamos sem token). Funciona para itens públicos.
- **Perguntas via API**: `GET /questions/search?seller_id=...` existe e funciona com o token do vendedor (não depende de certificação da busca).

### O que já foi tentado
- Parser de URL para `MLB-123` e `MLB123`.
- Busca sem token antes de com token.
- Logs no webhook (question_id, user_id_ml, usuário encontrado ou não).
- Fallback no webhook: se não achar usuário por `user_id`, percorre todos os `MlToken` e chama `get_question_detail` até achar o dono da pergunta.
- `get_item_by_id`: retry sem token em caso de 403.
- Admin: exibir `logs/backend.log`, botão atualizar, mensagem quando vazio.
- Migração automática para coluna `telegram_chat_id`.

---

## 2. Por que os problemas persistem

| Problema | Causa provável |
|----------|-----------------|
| **Perguntas não sobem** | (1) Webhook não é chamado pelo ML (URL, tópico ou app não configurado); (2) ML não envia `user_id`/seller no payload e o fallback não encontra o dono; (3) Erro silencioso no processamento em background. |
| **Busca por termo 403** | API `/sites/MLB/search` restringe acesso para apps não certificados (com ou sem token). Documentação ML indica busca básica sem auth em alguns contextos, mas na prática o ML pode bloquear por IP/origem/certificação. |
| **Comparação indisponível** | Mesmo endpoint de busca; mesmo 403. |
| **URL “não encontrada”** | `GET /items/{id}` pode retornar 404 (item inexistente/removido) ou 403 (acesso negado). Fallback sem token já implementado; em alguns casos o item pode estar em outra região ou indisponível. |
| **Logs vazios no Admin** | Em produção (ex.: Railway) o processo pode escrever em stdout e não em `logs/backend.log`, ou o arquivo é efêmero. O painel lê apenas o arquivo. |

---

## 3. Alternativas pesquisadas

### APIs gratuitas / outras formas de obter os mesmos resultados

- **Perguntas**
  - **Webhook (atual)**: correto; depende do ML enviar a notificação. Pode falhar por configuração ou formato do payload.
  - **Polling (sync manual)**: usar a API de perguntas do vendedor (`GET /questions/search?seller_id=...`) que **não exige certificação**. O usuário clica em “Buscar perguntas agora” e o backend traz as não respondidas e enfileira para aprovação. **Viável e recomendado** como complemento ao webhook.
  - Não há API gratuita de terceiros que replique as perguntas do ML.

- **Busca / concorrentes**
  - **Busca pública ML**: em teoria pode funcionar sem auth; na prática estamos recebendo 403 (certificação ou política do ML).
  - **Certificação do app no ML**: desbloqueia a busca; processo formal com o ML.
  - **Adicionar por link/ID (atual)**: não usa busca; usa `GET /items/{id}`. É a alternativa viável **sem certificação** e já está implementada.
  - Scraping: contra os termos do ML; não recomendado.

- **Comparação de posição**
  - Depende da busca; sem certificação continua indisponível.
  - **Alternativa**: o usuário já tem “Meus concorrentes cadastrados” (por link). Podemos destacar na UI que ele pode comparar **preço e vendidos** entre seus anúncios e os concorrentes cadastrados, sem usar a API de busca.

- **Logs**
  - Manter leitura de `logs/backend.log` no Admin.
  - Em produção, considerar enviar logs para um serviço (ex.: stdout + agregador do provedor) e, se houver API, expor “últimas N linhas” no Admin.

---

## 4. Comparação e decisão

| Objetivo | Abordagem atual | Alternativa viável | Decisão |
|----------|------------------|--------------------|---------|
| Ver perguntas dos anúncios | Só webhook | + Sync manual via API de perguntas | Implementar **sync** (botão “Buscar perguntas agora”). |
| Buscar concorrentes por termo | Busca ML (403) | Certificação ou só “por link” | Manter busca; em 403 mostrar mensagem clara e **priorizar “Adicionar por link”**. |
| Comparar posição na busca | Busca ML (403) | Só com certificação | Mensagem explícita; sugerir **comparar pelos concorrentes cadastrados** (preço/vendidos). |
| Adicionar concorrente | Por link/ID + GET /items | Já com fallback sem token | Manter; melhorar mensagem quando 404. |
| Logs no Admin | Arquivo `backend.log` | Stdout em produção | Manter arquivo; mensagem quando vazio; documentar que em produção os logs podem estar no painel do provedor. |

---

## 5. Solução coerente implementada

1. **Perguntas**
   - Novo endpoint **`POST /api/ml/questions/sync`**: busca perguntas do vendedor via API (`questions/search`), filtra não respondidas, para cada uma que ainda não está em `PendingQuestion` chama a mesma lógica do webhook (detalhe, IA, salvar, notificar). **Não depende do webhook.**
   - Botão **“Buscar perguntas agora”** na tela “Perguntas nos anúncios” que chama esse endpoint e atualiza a lista. O usuário pode puxar as perguntas manualmente quando quiser.

2. **Concorrentes / Busca**
   - Em 403/503 na busca: mensagem única e objetiva: *“A busca do Mercado Livre está restrita para este app. Use **Adicionar concorrente por link ou ID** acima para acompanhar concorrentes.”*
   - Reforçar na UI que o fluxo principal é “Adicionar por link”.

3. **Comparação**
   - Em 503 na comparação: mensagem: *“A comparação na busca exige certificação do app no ML. Você pode comparar preços e vendidos na lista **Meus concorrentes cadastrados** (adicione concorrentes pelo link).”*

4. **Documentação**
   - Este arquivo (`ANALISE-E-SOLUCAO.md`) deixa registrado: causas, alternativas, decisões e o que foi implementado.

---

## 6. Resumo

- **Perguntas**: webhook mantido; **sync manual** via API de perguntas garante que as perguntas “subam” mesmo se o webhook falhar.
- **Busca/Comparação**: 403 é limitação do ML (certificação); não há API gratuita alternativa que substitua a busca oficial. Solução: mensagens claras e uso de **concorrentes por link** + comparação por preço/vendidos na lista.
- **Dados tratados de forma inteligente**: reuso da mesma lógica do webhook no sync; fluxo de concorrentes focado em link/ID e lista cadastrada.
- **Viabilidade**: sync de perguntas e mensagens de UX são viáveis imediatamente; busca/posição só com certificação do app no Mercado Livre.
