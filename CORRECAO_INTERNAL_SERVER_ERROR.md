# 🔧 CORREÇÃO: INTERNAL SERVER ERROR NA CONFIG ML

**Data:** 09/02/2026 23:40  
**Problema:** Página de Config ML retorna "Internal Server Error"

---

## 🐛 PROBLEMA IDENTIFICADO

### Sintoma

**Logs mostram:**
```
❌ Diagnóstico falhou: Internal Server Error
❌ Erro ao carregar status: Internal Server Error
```

**Causa:**
- Import de `get_user_info` estava **FALTANDO** no `main.py`
- Código chamava `get_user_info(token.access_token)` mas função não estava importada
- Python lança `NameError` → FastAPI retorna 500 Internal Server Error

---

## ✅ CORREÇÃO APLICADA

### Arquivo: `app/main.py` (linha ~107)

**Antes:**
```python
from app.services.ml_api import (
    exchange_code_for_tokens,
    get_auth_url,
    refresh_access_token,
    get_user_items,  # ❌ get_user_info faltando
    ...
)
```

**Depois:**
```python
from app.services.ml_api import (
    exchange_code_for_tokens,
    get_auth_url,
    refresh_access_token,
    get_user_info,  # ✅ Adicionado
    get_user_items,
    ...
)
```

---

## 🚀 VOCÊ PRECISA FAZER DEPLOY!

O erro persiste no site porque você **NÃO FEZ PUSH** da correção.

### Comando:

```bash
cd "c:\Users\rebec\Documents\ml-intelligence-backend"

git add .

git commit -m "Fix: Add missing get_user_info import for ml-diagnostic endpoint"

git push origin main
```

**Aguarde 2-3 minutos** → **Limpe cache (Ctrl+Shift+R)**

---

## 🧪 TESTAR APÓS DEPLOY

### 1. Acesse Config ML

https://www.mercadoinsights.online/frontend/config-ml.html

### 2. Aguarde Carregar

**Esperado agora:**
- ✅ Status carrega corretamente (conectado/desconectado)
- ✅ Se conectado: Mostra seller_id, expiração, etc.
- ✅ Se desconectado: Mostra mensagem clara

### 3. Execute Diagnóstico

Clique em **"Executar Diagnóstico"**

**Esperado:**
```
✅ Buscar dados do usuário: OK
❌ Buscar anúncios: Falhou - Sem permissão 'Publicação e sincronização'
✅ Buscar perguntas: OK
❌ Buscar produto público: Erro 403

Recomendações:
💡 ⚠️ CRÍTICO: Ative permissão 'Publicação e sincronização' (Leitura) no portal ML.
```

**NÃO DEVE mostrar:**
```
❌ Erro: Internal Server Error
```

---

## 📊 POR QUE DASHBOARD MOSTRA "CONECTADO" MAS CONFIG MOSTRA "DESCONECTADO"?

### Dashboard (antes da correção)

Usa endpoint: `/api/ml-status`

```python
@app.get("/api/ml-status")
def ml_status(user: User = Depends(get_current_user)):
    token = get_valid_ml_token(user)
    return {"connected": token is not None}  # ✅ Funciona
```

Este endpoint é simples e **não dá erro**.

### Config ML (antes da correção)

Usa endpoint: `/api/ml-diagnostic`

```python
@app.get("/api/ml-diagnostic")
def ml_diagnostic(user: User = Depends(get_current_user)):
    # ...
    user_info = get_user_info(token.access_token)  # ❌ NameError!
    # ...
```

Este endpoint é complexo e **dava erro** por falta de import.

**Quando dá erro 500:**
- Frontend recebe erro
- Interpreta como "não conseguiu carregar"
- Mostra "Desconectado" como fallback

---

## ✅ APÓS O DEPLOY

Ambos os endpoints funcionarão corretamente:

| Endpoint | Status | Uso |
|----------|--------|-----|
| `/api/ml-status` | ✅ Funcionando | Dashboard, páginas gerais |
| `/api/ml-diagnostic` | ✅ **CORRIGIDO** | Config ML (diagnóstico avançado) |

**Resultado:** Status consistente em todas as páginas!

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ **Fazer deploy** (comando acima)
2. ✅ **Limpar cache** (Ctrl+Shift+R)
3. ✅ **Testar Config ML** (deve carregar sem erro)
4. ✅ **Executar diagnóstico** (deve mostrar testes)
5. ⚠️ **Corrigir permissões no portal ML** (se diagnóstico mostrar falhas)
6. ✅ **Reconectar** (após corrigir permissões)
7. ✅ **Diagnóstico novamente** (deve mostrar ✅ Tudo OK)

---

**🚀 Deploy corrigido! Teste e me avise se funcionar!**
