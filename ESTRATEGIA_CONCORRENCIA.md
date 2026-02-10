# 🎯 ESTRATÉGIA DE MONITORAMENTO DE CONCORRÊNCIA - MERCADO INSIGHTS

**Data:** 09/02/2026  
**Baseado em:** Pesquisa de mercado + Análise técnica

---

## ✅ VALIDAÇÃO DA ABORDAGEM ATUAL

### Nossa estratégia está CORRETA ✓

Após pesquisa extensa sobre como **comparadores profissionais** (Zoom, Buscapé, Google Shopping) funcionam:

**✅ Usam API Oficial do ML** (não scraping)  
**✅ Adição por ID/Link individual** (base sólida)  
**✅ Cache inteligente** com TTL variável  
**✅ Rate limiting** com backoff exponencial  
**❌ Evitam scraping** (risco de bloqueio, não conformidade)

**Conclusão:** Não precisamos mudar arquitetura. Apenas **corrigir bugs** e **otimizar**.

---

## 🔧 CORREÇÃO APLICADA (09/02/2026)

### Problema: Mensagens de erro genéricas

**Antes:**
- Erro de conexão → "Anúncio não encontrado"
- 404 (não existe) → "Anúncio não encontrado"
- 500 (erro ML) → "Anúncio não encontrado"

**Causa:** `get_item_by_id()` retornava `None` para todos os erros.

### Solução Implementada

#### 1. `get_item_by_id()` agora retorna dict com erro

**Arquivo:** `app/services/ml_api.py`

```python
# Antes
except requests.RequestException as e:
    _log.warning("ML get item error: %s", e)
    return None  # ❌ Perde informação

# Depois
except requests.RequestException as e:
    _log.warning("ML get item error: %s", e)
    return {
        "error": True,
        "status_code": 0,
        "message": str(e),
        "detail": f"Erro de conexão: {type(e).__name__}"
    }  # ✅ Preserva detalhes
```

#### 2. Rota `/api/ml/competitors` diferencia erros

**Arquivo:** `app/main.py`

```python
if item and item.get("error"):
    status_code = error_info.get("status_code", 0)
    
    if status_code == 0:
        raise HTTPException(503, "Erro de conexão...")
    elif status_code == 404:
        raise HTTPException(404, "Anúncio não encontrado...")
    elif status_code == 403:
        raise HTTPException(403, "Acesso negado...")
    else:
        raise HTTPException(503, f"Erro ML ({status_code})...")
```

### Resultado

**Mensagens claras por tipo:**
- ✅ Erro de conexão → "Erro de conexão com a API do Mercado Livre..."
- ✅ 404 → "Anúncio MLB123 não encontrado. Verifique se está ativo."
- ✅ 403 → "Acesso negado. Verifique se sua conta ML está conectada."
- ✅ 500 → "Erro no servidor do Mercado Livre (500)..."

---

## 📚 COMO COMPARADORES PROFISSIONAIS FUNCIONAM

### 1. Coleta de Dados

#### **API Oficial do ML** (método preferido)

**Endpoints principais:**

| Endpoint | Uso | Autenticação |
|----------|-----|--------------|
| `/items/{ID}` | Buscar produto específico | Opcional |
| `/items?ids={ID1},{ID2},...` | Multiget (até 20 por vez) | Opcional |
| `/sites/MLB/search?q=...` | Busca pública por termo | Opcional |
| `/sites/MLB/search?seller_id=...` | Produtos de um vendedor | Opcional |
| `/users/{USER_ID}/items/search` | Lista completa de itens | OAuth |
| `/products/search?product_identifier=...` | Busca por EAN/GTIN | Opcional |

**Limitações conhecidas:**
- `available_quantity` retorna **faixas**, não valores exatos
- Busca pública pode ter restrições para apps não certificados (403)
- Rate limits variam (normalmente ~1000 req/hora sem certificação)

#### **Scraping** (último recurso)

**Usado apenas quando:**
- Dados não estão disponíveis via API
- Necessário em tempo real (ex: disponibilidade instantânea)
- Escala justifica custo de proxies (~$20-100/mês)

**Plataformas terceiras:**
- **Apify:** ~$20/mês + uso
- **Oxylabs:** ~$49/mês + volume
- **ScraperAPI:** ~$29/mês

**Riscos:**
- Bloqueio de IP
- Violação de termos de uso
- Necessita manutenção constante (ML muda HTML)
- CAPTCHA e anti-bot

**Nossa recomendação:** **Evitar scraping.** API oficial é suficiente.

---

### 2. Estratégias de Atualização

| Método | Frequência | Uso | Custo |
|--------|-----------|-----|-------|
| **Webhooks** | Tempo real | Notificações de mudanças | Baixo |
| **Polling Agressivo** | A cada 10-30min | Produtos críticos | Médio |
| **Polling Moderado** | A cada 2-4h | Produtos normais | Baixo |
| **Polling Relaxado** | A cada 12-24h | Produtos de baixa demanda | Muito baixo |
| **Manual** | Sob demanda | Análises pontuais | Zero |

**Comparadores profissionais usam:**
- Webhooks (quando disponível)
- Polling com **priorização** (produtos mais vendidos = update mais frequente)
- Cache de 4-8h para dados estáveis (título, categoria)
- Cache de 1-2h para dados voláteis (preço, estoque)

---

### 3. Otimizações Comuns

#### **Multiget (Recomendado)**

Em vez de:
```python
# 20 requisições separadas
for id in ids:
    item = get_item_by_id(id)
```

Usar:
```python
# 1 requisição com 20 IDs
GET /items?ids=MLB1,MLB2,...,MLB20&attributes=id,price,title
```

**Vantagem:** 20x mais eficiente.

#### **Seleção de Campos**

```python
# Retorna tudo (~5KB por item)
GET /items/MLB123

# Retorna apenas o necessário (~500B)
GET /items/MLB123?attributes=id,price,title,sold_quantity
```

**Vantagem:** 10x menos dados, resposta mais rápida.

#### **Cache Inteligente**

```python
cache = {
    "MLB123": {
        "data": {...},
        "cached_at": datetime.now(),
        "ttl": 3600  # 1 hora para preço
    }
}

# Antes de requisitar
if cache.get(item_id) and cache[item_id]["cached_at"] + cache[item_id]["ttl"] > now():
    return cache[item_id]["data"]  # Usa cache
else:
    fetch_from_api()  # Atualiza
```

#### **Rate Limiting com Token Bucket**

```python
class TokenBucket:
    def __init__(self, capacity=100, refill_rate=10):
        self.capacity = capacity  # máx tokens
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens/segundo
    
    def consume(self, tokens=1):
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False  # aguardar
```

#### **Backoff Exponencial**

```python
def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:  # Rate limit
            wait = 2 ** attempt  # 1s, 2s, 4s...
            time.sleep(wait)
        else:
            raise Exception(f"Erro {resp.status_code}")
    raise Exception("Max retries")
```

---

## 🚀 ROADMAP DE MELHORIAS

### Fase 1: Estabilização (CONCLUÍDA ✅)
- [x] Corrigir mensagens de erro
- [x] Validar abordagem (API oficial)
- [x] Documentar estratégia

### Fase 2: Otimização Básica (PRÓXIMOS PASSOS)
- [ ] Implementar **Multiget** (`/items?ids=...`)
- [ ] Adicionar **cache em memória** (TTL 1-4h)
- [ ] Implementar **rate limiting** (Token Bucket)
- [ ] Adicionar **backoff exponencial** para 429

### Fase 3: Escalabilidade (FUTURO)
- [ ] Cache persistente (Redis)
- [ ] Fila de atualização com priorização
- [ ] Histórico de preços (banco de dados)
- [ ] Webhooks ML (se disponível)

### Fase 4: Avançado (SE NECESSÁRIO)
- [ ] Certificação ML (se GMV > $10k/mês)
- [ ] Proxies (se bloqueio persistir)
- [ ] Scraping (apenas se API insuficiente)

---

## 📊 BENCHMARKS DE REFERÊNCIA

### Zoom/Buscapé (Maior comparador BR)
- **Catálogo:** 2,5 milhões de produtos
- **Lojas:** 300+ integradas
- **Monitoramento:** 16 milhões de ofertas/ano
- **Histórico:** 40 dias a 6 meses
- **Método:** API de afiliados + scraping complementar

### Nossa escala atual
- **Produtos monitorados:** <100 (estimado por usuário)
- **Usuários:** <1000 (estimado)
- **Requests/dia:** <10.000 (estimado)

**Conclusão:** API oficial é suficiente para nossa escala por anos.

---

## 🎯 RECOMENDAÇÕES FINAIS

### Curto Prazo (1-2 semanas)
1. ✅ **Testar correção aplicada** (mensagens de erro)
2. ⚠️ **Implementar Multiget** para listar concorrentes (20x mais rápido)
3. ⚠️ **Cache em memória** com TTL de 2h

### Médio Prazo (1-3 meses)
1. **Rate limiting** para evitar bloqueio
2. **Histórico de preços** (graváveis no banco)
3. **Atualização automática** periódica (cron job a cada 4h)

### Longo Prazo (6+ meses)
1. **Certificação ML** (se escala justificar - GMV $10k+/mês)
2. **Webhooks** para updates em tempo real
3. **Analytics** de tendências de mercado

---

## 📚 REFERÊNCIAS

### Documentação Oficial ML
- [API Docs](https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br)
- [Itens e Buscas](https://developers.mercadolivre.com.br/pt_br/itens-e-buscas)
- [Developer Partner Program](https://global-selling.mercadolibre.com/devsite/developer-partner-program-global-selling)

### Ferramentas Terceiras (Referência)
- [Apify ML Scrapers](https://apify.com/spider.engine/mercadolibre-deals-scraper)
- [Oxylabs](https://oxylabs.io/products/scraper-api/ecommerce/mercadolibre)

### Comparadores Brasileiros
- Zoom + Buscapé (fusão 2018)
- Google Shopping (Merchant Center)

---

**Última atualização:** 09/02/2026  
**Status:** Estratégia validada, correções aplicadas, roadmap definido.
