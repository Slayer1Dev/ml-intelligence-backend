# Varredura de bugs e melhorias — ML Intelligence Backend

Relatório de beta test crítico: bugs encontrados, riscos e sugestões de melhoria.

**Correções aplicadas (resolução baseada neste documento):**  
Bugs 1–7, 9–10, 12–13 corrigidos. Bug 8 já estava protegido (guards de divisão por zero). Melhorias 11, 14–15 permanecem como sugestões (documentação/paginação, persistência de settings, mais eventos em audit_log).

---

## Bugs críticos (quebram fluxo)

### 1. Upload de planilha: dado errado passado para análise
- **Onde:** `app/main.py` → `process_job()` (linha ~114)
- **Problema:** Quando `process_sheet()` retorna sucesso, o retorno é um **dict** `{"records": [...], "rows": N}`. O código chama `analyze_uploaded_sheet(records)` passando esse dict inteiro. Em `ai_agent.analyze_uploaded_sheet()` o laço é `for item in records:`, então itera pelas **chaves** ("records", "rows"), não pela lista de linhas. Em seguida `calculate_profit(item, settings)` recebe string ("records" ou "rows") e quebra com `KeyError` ou tipo inválido.
- **Correção:** Passar apenas a lista de registros:  
  `analysis = analyze_uploaded_sheet(records.get("records", []))`

### 2. `get_settings()` chamado sem argumento
- **Onde:** `app/services/ai_agent.py` → `analyze_uploaded_sheet()` (linha ~45)
- **Problema:** `get_settings(user_id: str)` exige `user_id`, mas é chamado como `get_settings()`. Isso gera **TypeError** assim que o job de upload tenta rodar a análise (após corrigir o bug 1).
- **Correção:** O job em background não tem `user` no escopo. É preciso: (a) passar `user_id` ao enfileirar o job em `upload_planilha` e para `process_job`, e (b) chamar `get_settings(str(user_id))` em `analyze_uploaded_sheet`, ou (c) usar defaults quando `user_id` não estiver disponível (ex.: `get_settings(user_id or "")` e garantir que `get_settings("")` retorne defaults).

### 3. Painel financeiro (dashboard) com planilha ML: colunas fixas em inglês
- **Onde:** `app/main.py` → `financial_dashboard()` (linhas ~992–1005)
- **Problema:** O código usa `df.get("PRICE")`, `df.get("FEE_PER_SALE")`, `df.get("SKU")`, `df.get("STATUS")`, `df.get("QUANTITY")`, `df.get("TITLE")`. A planilha exportada do Mercado Livre pode ter cabeçalhos em **português** (ex.: "Preço", "Taxa", "Status", "Quantidade"). Se alguma coluna não existir, `df.get(...)` retorna **None** e:
  - `df.get("FEE_PER_SALE").apply(_parse_percent)` → **AttributeError** (None.apply).
  - Demais métricas ficam NaN ou quebram.
- **Correção:** Normalizar colunas como em `_parse_analise_anuncios` (aliases em PT/EN), por exemplo uma função `_find_col(df, "PRICE", "Preço", "Preco")` e usar a coluna encontrada em vez de nomes fixos.

### 4. Tipo do arquivo de custos apenas pelo nome
- **Onde:** `app/main.py` → `_parse_costs_sheet(file_bytes, filename)` (linha ~318)
- **Problema:** CSV vs Excel é decidido por `filename.lower().endswith(".csv")`. Se o usuário enviar um CSV com extensão `.xlsx` (ou sem extensão), o código tenta ler como Excel e falha.
- **Melhoria:** Detectar pelo conteúdo (magic bytes) ou tentar CSV primeiro e fallback para Excel quando fizer sentido.

---

## Bugs de robustez / edge cases

### 5. `except:` sem tipo (bare except)
- **Onde:** `app/services/ai_agent.py` (linha ~34), `app/services/normalizer.py` (linhas ~7 e ~12)
- **Problema:** Captura até `KeyboardInterrupt`/`SystemExit`, dificulta debug e pode esconder erros reais.
- **Correção:** Usar `except Exception:` e, se possível, logar o erro.

### 6. Arquivos temporários nunca removidos
- **Onde:** `app/main.py` → `upload_planilha` grava em `tmp_dir / safe_name` e `process_job` usa o arquivo, mas não há `os.remove`/`unlink` após o processamento.
- **Problema:** Disco enche em uso contínuo; em produção pode ser crítico.
- **Correção:** No final de `process_job` (em `finally`), remover o arquivo se existir.

### 7. JOB_STORE em memória sem limite
- **Onde:** `app/main.py` → `JOB_STORE: Dict[str, Dict] = {}`
- **Problema:** Jobs nunca são removidos; em deploy com muitas requisições o dicionário cresce sem limite. Em restart todos os jobs são perdidos.
- **Melhoria:** Limitar tamanho (ex.: últimos N jobs), ou TTL; considerar persistir estado em Redis/DB para jobs importantes.

### 8. Divisão por zero em cálculo de margem
- **Onde:** `app/main.py` → `calculate_profit_endpoint`: `margem = (lucro / data.preco_venda) * 100 if data.preco_venda else 0`. Outros pontos usam `(profit / price) * 100` sem checagem.
- **Risco:** Se em algum fluxo `preco_venda` ou `price` for 0 sem o `if`, gera **ZeroDivisionError**.
- **Verificar:** Garantir que todos os cálculos de margem tenham guard (if preco/preco_venda) ou use `price or 1` apenas onde for seguro.

---

## Segurança e exposição

### 9. Rotas de análise/sheets sem autenticação
- **Onde:** `app/main.py` → `/sheets/test`, `/analysis/base`, `/analysis/market`, `/analysis/market/ai`
- **Problema:** Qualquer um pode chamar. Se `read_sheet()` (Google Sheets?) retornar dados sensíveis, há vazamento.
- **Melhoria:** Proteger com `Depends(get_current_user)` ou remover em produção.

### 10. Webhook Mercado Pago sem validação de assinatura
- **Onde:** `app/main.py` → `mercado_pago_webhook`
- **Problema:** Recebe POST e processa sem verificar se a requisição veio mesmo do MP (ex.: assinatura HMAC ou token). Permite falsificar notificações e ativar planos.
- **Melhoria:** Implementar validação conforme documentação do Mercado Pago (verificar header/body com secret).

---

## Melhorias gerais

### 11. Recursão em `get_user_items(status="all")`
- **Onde:** `app/services/ml_api.py` → `get_user_items` quando `status == "all"`
- **Observação:** Faz 4 chamadas (active, paused, closed, under_review) e concatena; retorna no máximo 50 de cada. Se o usuário tiver mais de 50 em algum status, o “total” agregado pode ser enganoso. Documentar ou paginar.

### 12. Mensagem de erro do job genérica
- **Onde:** `process_job` em caso de exceção grava `str(e)` no JOB_STORE. Para o usuário pode ser pouco claro (ex.: KeyError, TypeError).
- **Melhoria:** Mapear erros conhecidos para mensagens amigáveis e logar o traceback completo no servidor.

### 13. Configuração do servidor (README / ambiente)
- **Observação:** Em ambiente de teste, `uvicorn` não estava no PATH. O README diz apenas `uvicorn app.main:app --reload`.
- **Sugestão:** Incluir alternativa: `python -m uvicorn app.main:app --reload` para quem não tem uvicorn no PATH.

### 14. User settings em memória
- **Onde:** `app/services/user_settings.py` → `USER_SETTINGS = {}`
- **Problema:** Configurações por usuário são perdidas ao reiniciar e não são compartilhadas entre workers/instâncias.
- **Melhoria:** Persistir em banco (ex.: tabela `user_settings`) ou cache externo.

### 15. Logs e auditoria
- **Positivo:** Uso de `AuditLog` para falhas de IA e arquivo de log do backend.
- **Sugestão:** Incluir em audit_log eventos como “upload planilha”, “OAuth ML conectado”, “checkout iniciado”, para rastreio de abusos e suporte.

---

## Resumo prioritário

| Prioridade | Item | Ação sugerida |
|------------|------|----------------|
| P0 | Bug 1 – dict em vez de lista no job | Passar `records.get("records", [])` para `analyze_uploaded_sheet` |
| P0 | Bug 2 – get_settings() sem user_id | Passar user_id no job e para get_settings, ou defaults |
| P0 | Bug 3 – colunas do financial_dashboard | Normalizar colunas PT/EN (aliases) antes de usar |
| P1 | Bug 5 – bare except | Trocar por `except Exception:` e log |
| P1 | Bug 6 – arquivos tmp | Remover arquivo em `finally` em `process_job` |
| P1 | Bug 10 – webhook MP | Validar assinatura do webhook |
| P2 | Bug 4 – tipo arquivo custos | Detecção por conteúdo ou fallback |
| P2 | Bug 7 – JOB_STORE | Limite de tamanho ou TTL |
| P2 | Bug 9 – rotas sem auth | Proteger /sheets e /analysis |

---

*Varredura feita por análise estática e fluxo de código. Recomenda-se rodar o sistema localmente (ex.: `python -m uvicorn app.main:app --reload`), repetir os fluxos de upload, painel financeiro e webhook para validar correções.*
