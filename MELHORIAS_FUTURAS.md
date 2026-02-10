# 🚀 ROADMAP DE MELHORIAS - MERCADO INSIGHTS

**Baseado em:** Pesquisa de comparadores profissionais + Análise técnica  
**Última atualização:** 09/02/2026

---

## 🎯 VISÃO GERAL

Este documento lista melhorias **não urgentes** que podem aumentar performance, reduzir custos e melhorar UX.

**Todas as funcionalidades principais já funcionam.** Estas são otimizações incrementais.

---

## 📊 PRIORIZAÇÃO POR IMPACTO

| Melhoria | Impacto | Esforço | Prioridade | Quando |
|----------|---------|---------|-----------|--------|
| **Multiget** | 🟢 Alto | 🟡 Baixo | ⭐⭐⭐ | Curto prazo |
| **Cache básico** | 🟢 Alto | 🟡 Médio | ⭐⭐⭐ | Curto prazo |
| **Rate limiting** | 🟡 Médio | 🟡 Baixo | ⭐⭐ | Médio prazo |
| **Backoff exponencial** | 🟡 Médio | 🟢 Baixo | ⭐⭐ | Médio prazo |
| **Histórico de preços** | 🟡 Médio | 🟠 Alto | ⭐ | Longo prazo |
| **Webhooks ML** | 🟡 Médio | 🟠 Alto | ⭐ | Longo prazo |
| **Certificação ML** | 🟢 Alto | 🔴 Muito alto | ⚠️ | Só se GMV > $10k/mês |
| **Proxies** | 🔵 Baixo | 🟠 Alto | ❌ | Evitar |
| **Scraping** | 🔵 Baixo | 🔴 Muito alto | ❌ | Evitar |

---

## 🚀 FASE 1: OTIMIZAÇÃO BÁSICA (1-2 SEMANAS)

### 1.1. Implementar Multiget

**Problema atual:**
```python
# Buscar 20 concorrentes = 20 requisições
for item_id in competitor_ids:
    detail = get_item_by_id(token, item_id)  # 1 request cada
```

**Solução:**
```python
# Buscar 20 concorrentes = 1 requisição
def get_multiple_items_optimized(access_token: str, item_ids: List[str]) -> List[dict]:
    """Busca até 20 itens de uma vez usando /items?ids=..."""
    if not item_ids:
        return []
    
    # API ML aceita até 20 IDs por vez
    chunks = [item_ids[i:i+20] for i in range(0, len(item_ids), 20)]
    all_items = []
    
    for chunk in chunks:
        ids_str = ",".join(chunk)
        params = {
            "ids": ids_str,
            "attributes": "id,price,title,sold_quantity,permalink,thumbnail"  # Reduz payload
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(f"{ML_API}/items", headers=headers, params=params, timeout=15)
        
        if resp.status_code == 200:
            raw = resp.json()  # [{code: 200, body: {...}}, ...]
            for obj in raw:
                if obj.get("code") == 200 and "body" in obj:
                    all_items.append(obj["body"])
        
    return all_items
```

**Impacto:**
- ✅ **20x mais rápido** para listar concorrentes
- ✅ **90% menos requisições** (economia de rate limit)
- ✅ **Menor payload** com seleção de campos

**Onde aplicar:**
- `/api/ml/competitors` (GET) - listar concorrentes cadastrados

---

### 1.2. Cache em Memória

**Problema atual:**
```python
# Toda vez que lista concorrentes, busca na API ML (lento)
for r in rows:
    detail = get_item_by_id(token, r.item_id)  # API call
```

**Solução:**
```python
from datetime import datetime, timedelta

# Cache global (ou usar Redis em produção)
_items_cache = {}

def get_item_cached(access_token: str, item_id: str, ttl_seconds: int = 7200):
    """Busca item com cache de 2 horas (padrão)."""
    now = datetime.utcnow()
    cache_key = f"item:{item_id}"
    
    # Verifica cache
    if cache_key in _items_cache:
        cached = _items_cache[cache_key]
        if cached["expires_at"] > now:
            return cached["data"]  # Usa cache ✅
    
    # Cache expirado ou não existe, busca na API
    item = get_item_by_id(access_token, item_id)
    
    # Armazena no cache (apenas se sucesso)
    if item and not item.get("error"):
        _items_cache[cache_key] = {
            "data": item,
            "expires_at": now + timedelta(seconds=ttl_seconds)
        }
    
    return item
```

**TTL recomendado:**
- Título, categoria: 24 horas (raramente muda)
- Preço, estoque: 2-4 horas (pode mudar)
- Vendidos: 1 hora (atualiza frequentemente)

**Impacto:**
- ✅ **80% menos requisições** à API ML
- ✅ **3x mais rápido** para usuário
- ✅ **Reduz rate limit** significativamente

---

### 1.3. Seleção de Campos

**Problema atual:**
```python
# Retorna ~5KB por item (inclui tudo: imagens, variações, etc.)
GET /items/MLB123
```

**Solução:**
```python
# Retorna ~500B (apenas o necessário)
GET /items/MLB123?attributes=id,price,title,sold_quantity,permalink,thumbnail
```

**Implementação:**
```python
def get_item_by_id(access_token, item_id, attributes=None):
    params = {}
    if attributes:
        params["attributes"] = ",".join(attributes)
    
    resp = requests.get(f"{ML_API}/items/{item_id}", 
                       headers=headers, 
                       params=params,  # ✅ Adiciona seleção
                       timeout=15)
```

**Impacto:**
- ✅ **10x menos dados** transferidos
- ✅ **Resposta 2x mais rápida**
- ✅ **Economia de banda**

---

## ⚙️ FASE 2: CONFIABILIDADE (1-3 MESES)

### 2.1. Rate Limiting com Token Bucket

**Problema:** Sem controle de quantas requisições fazemos à API ML.

**Solução:**
```python
class TokenBucket:
    """Limita requisições à API ML."""
    def __init__(self, capacity=100, refill_rate=10):
        self.capacity = capacity  # máx 100 tokens
        self.tokens = capacity
        self.refill_rate = refill_rate  # +10 tokens/segundo
        self.last_refill = datetime.utcnow()
    
    def consume(self, tokens=1):
        """Tenta consumir N tokens. Retorna True se OK."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False  # Rate limit atingido
    
    def _refill(self):
        """Adiciona tokens ao longo do tempo."""
        now = datetime.utcnow()
        elapsed = (now - self.last_refill).total_seconds()
        tokens_to_add = int(elapsed * self.refill_rate)
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

# Uso global
ml_rate_limiter = TokenBucket(capacity=100, refill_rate=10)

def safe_ml_request(url, headers):
    if not ml_rate_limiter.consume():
        raise HTTPException(429, "Rate limit interno. Aguarde alguns segundos.")
    return requests.get(url, headers=headers, timeout=15)
```

**Impacto:**
- ✅ Evita bloqueio da API ML
- ✅ Distribui requisições ao longo do tempo
- ✅ Permite bursts controlados

---

### 2.2. Backoff Exponencial para 429

**Problema:** Se ML retornar 429 (Too Many Requests), falhamos imediatamente.

**Solução:**
```python
def fetch_with_retry(url, headers, max_retries=3):
    """Tenta requisição com retry exponencial."""
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            return resp.json()
        
        elif resp.status_code == 429:
            # Respeita Retry-After se fornecido
            retry_after = int(resp.headers.get('Retry-After', 2 ** attempt))
            _log.warning(f"Rate limit 429, aguardando {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        else:
            # Outro erro, não retry
            raise Exception(f"Erro {resp.status_code}")
    
    raise Exception("Max retries atingido")
```

**Impacto:**
- ✅ Recuperação automática de rate limit
- ✅ Menos erros para o usuário
- ✅ Melhor UX

---

### 2.3. Circuit Breaker

**Problema:** Se API ML estiver instável, continuamos tentando (desperdiça recursos).

**Solução:**
```python
class CircuitBreaker:
    """Para requisições se API está falhando consistentemente."""
    def __init__(self, threshold=5, timeout=60):
        self.threshold = threshold  # Erros consecutivos para abrir
        self.timeout = timeout  # Segundos até tentar novamente
        self.failures = 0
        self.opened_at = None
        self.state = "closed"  # closed | open | half-open
    
    def call(self, func, *args, **kwargs):
        if self.state == "open":
            # Verifica se pode tentar novamente
            if datetime.utcnow() > self.opened_at + timedelta(seconds=self.timeout):
                self.state = "half-open"  # Tentativa única
            else:
                raise Exception("Circuit breaker aberto. API ML temporariamente indisponível.")
        
        try:
            result = func(*args, **kwargs)
            self.failures = 0
            self.state = "closed"
            return result
        except Exception as e:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "open"
                self.opened_at = datetime.utcnow()
                _log.error(f"Circuit breaker aberto após {self.failures} falhas")
            raise e
```

**Impacto:**
- ✅ Evita sobrecarga quando API ML está fora
- ✅ Recuperação automática
- ✅ Mensagem clara ao usuário

---

## 📈 FASE 3: ESCALABILIDADE (6+ MESES)

### 3.1. Histórico de Preços

**Problema:** Não sabemos como o preço dos concorrentes mudou ao longo do tempo.

**Solução:**
```python
class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    item_id = Column(String(32), nullable=False, index=True)
    price = Column(Float, nullable=False)
    sold_quantity = Column(Integer, nullable=True)
    available_quantity = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

# Job periódico (a cada 4h)
def record_competitor_prices():
    """Registra preço atual de todos os concorrentes."""
    db = SessionLocal()
    items = db.query(CompetitorItem).all()
    for item in items:
        detail = get_item_cached(token, item.item_id)
        if detail and not detail.get("error"):
            db.add(PriceHistory(
                item_id=item.item_id,
                price=detail.get("price"),
                sold_quantity=detail.get("sold_quantity"),
                available_quantity=detail.get("available_quantity")
            ))
    db.commit()
```

**Impacto:**
- ✅ Análise de tendências (preço subindo/caindo)
- ✅ Alertas de mudança de preço
- ✅ Gráficos de histórico

---

### 3.2. Atualização Automática (Cron Job)

**Problema:** Dados de concorrentes só atualizam quando usuário acessa.

**Solução:**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', hours=4)
def update_all_competitors():
    """Atualiza dados de todos os concorrentes a cada 4h."""
    db = SessionLocal()
    items = db.query(CompetitorItem).all()
    
    # Agrupa por usuário para usar token correto
    by_user = {}
    for item in items:
        if item.user_id not in by_user:
            by_user[item.user_id] = []
        by_user[item.user_id].append(item.item_id)
    
    for user_id, item_ids in by_user.items():
        user = db.query(User).get(user_id)
        token = get_valid_ml_token(user)
        if not token:
            continue
        
        # Usa Multiget (até 20 por vez)
        items_data = get_multiple_items_optimized(token.access_token, item_ids)
        
        # Registra histórico
        for item_data in items_data:
            db.add(PriceHistory(
                item_id=item_data["id"],
                price=item_data.get("price"),
                sold_quantity=item_data.get("sold_quantity")
            ))
    
    db.commit()
    _log.info(f"Atualização automática: {len(items)} concorrentes atualizados")

# Inicia scheduler no startup
scheduler.start()
```

**Impacto:**
- ✅ Dados sempre atualizados
- ✅ Usuário vê informações recentes sem esperar
- ✅ Histórico automático

---

### 3.3. Cache Persistente (Redis)

**Problema:** Cache em memória se perde quando backend reinicia.

**Solução:**
```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_item_redis_cached(access_token, item_id, ttl=7200):
    """Cache com Redis (persiste entre restarts)."""
    cache_key = f"ml:item:{item_id}"
    
    # Verifica cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Busca na API
    item = get_item_by_id(access_token, item_id)
    
    # Armazena (apenas se sucesso)
    if item and not item.get("error"):
        redis_client.setex(cache_key, ttl, json.dumps(item))
    
    return item
```

**Impacto:**
- ✅ Cache sobrevive a restarts
- ✅ Compartilhado entre instâncias (horizontal scaling)
- ✅ TTL automático (Redis gerencia expiração)

**Custo:**
- Railway Redis: ~$5/mês

---

## 🎓 FASE 4: AVANÇADO (APENAS SE NECESSÁRIO)

### 4.1. Certificação ML

**Quando considerar:**
- GMV mensal > $10k (requisito mínimo)
- Precisa de SLA de suporte
- Busca pública bloqueada (403 persistente)

**Níveis:**
| Nível | GMV/mês | Requisitos | Benefícios |
|-------|---------|-----------|------------|
| Certified | $10k | Segurança 65% | Suporte via ticket |
| Silver | $100k | Segurança 80% | Listagem App-Store |
| Gold | $1M | Segurança 90% | SLA reduzido (10 dias) |
| Platinum | $10M | Segurança 95% | Wishlist de recursos |

**Nosso caso:**
- ⚠️ **Não recomendado agora** (escala pequena)
- ✅ API sem certificação é suficiente
- ✅ Adicionar por link/ID funciona perfeitamente

---

### 4.2. Proxies (NÃO RECOMENDADO)

**Quando usar:**
- Bloqueio persistente por IP
- Necessário scraping (não nosso caso)
- Geo-targeting (não nosso caso)

**Custo:**
- Proxies residenciais: $20-100/mês (Oxylabs, Bright Data)
- Rotação de IP: $49/mês (ScraperAPI)

**Nosso caso:**
- ❌ **Não necessário**
- API oficial funciona sem proxies
- Economia: $20-100/mês

---

### 4.3. Scraping (ÚLTIMO RECURSO)

**Quando usar:**
- Dados não disponíveis via API
- Certificação ML impossível
- Necessário em tempo real absoluto

**Riscos:**
- ❌ Bloqueio de IP/conta
- ❌ Violação de termos de uso
- ❌ Manutenção constante (HTML muda)
- ❌ CAPTCHA e anti-bot
- ❌ Custo alto (proxies + desenvolvimento)

**Nosso caso:**
- ❌ **Evitar completamente**
- API oficial atende todas as necessidades
- Adicionar por ID/link funciona sem scraping

---

## 📊 COMPARAÇÃO DE ABORDAGENS

| Abordagem | Custo/mês | Confiabilidade | Manutenção | Legal | Nossa nota |
|-----------|-----------|----------------|-----------|-------|-----------|
| **API oficial** | $0 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ |
| **API + Multiget** | $0 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ |
| **API + Cache** | $0-5 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐ |
| **Certificação ML** | $0* | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐ |
| **Proxies** | $20-100 | ⭐⭐⭐ | ⭐⭐ | ⚠️ | ⭐ |
| **Scraping** | $50-200 | ⭐⭐ | ⭐ | ❌ | ❌ |

**\*Certificação requer GMV $10k+/mês**

**Recomendação:** API oficial + Multiget + Cache.

---

## 🧪 TESTES ANTES DE IMPLEMENTAR

### Antes de Multiget:
```bash
# Medir tempo atual
time curl "https://mercadoinsights.online/api/ml/competitors" \
  -H "Authorization: Bearer TOKEN"

# Esperado: ~5-10s para 10 concorrentes
```

### Depois de Multiget:
```bash
# Medir tempo otimizado
time curl "https://mercadoinsights.online/api/ml/competitors" \
  -H "Authorization: Bearer TOKEN"

# Esperado: <1s para 10 concorrentes
```

---

## 📚 REFERÊNCIAS TÉCNICAS

### Artigos e Guias
- [ML API Best Practices](https://developers.mercadolivre.com.br/pt_br/boas-praticas-de-apis)
- [Rate Limiting Strategies](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
- [Cache Invalidation Patterns](https://martinfowler.com/bliki/TwoHardThings.html)

### Ferramentas
- [APScheduler](https://apscheduler.readthedocs.io/) - Cron jobs em Python
- [Redis](https://redis.io/) - Cache persistente
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)

---

## ✅ CONCLUSÃO

### Nossa estratégia (API oficial + ID/link) é sólida ✓

**Validado por:**
- ✅ Comparadores profissionais usam a mesma abordagem
- ✅ Escala atual não justifica scraping
- ✅ API ML atende nossas necessidades

**Próximas otimizações:**
1. **Multiget** (maior impacto, baixo esforço) ← PRIORIDADE
2. **Cache** (reduz custos, melhora UX)
3. **Rate limiting** (evita bloqueio)

**Evitar:**
- ❌ Scraping (risco, custo, manutenção)
- ❌ Proxies (custo desnecessário)
- ⚠️ Certificação ML (só se GMV > $10k/mês)

---

**🚀 Implemente as melhorias da Fase 1 nas próximas 1-2 semanas.**

Ver código de exemplo completo em: `ESTRATEGIA_CONCORRENCIA.md`
