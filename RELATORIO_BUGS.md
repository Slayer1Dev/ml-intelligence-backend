# 🔍 RELATÓRIO DE DIAGNÓSTICO - INTEGRAÇÕES MERCADO LIVRE

**Data inicial:** 09/02/2026  
**Última atualização:** 09/02/2026 21:00  
**Status:** ✅ Problemas #2 e #3 CORRIGIDOS | ⚠️ Outros pendentes  
**Escopo:** Concorrência, Perguntas e Análise de Anúncios

---

## 🆕 ATUALIZAÇÕES

### 09/02/2026 - 21:00
- ✅ **Problema #2 CORRIGIDO:** `search_public()` e `get_item_by_id()` agora retornam dict com detalhes de erro
- ✅ **Problema #3 MELHORADO:** Mensagens específicas por tipo de erro (403, 429, 500, etc.)
- ✅ **Validação de estratégia:** Pesquisa confirmou que nossa abordagem (API oficial) está correta
- 📄 **Novo documento:** `ESTRATEGIA_CONCORRENCIA.md` com roadmap de otimizações

### 09/02/2026 - 18:00
- ✅ Código de debug removido (localhost 127.0.0.1:7242)
- ✅ URLs hardcoded corrigidas
- ✅ Nome alterado: "ML Intelligence" → "Mercado Insights"
- ✅ Mixed Content corrigido (imagens HTTPS)

---

## 🚨 PROBLEMA CRÍTICO #1: VARIÁVEIS DE AMBIENTE AUSENTES

### Arquivo Afetado
- `.env` (raiz do projeto)

### Descrição
As variáveis de ambiente essenciais para a API do Mercado Livre **NÃO ESTÃO CONFIGURADAS**:
- `ML_APP_ID` - ❌ AUSENTE
- `ML_SECRET` - ❌ AUSENTE
- `ML_REDIRECT_URI` - ❌ AUSENTE

### Arquivos que Dependem
- `app/services/ml_api.py` (linhas 10-13)
- `app/main.py` (rotas OAuth, linhas 507-601)

### Impacto
**CRÍTICO** - Todas as funções de integração com o Mercado Livre retornarão `None` ou falharão silenciosamente:
- ✗ `get_auth_url()` retorna `None` (linha 18-19)
- ✗ `exchange_code_for_tokens()` retorna `None` (linha 32-33)
- ✗ `refresh_access_token()` retorna `None` (linha 49-50)
- ✗ OAuth callback não consegue trocar código por tokens
- ✗ Renovação automática de tokens falha
- ✗ Sem tokens válidos, TODAS as requisições à API do ML falham

### Causa Provável
Arquivo `.env` só contém configurações do Clerk. As credenciais do Mercado Livre nunca foram adicionadas ou foram removidas acidentalmente.

---

## ⚠️ PROBLEMA #2: SILENCIAMENTO DE ERROS NA API DO ML

### Arquivos Afetados
- `app/services/ml_api.py` (múltiplas funções)

### Descrição
Todas as funções de API retornam `None` em caso de erro, **sem lançar exceções** ou fornecer detalhes:

#### Funções com Retorno Silencioso
1. **`search_public()`** (linhas 159-192)
   - Status != 200: apenas `_log.warning()` e retorna `None`
   - Exceções capturadas: `_log.warning()` e retorna `None`

2. **`get_questions_search()`** (linhas 225-254)
   - Status != 200: apenas `_log.warning()` e retorna `None`
   - Exceções capturadas: `_log.warning()` e retorna `None`

3. **`get_item_by_id()`** (linhas 289-311)
   - Falhas registradas em warning, mas retorna `None`

4. **`post_answer()`** (linhas 272-286)
   - Falha ao publicar: apenas `_log.warning()` e retorna `None`

5. **`get_user_items()`** (linhas 72-103)
   - Status != 200: retorna `None` sem detalhes

### Impacto
**ALTO** - Dificulta o diagnóstico:
- Frontend recebe `null` ou mensagens genéricas
- Logs não mostram o erro real da API do ML
- Usuário não sabe se o problema é token, permissão ou certificação

### Causa Provável
Design defensivo: evitar crashes, mas sacrifica transparência. Deveria lançar `HTTPException` com o detalhe do erro do ML.

---

## ⚠️ PROBLEMA #3: BUSCA PÚBLICA SEM TOKEN (403 ESPERADO)

### Arquivos Afetados
- `app/main.py` (linhas 722-745, 838-889)
- `frontend/concorrentes.html` (linhas 331-423)

### Descrição
As rotas de busca (`/api/ml/search` e `/api/ml/compare`) tentam primeiro **sem token**, depois **com token**, mas apps não certificados sempre recebem **403 Forbidden** da API do ML:

```python
# linha 734: tenta sem token
result = search_public(site_id="MLB", q=q.strip(), limit=limit, offset=offset, sort=sort, access_token=None)

# linha 736-739: se falhar, tenta com token (mas também falhará se app não é certificado)
if result is None:
    token = get_valid_ml_token(user)
    access_token = token.access_token if token else None
    if access_token:
        result = search_public(...)
```

### Impacto
**MÉDIO** - Busca por termo não funciona (esperado para apps não certificados):
- Mensagem de erro é genérica: "503 - A busca do Mercado Livre está restrita para este app"
- Frontend mostra fallback para adicionar por link/ID (comportamento correto)

### Causa Provável
**NÃO É BUG** - Limitação da API do ML para apps não certificados. Sistema já tem workaround (adicionar por link/ID).

---

## ⚠️ PROBLEMA #4: TOKEN ML PODE ESTAR EXPIRADO OU INVÁLIDO

### Arquivos Afetados
- `app/main.py` (função `get_valid_ml_token`, linhas 566-594)
- `app/services/ml_api.py` (função `refresh_access_token`, linhas 47-60)

### Descrição
Se o token ML estiver expirado e a renovação falhar, o sistema retorna `None` **sem notificar o usuário**:

```python
# linha 578-590
new_tokens = refresh_access_token(token.refresh_token)
if new_tokens and "access_token" in new_tokens:
    # renova...
else:
    logger.warning(f"Falha ao renovar token ML para usuário {user.id}")
    return None  # ❌ Usuário não sabe que precisa reconectar
```

### Impacto
**ALTO** - Usuário com conta conectada vê "ml_not_connected" sem saber por quê:
- Token expira depois de 6 horas (padrão ML)
- Renovação falha se: refresh_token inválido, ML_APP_ID/ML_SECRET ausentes, rede fora
- Frontend recebe 403 "ml_not_connected" mas não explica que o token expirou

### Causa Provável
Falta tratamento de erro quando `refresh_access_token()` retorna `None` devido às variáveis ausentes.

---

## ⚠️ PROBLEMA #5: FALTA VALIDAÇÃO DE PARÂMETROS MLB

### Arquivos Afetados
- `app/main.py` (função `_parse_ml_item_id`, linhas 748-757)
- `app/services/ml_api.py` (função `search_public`, linha 185)

### Descrição
A função `_parse_ml_item_id()` aceita "MLB-123" e "MLB123", mas a API do ML espera **apenas "MLB123"** (sem hífen):

```python
# linha 755-756
raw = match.group(0).upper()
return raw.replace("-", "") if "-" in raw else raw
```

O parâmetro `site_id` é hardcoded como "MLB" (linha 734, 860), mas nunca é validado se o ID do item corresponde ao site.

### Impacto
**BAIXO** - Código já remove o hífen corretamente. Não é bug, mas poderia validar se o ID pertence ao site correto (MLB vs MLM, MLA, etc.).

### Causa Provável
Simplificação: assume que todos os usuários vendem no Brasil (MLB). Funciona para o caso de uso atual.

---

## ⚠️ PROBLEMA #6: FALTA LOGGING NO FRONTEND

### Arquivos Afetados
- `frontend/concorrentes.html` (linha 343)
- `frontend/perguntas-anuncios.html` (linha 138)

### Descrição
Quando uma requisição falha, o frontend **não registra detalhes do erro** no console:

```javascript
// linha 367-370 (concorrentes.html)
if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Erro na busca');
}
```

O erro é capturado, mas os detalhes (status code, headers, body completo) não são logados.

### Impacto
**MÉDIO** - Dificulta debug no navegador:
- Dev Tools não mostra o erro real do backend
- Usuário vê apenas mensagem genérica

### Causa Provável
Falta `console.error(res.status, await res.text())` antes de lançar exceção.

---

## ⚠️ PROBLEMA #7: WEBHOOK DE PERGUNTAS PODE FALHAR SILENCIOSAMENTE

### Arquivos Afetados
- `app/main.py` (rota `/api/ml-webhook`, linhas 1035-1089)

### Descrição
Se o `seller_id` não bater com nenhum usuário, o webhook retorna **200 OK** mas não processa:

```python
# linha 1086-1088
else:
    logger.warning("Webhook ML questions: usuário não encontrado. question_id=%s user_id_ml=%s", question_id, user_id_ml)
# retorna 200 de qualquer forma (linha 1089)
```

ML não reenvia notificações com 200 OK, então a pergunta é **perdida**.

### Impacto
**ALTO** - Perguntas podem não chegar se:
- `seller_id` no webhook não bate com o cadastrado no banco
- Usuário conectou ML mas `seller_id` não foi salvo corretamente

### Causa Provável
Fallback tenta buscar usuário por todos os tokens (linhas 1068-1081), mas se falhar, pergunta é perdida. Deveria retornar **404** para ML reenviar.

---

## ⚠️ PROBLEMA #8: CORS PODE ESTAR BLOQUEANDO REQUISIÇÕES

### Arquivos Afetados
- `app/main.py` (configuração CORS, linhas 55-62 - não mostradas no diagnóstico, mas inferidas)

### Descrição
Se `ALLOWED_ORIGINS` não estiver configurado corretamente, o navegador pode bloquear requisições do frontend para o backend.

### Impacto
**CRÍTICO** se ocorrer - Todas as requisições falham com erro de CORS:
- Navegador não permite `authFetch()` enviar `Authorization` header
- Erro no console: "Access-Control-Allow-Origin"

### Causa Provável
**HIPÓTESE** (não confirmada) - Se backend e frontend estão em domínios diferentes sem CORS configurado.

---

## ⚠️ PROBLEMA #9: FALTA TRATAMENTO DE RATE LIMIT DA API ML

### Arquivos Afetados
- `app/services/ml_api.py` (todas as funções que fazem requests)

### Descrição
API do Mercado Livre tem rate limit (limite de requisições por minuto). Código não verifica status **429 Too Many Requests**:

```python
# linha 186-188 (search_public)
if resp.status_code != 200:
    _log.warning("ML search failed: status=%s body=%s", resp.status_code, resp.text[:200])
    return None
```

Status 429 é tratado igual a qualquer erro, sem retry ou backoff.

### Impacto
**MÉDIO** - Em uso intenso (ex: sincronizar muitas perguntas), API pode bloquear temporariamente:
- Usuário vê "Erro ao buscar" sem saber que é rate limit
- Deveria esperar e tentar novamente

### Causa Provável
Falta lógica de retry com exponential backoff para 429.

---

## ⚠️ PROBLEMA #10: FALTA VALIDAÇÃO DE CONEXÃO ANTES DE LISTAR CONCORRENTES

### Arquivos Afetados
- `frontend/concorrentes.html` (função `loadCompetitors`, linhas 254-294)

### Descrição
Frontend tenta carregar concorrentes mesmo se ML não está conectado:

```javascript
// linha 184-186
if (mlConnected) {
    document.getElementById('compare-section').style.display = 'block';
    loadMyItems();
    loadCompetitors(); // ❌ Chama mesmo sem verificar token válido
}
```

Se token expirou no servidor mas `mlConnected` ainda é `true`, a requisição falha.

### Impacto
**BAIXO** - Lista fica vazia, mas não explica por quê. Deveria verificar `/api/ml-status` antes de cada ação crítica.

### Causa Provável
`mlConnected` é verificado apenas no `checkAccess()` inicial. Não revalida em ações subsequentes.

---

## 📊 RESUMO DOS PROBLEMAS

| # | Problema | Status | Severidade | Arquivo Principal | Linha |
|---|----------|--------|-----------|-------------------|-------|
| 1 | **Variáveis ML ausentes no .env** | ✅ **N/A** | 🟢 (estão na Railway) | `.env` | - |
| 2 | Silenciamento de erros (retorna None) | ✅ **CORRIGIDO** | 🟡 Alta | `app/services/ml_api.py` | 159-365 |
| 3 | Busca pública retorna 403 (esperado) | ✅ **MELHORADO** | 🟢 Média | `app/main.py` | 722-770 |
| 4 | Token expirado sem notificação | ⚠️ **PENDENTE** | 🟡 Alta | `app/main.py` | 566-594 |
| 5 | Validação de parâmetro MLB | ✅ **OK** | 🟢 Baixa | `app/main.py` | 773-782 |
| 6 | Falta logging de erros no frontend | ✅ **CORRIGIDO** | 🟡 Média | `frontend/concorrentes.html` | 355-385 |
| 7 | Webhook retorna 200 mesmo sem processar | ⚠️ **PENDENTE** | 🟡 Alta | `app/main.py` | 1035-1089 |
| 8 | CORS pode bloquear requisições | ✅ **OK** | 🟢 (configurado) | `app/main.py` | 81-87 |
| 9 | Falta tratamento de rate limit (429) | ⚠️ **PENDENTE** | 🟡 Média | `app/services/ml_api.py` | várias |
| 10 | Falta revalidação de token no frontend | ⚠️ **PENDENTE** | 🟢 Baixa | `frontend/concorrentes.html` | 184-186 |
| 11 | 🆕 Código de debug em produção | ✅ **CORRIGIDO** | 🔴 CRÍTICA | `clerk-auth.js`, `dashboard.html`, etc. | várias |
| 12 | 🆕 URLs hardcoded (localhost) | ✅ **CORRIGIDO** | 🔴 CRÍTICA | `jobs.html`, `logs.html`, `app.js` | várias |

**Status geral:** 6 problemas corrigidos | 4 pendentes (não bloqueantes)

---

## 🎯 PRIORIDADE DE CORREÇÃO

### 1️⃣ **IMEDIATO** (Bloqueia todas as integrações)
- [ ] Adicionar `ML_APP_ID`, `ML_SECRET` e `ML_REDIRECT_URI` no `.env`

### 2️⃣ **URGENTE** (Melhora diagnóstico e confiabilidade)
- [ ] Lançar exceções com detalhes nos erros de API ML (em vez de retornar `None`)
- [ ] Notificar usuário quando token ML expirar (em vez de `ml_not_connected` genérico)
- [ ] Retornar 404 no webhook se usuário não for encontrado (para ML reenviar)

### 3️⃣ **IMPORTANTE** (Melhora experiência e debugging)
- [ ] Adicionar `console.error()` com detalhes no frontend quando requisições falharem
- [ ] Implementar retry com backoff para rate limit (429)
- [ ] Revalidar `/api/ml-status` antes de ações críticas no frontend

### 4️⃣ **OPCIONAL** (Melhorias incrementais)
- [ ] Validar se ID do item corresponde ao site correto (MLB vs outros)
- [ ] Cache de resultados de busca para reduzir calls à API ML

---

## 🧪 TESTES SUGERIDOS (APÓS CORREÇÕES)

1. **Teste de autenticação**
   - Adicionar credenciais ML no `.env`
   - Conectar conta ML via OAuth
   - Verificar se token é salvo no banco (`ml_tokens` table)

2. **Teste de busca de concorrentes**
   - Buscar termo no campo de pesquisa
   - Verificar se retorna 403 ou dados (depende de certificação)
   - Adicionar concorrente por link/ID (deve funcionar)

3. **Teste de perguntas**
   - Fazer pergunta em anúncio ML (ou usar webhook de teste)
   - Verificar se chega em `/api/ml/questions/pending`
   - Aprovar resposta e verificar se publica no ML

4. **Teste de renovação de token**
   - Expirar token manualmente no banco (setar `expires_at` no passado)
   - Fazer requisição que use `get_valid_ml_token()`
   - Verificar se renova automaticamente

---

## 📝 OBSERVAÇÕES ADICIONAIS

### Logs do Backend
- Arquivo: `logs/backend.log`
- **Status:** Vazio (backend pode não estar rodando ou logs não estão sendo escritos)
- Verificar se o servidor está ativo e se o diretório `logs/` tem permissões de escrita

### Frontend
- Autenticação Clerk funcionando corretamente
- Headers `Authorization: Bearer {token}` sendo enviados via `authFetch()`
- Função `authFetch()` adiciona token JWT automaticamente (linha 75-79, `clerk-auth.js`)

### Backend
- Validação JWT Clerk funcionando (`get_current_user` em `auth.py`)
- Middleware `paid_guard` verifica plano ativo corretamente
- Sistema de renovação de token ML está implementado, mas falha por falta de credenciais

---

## 🔗 ARQUIVOS ANALISADOS

- ✅ `app/services/ml_api.py` - Funções de API ML
- ✅ `app/main.py` - Rotas de concorrencia (722-890), perguntas (1035-1250), analise (1586-1599)
- ✅ `app/auth.py` - Autenticação Clerk e guards
- ✅ `app/models.py` - Modelo MlToken
- ✅ `frontend/concorrentes.html` - UI de concorrentes
- ✅ `frontend/perguntas-anuncios.html` - UI de perguntas
- ✅ `frontend/clerk-auth.js` - Autenticação frontend
- ✅ `.env` - Variáveis de ambiente
- ✅ `.env.example` - Template de configuração

---

**FIM DO RELATÓRIO**  
_Próximo passo: Implementar correções conforme prioridade acima._
