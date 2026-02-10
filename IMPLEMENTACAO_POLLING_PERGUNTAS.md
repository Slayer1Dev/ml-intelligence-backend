# 🔄 IMPLEMENTAÇÃO: POLLING AUTOMÁTICO DE PERGUNTAS

**Data:** 09/02/2026  
**Estratégia:** Polling a cada 30 minutos + ao abrir página + webhook

---

## 🎯 ESTRATÉGIA HÍBRIDA (RECOMENDADA)

### Por que Polling + Webhook?

**Webhook sozinho:**
- ✅ Tempo real (instantâneo)
- ❌ Pode falhar (rede, ML instável, app não recebe)
- ❌ Não pega perguntas antigas

**Polling sozinho:**
- ✅ Confiável (sempre busca)
- ✅ Pega perguntas perdidas
- ❌ Atraso (até 30min)
- ❌ Mais requisições à API

**Híbrido (Webhook + Polling):**
- ✅ Melhor dos dois mundos
- ✅ Tempo real via webhook
- ✅ Backup via polling (caso webhook falhe)
- ✅ Pega perguntas antigas ao abrir página

---

## 🔧 IMPLEMENTAÇÃO

### Opção 1: Polling no Backend (RECOMENDADA)

**Vantagens:**
- ✅ Roda mesmo com navegador fechado
- ✅ Centralizado (um cron para todos os usuários)
- ✅ Mais eficiente (usa Multiget)
- ✅ Não depende de frontend aberto

**Implementação:**

```python
# app/main.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Criar scheduler global
scheduler = BackgroundScheduler()

def sync_all_users_questions():
    """Busca perguntas não respondidas de TODOS os usuários a cada 30min."""
    logger.info("Iniciando polling automático de perguntas...")
    db = SessionLocal()
    try:
        # Busca todos os usuários com conta ML conectada
        tokens = db.query(MlToken).all()
        total_synced = 0
        
        for ml_token in tokens:
            user = db.query(User).filter(User.id == ml_token.user_id).first()
            if not user:
                continue
            
            # Valida/renova token
            token = get_valid_ml_token(user)
            if not token or not token.seller_id:
                logger.warning(f"Token inválido para user_id={user.id}, pulando...")
                continue
            
            # Busca perguntas não respondidas
            result = get_questions_search(
                token.access_token,
                seller_id=token.seller_id,
                limit=50,
                offset=0
            )
            
            if not result:
                continue
            
            questions = result.get("questions", [])
            synced = 0
            
            for q in questions:
                status = (q.get("status") or "").upper()
                if status in ("ANSWERED", "BANNED", "DELETED", "DISABLED"):
                    continue
                
                question_id = str(q.get("id") or "").strip()
                if not question_id:
                    continue
                
                # Verifica se já existe
                if db.query(PendingQuestion).filter(
                    PendingQuestion.user_id == user.id,
                    PendingQuestion.question_id == question_id
                ).first():
                    continue
                
                # Processa (adiciona à fila de aprovação)
                _process_ml_question_webhook(question_id, user.id)
                synced += 1
            
            total_synced += synced
            logger.info(f"Polling: user_id={user.id}, synced={synced} perguntas")
        
        logger.info(f"Polling automático concluído: {total_synced} perguntas sincronizadas no total")
    
    except Exception as e:
        logger.exception(f"Erro no polling de perguntas: {e}")
    finally:
        db.close()


# Iniciar scheduler no startup da aplicação
@app.on_event("startup")
def start_scheduler():
    """Inicia o scheduler de polling de perguntas."""
    # Polling a cada 30 minutos
    scheduler.add_job(
        sync_all_users_questions,
        trigger=IntervalTrigger(minutes=30),
        id='sync_questions_job',
        name='Sync ML Questions Every 30min',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler de polling de perguntas iniciado (30min)")


@app.on_event("shutdown")
def shutdown_scheduler():
    """Para o scheduler ao desligar."""
    scheduler.shutdown()
    logger.info("Scheduler de polling desligado")
```

**Dependência necessária:**

Adicione no `requirements.txt`:
```
APScheduler==3.10.4
```

Instale:
```bash
pip install APScheduler==3.10.4
```

---

### Opção 2: Polling no Frontend (COMPLEMENTAR)

**Vantagens:**
- ✅ Atualiza ao abrir página (primeira vez)
- ✅ Usuário vê perguntas novas imediatamente
- ✅ Não depende de backend rodando cron

**Implementação:**

```javascript
// frontend/perguntas-anuncios.html

let pollingInterval = null;

async function syncQuestions() {
  console.log('[Polling] Buscando perguntas no ML...');
  try {
    const res = await authFetch(`${API_BASE}/api/ml/questions/sync`, { 
      method: 'POST' 
    });
    const data = await res.json();
    
    if (res.ok && data.synced > 0) {
      console.log(`[Polling] ${data.synced} pergunta(s) nova(s) encontrada(s)`);
      loadPending();  // Recarrega lista
    }
  } catch (e) {
    console.error('[Polling] Erro ao sincronizar:', e);
  }
}

async function init() {
  await initClerkAuth({ ... });
  if (!window.ClerkAuth?.signedIn) return;
  
  // ... checkAccess, etc ...
  
  // 1. Busca imediatamente ao abrir página
  await syncQuestions();
  
  // 2. Polling a cada 30 minutos
  pollingInterval = setInterval(syncQuestions, 30 * 60 * 1000);  // 30min
  
  // Para o polling ao sair da página (economia de recursos)
  window.addEventListener('beforeunload', () => {
    if (pollingInterval) clearInterval(pollingInterval);
  });
}
```

---

### Opção 3: Híbrido (MELHOR ABORDAGEM) ✅

**Backend:** Cron a cada 30min (para todos os usuários)  
**Frontend:** Busca ao abrir página (para usuário específico)  
**Webhook:** Tempo real (quando funcionar)

**Resultado:**
- ✅ Perguntas chegam em tempo real (webhook)
- ✅ Se webhook falhar, polling pega em até 30min
- ✅ Ao abrir página, sempre atualizado
- ✅ Não perde perguntas

---

## 📊 COMPARAÇÃO DE ESTRATÉGIAS

| Estratégia | Latência | Confiabilidade | Requisições/dia | Custo |
|-----------|----------|----------------|-----------------|-------|
| **Webhook apenas** | 0s | ⭐⭐ | 0 | $0 |
| **Polling 30min** | 0-30min | ⭐⭐⭐⭐ | ~50/dia/usuário | Baixo |
| **Polling 5min** | 0-5min | ⭐⭐⭐⭐⭐ | ~300/dia/usuário | Médio |
| **Polling ao abrir** | 0s | ⭐⭐⭐ | ~10/dia/usuário | Muito baixo |
| **Híbrido (recomendado)** | 0-30min | ⭐⭐⭐⭐⭐ | ~60/dia/usuário | Baixo |

**Nossa recomendação:** **Híbrido** (webhook + polling 30min + abrir página)

---

## 🚀 IMPLEMENTAÇÃO PASSO A PASSO

### 1. Instalar Dependência

```bash
pip install APScheduler==3.10.4
```

Adicione no `requirements.txt`:
```
APScheduler==3.10.4
```

### 2. Adicionar Código no Backend

No arquivo `app/main.py`, adicione:

**No topo (imports):**
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
```

**Após a definição de `app = FastAPI(...)`:**
```python
# Scheduler global
scheduler = BackgroundScheduler()
```

**Função de polling** (adicione onde preferir, ex: após rotas de perguntas):
```python
def sync_all_users_questions():
    """Busca perguntas de todos os usuários a cada 30min."""
    # (código da Opção 1 acima)
```

**Eventos de startup/shutdown:**
```python
@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        sync_all_users_questions,
        trigger=IntervalTrigger(minutes=30),
        id='sync_questions_job',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Polling de perguntas iniciado (30min)")

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
```

### 3. Adicionar Polling no Frontend

No arquivo `frontend/perguntas-anuncios.html`, modifique a função `init()`:

**Adicione após `checkAccess()`:**
```javascript
async function init() {
  await initClerkAuth({ ... });
  if (!window.ClerkAuth?.signedIn) return;
  setupConectarMlButton();
  
  if (await checkAccess()) {
    // ... código existente ...
    
    // ✅ ADICIONE AQUI:
    // Busca perguntas ao abrir página
    console.log('[Polling] Buscando perguntas ao abrir página...');
    syncQuestionsQuietly();
    
    // Polling a cada 30 minutos
    setInterval(syncQuestionsQuietly, 30 * 60 * 1000);
  }
}

// ✅ ADICIONE ESTA FUNÇÃO:
async function syncQuestionsQuietly() {
  """Sincroniza perguntas sem mostrar alert."""
  try {
    const res = await authFetch(`${API_BASE}/api/ml/questions/sync`, { 
      method: 'POST' 
    });
    const data = await res.json();
    
    if (res.ok && data.synced > 0) {
      console.log(`[Polling] ${data.synced} pergunta(s) nova(s) sincronizada(s)`);
      loadPending();  // Atualiza lista automaticamente
    }
  } catch (e) {
    console.error('[Polling] Erro ao sincronizar:', e);
  }
}
```

---

## 🧪 TESTAR

### 1. Após deploy (backend com cron):

```bash
# Verificar logs (Railway ou local)
# Deve aparecer a cada 30min:
"Polling automático concluído: X perguntas sincronizadas"
```

### 2. Após deploy (frontend):

1. Abra: https://www.mercadoinsights.online/frontend/perguntas-anuncios.html
2. DevTools (F12) → Console
3. Deve aparecer:
   ```
   [Polling] Buscando perguntas ao abrir página...
   [Polling] 0 pergunta(s) nova(s) sincronizada(s)
   ```
4. Aguarde 30 minutos (ou force com botão "Buscar perguntas agora")
5. Console deve mostrar novo polling

---

## 📊 FLUXO COMPLETO (APÓS IMPLEMENTAÇÃO)

```
┌─────────────────────────────────────────────────────────────────┐
│ WEBHOOK (Tempo Real - se configurado)                           │
│ Comprador faz pergunta → ML envia webhook                       │
│ → Backend processa → Salva em PendingQuestion                   │
│ Latência: ~0-30s                                                 │
└─────────────────────────────────────────────────────────────────┘
                              OU (se webhook falhar)
┌─────────────────────────────────────────────────────────────────┐
│ POLLING BACKEND (A cada 30min - automático)                     │
│ Cron job → Busca perguntas de todos os usuários                 │
│ → Salva novas em PendingQuestion                                │
│ Latência: 0-30min                                                │
└─────────────────────────────────────────────────────────────────┘
                              +
┌─────────────────────────────────────────────────────────────────┐
│ POLLING FRONTEND (Ao abrir página)                              │
│ Usuário abre página de perguntas                                │
│ → Busca imediatamente → Atualiza lista                          │
│ → Polling a cada 30min enquanto página aberta                   │
│ Latência: 0s (primeira vez)                                      │
└─────────────────────────────────────────────────────────────────┘
                              +
┌─────────────────────────────────────────────────────────────────┐
│ MANUAL (Botão "Buscar perguntas agora")                         │
│ Usuário clica no botão                                          │
│ → Busca imediatamente → Atualiza lista                          │
│ Latência: 0s                                                     │
└─────────────────────────────────────────────────────────────────┘
```

**Resultado:** Perguntas SEMPRE chegam, mesmo se webhook falhar!

---

## ⚡ OTIMIZAÇÃO: POLLING INTELIGENTE

### Priorização por Atividade

```python
def get_polling_interval(user_id):
    """Retorna intervalo de polling baseado em atividade do usuário."""
    db = SessionLocal()
    
    # Conta perguntas recentes (últimas 24h)
    recent_questions = db.query(PendingQuestion).filter(
        PendingQuestion.user_id == user_id,
        PendingQuestion.created_at >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    if recent_questions > 10:
        return 15  # Alta atividade: polling a cada 15min
    elif recent_questions > 5:
        return 30  # Média atividade: 30min
    else:
        return 60  # Baixa atividade: 1 hora
```

**Impacto:**
- ✅ Vendedores ativos: updates mais frequentes
- ✅ Vendedores inativos: menos requisições (economia)

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### Backend:
- [ ] Instalar APScheduler (`pip install APScheduler==3.10.4`)
- [ ] Adicionar imports no `main.py`
- [ ] Criar função `sync_all_users_questions()`
- [ ] Adicionar evento `@app.on_event("startup")`
- [ ] Adicionar evento `@app.on_event("shutdown")`
- [ ] Testar localmente (verificar logs a cada 30min)

### Frontend:
- [ ] Adicionar função `syncQuestionsQuietly()` em `perguntas-anuncios.html`
- [ ] Chamar ao abrir página (`init()`)
- [ ] Iniciar polling a cada 30min (`setInterval`)
- [ ] Testar no navegador (verificar console)

### Configuração ML:
- [ ] Ativar tópico "**Questions**" no portal ML
- [ ] Ativar permissão "**Publicação e sincronização**" (Leitura)
- [ ] Reconectar conta ML no Mercado Insights
- [ ] Testar webhook (fazer pergunta de teste)

---

## 🎯 RESULTADO ESPERADO

### Console (Frontend):
```
[Polling] Buscando perguntas ao abrir página...
[Polling] 0 pergunta(s) nova(s) sincronizada(s)

(30 minutos depois)
[Polling] Buscando perguntas...
[Polling] 1 pergunta(s) nova(s) sincronizada(s)
```

### Logs (Backend):
```
INFO | Polling de perguntas iniciado (30min)

(a cada 30min)
INFO | Iniciando polling automático de perguntas...
INFO | Polling: user_id=1, synced=2 perguntas
INFO | Polling automático concluído: 2 perguntas sincronizadas
```

### UI (Página de Perguntas):
- ✅ Perguntas aparecem automaticamente (sem precisar recarregar)
- ✅ Lista atualiza a cada 30min (ou ao clicar botão)
- ✅ Notificação visual quando novas perguntas chegam (opcional)

---

## 💡 MELHORIAS OPCIONAIS

### 1. Notificação Visual de Novas Perguntas

```javascript
function showNotification(count) {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed; top: 20px; right: 20px;
    background: #059669; color: white; padding: 1rem;
    border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 9999;
  `;
  notification.textContent = `${count} nova(s) pergunta(s) recebida(s)!`;
  document.body.appendChild(notification);
  
  // Remove após 5s
  setTimeout(() => notification.remove(), 5000);
}

async function syncQuestionsQuietly() {
  const res = await authFetch(`${API_BASE}/api/ml/questions/sync`, { method: 'POST' });
  const data = await res.json();
  
  if (res.ok && data.synced > 0) {
    console.log(`[Polling] ${data.synced} pergunta(s) nova(s)`);
    loadPending();
    showNotification(data.synced);  // ✅ Mostra notificação
  }
}
```

### 2. Badge com Contador

```javascript
// Mostra número de perguntas pendentes no menu
async function updatePendingBadge() {
  const res = await authFetch(`${API_BASE}/api/ml/questions/pending`);
  const items = await res.json();
  const count = items.length;
  
  // Atualiza badge no menu
  const link = document.querySelector('a[href="perguntas-anuncios.html"]');
  if (link && count > 0) {
    link.innerHTML = `Perguntas nos anúncios <span style="background:#dc2626;color:white;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.75rem;margin-left:0.5rem;">${count}</span>`;
  }
}
```

### 3. Ajuste Dinâmico de Intervalo

```javascript
let pollingInterval = 30 * 60 * 1000;  // Padrão: 30min

async function syncQuestionsQuietly() {
  const res = await authFetch(`${API_BASE}/api/ml/questions/sync`, { method: 'POST' });
  const data = await res.json();
  
  if (res.ok && data.synced > 5) {
    // Alta atividade: reduz intervalo para 15min
    pollingInterval = 15 * 60 * 1000;
    console.log('[Polling] Alta atividade detectada, intervalo reduzido para 15min');
  } else if (data.synced === 0) {
    // Sem perguntas: aumenta intervalo para 60min
    pollingInterval = 60 * 60 * 1000;
    console.log('[Polling] Nenhuma pergunta, intervalo aumentado para 60min');
  }
  
  // Reinicia intervalo
  clearInterval(pollingId);
  pollingId = setInterval(syncQuestionsQuietly, pollingInterval);
}
```

---

## ✅ BENEFÍCIOS DA IMPLEMENTAÇÃO

| Benefício | Antes | Depois |
|-----------|-------|--------|
| **Perguntas perdidas** | ❌ Sim (se webhook falhar) | ✅ Não (polling pega) |
| **Latência** | 0s (webhook) ou ∞ (sem backup) | 0-30min (pior caso) |
| **Confiabilidade** | ⭐⭐ (depende de webhook) | ⭐⭐⭐⭐⭐ (múltiplos backups) |
| **Requisições/dia** | 0 (webhook) | ~60 (polling) |
| **Manutenção** | Alta (se webhook quebrar) | Baixa (sempre funciona) |

---

## 🎯 PRÓXIMOS PASSOS

### 1. URGENTE: Corrigir Configuração App ML
Leia: **`PROBLEMA_CONFIGURACAO_ML.md`**

- [ ] Ativar "Publicação e sincronização" (Leitura)
- [ ] Ativar tópico "Questions"
- [ ] Reconectar conta ML

### 2. Implementar Polling
- [ ] Backend: Cron a cada 30min (Opção 1)
- [ ] Frontend: Ao abrir página (Opção 2)
- [ ] Testar (verificar logs)

### 3. Fazer Deploy
```bash
git add .
git commit -m "Add: Questions polling (30min + on page load)"
git push origin main
```

---

**🎉 Com polling + webhook, você NUNCA perderá uma pergunta!** 🚀
