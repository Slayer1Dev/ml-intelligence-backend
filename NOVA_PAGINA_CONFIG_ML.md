# ⚙️ NOVA PÁGINA: CONFIGURAÇÕES MERCADO LIVRE

**Criado em:** 09/02/2026  
**Arquivo:** `frontend/config-ml.html`  
**URL:** https://www.mercadoinsights.online/frontend/config-ml.html

---

## 🎯 O QUE FOI CRIADO

Uma página dedicada para **gerenciar conexão com o Mercado Livre** de forma robusta, com:

### ✅ Funcionalidades

1. **Status da Conexão**
   - Visual claro (conectado/desconectado)
   - Detalhes do token (seller_id, expiração, tempo restante)
   - Atualização automática a cada 30s

2. **Controles**
   - Botão "Conectar Mercado Livre"
   - Botão "Desconectar"
   - Botão "Atualizar Status"

3. **Diagnóstico Avançado**
   - Testa 4 endpoints da API ML
   - Verifica permissões (Items, Comunicações, etc.)
   - Mostra recomendações de correção
   - Identifica problemas específicos

4. **Teste de API**
   - Campo para testar busca de produto por ID
   - Mostra se token tem permissão
   - Exibe detalhes do produto (se encontrado)

5. **Logs de Debug**
   - Histórico de ações
   - Timestamps de todas as operações
   - Console visual (últimos 50 logs)
   - Botão para limpar logs

---

## 🔧 ENDPOINTS CRIADOS NO BACKEND

### 1. `DELETE /api/ml-disconnect`
Desconecta a conta ML (remove token do banco).

**Resposta de sucesso:**
```json
{
  "ok": true,
  "message": "Conta do Mercado Livre desconectada com sucesso."
}
```

### 2. `GET /api/ml-diagnostic`
Diagnóstico completo com testes de API.

**Resposta (conectado):**
```json
{
  "connected": true,
  "seller_id": "123456789",
  "expires_at": "2026-02-10T06:30:00",
  "created_at": "2026-02-09T18:00:00",
  "token_expired": false,
  "time_until_expiry_minutes": 45,
  "tests": {
    "Buscar dados do usuário (/users/me)": {
      "success": true,
      "message": "OK - Dados do usuário carregados"
    },
    "Buscar anúncios (/users/{id}/items/search)": {
      "success": false,
      "message": "Falhou - Sem permissão 'Publicação e sincronização'"
    },
    ...
  },
  "scopes": ["read", "offline_access"],
  "recommendations": [
    "⚠️ CRÍTICO: Ative permissão 'Publicação e sincronização' (Leitura) no portal ML."
  ]
}
```

**Resposta (desconectado):**
```json
{
  "connected": false,
  "message": "Nenhuma conta ML conectada.",
  "recommendations": [
    "Clique em 'Conectar Mercado Livre' para autorizar sua conta."
  ]
}
```

### 3. `GET /api/ml-test-item/{item_id}`
Testa busca de produto específico.

**Resposta (sucesso):**
```json
{
  "success": true,
  "item": {
    "id": "MLB123",
    "title": "Smartwatch...",
    "price": 499.00,
    "sold_quantity": 150,
    "status": "active",
    "permalink": "https://..."
  },
  "message": "Produto encontrado: Smartwatch..."
}
```

**Resposta (erro):**
```json
{
  "success": false,
  "error": true,
  "status_code": 403,
  "message": "Forbidden",
  "detail": "Falhou ao buscar item MLB123: Forbidden"
}
```

---

## 🧪 COMO USAR

### 1. Acessar a Página

https://www.mercadoinsights.online/frontend/config-ml.html

OU

Dashboard → Menu lateral → **"⚙️ Config. Mercado Livre"**

### 2. Verificar Status

A página carrega automaticamente e mostra:
- ✅ **Conectado:** Badge verde + detalhes do token
- ❌ **Desconectado:** Badge vermelho + mensagem

### 3. Conectar/Reconectar

1. Clique em **"Conectar Mercado Livre"**
2. Autorize no portal ML
3. Será redirecionado de volta
4. Status atualiza automaticamente

### 4. Desconectar

1. Clique em **"Desconectar"**
2. Confirme (popup)
3. Token é removido do banco
4. Status atualiza para "Desconectado"

### 5. Executar Diagnóstico

1. Clique em **"Executar Diagnóstico"**
2. Sistema testa 4 endpoints da API ML
3. Mostra resultados:
   - ✅ OK - Permissão ativa
   - ❌ Falhou - Sem permissão
4. Lista recomendações de correção

**Exemplo de resultado:**
```
✅ Buscar dados do usuário: OK
❌ Buscar anúncios: Falhou - Sem permissão 'Publicação e sincronização'
✅ Buscar perguntas: OK
❌ Buscar produto público: Erro 403

Recomendações:
💡 ⚠️ CRÍTICO: Ative permissão 'Publicação e sincronização' (Leitura) no portal ML.
```

### 6. Testar API com Produto Específico

1. Digite um ID de produto (ex: MLB4443868923)
2. Clique em **"Testar"**
3. Resultado:
   - ✅ Sucesso: Mostra título, preço, vendidos
   - ❌ Erro: Mostra mensagem específica (403, 404, etc.)

**Use isso para validar se permissões estão corretas!**

---

## 📊 EXEMPLO DE USO: TESTAR PERMISSÕES

### Cenário: Acabei de ativar permissão "Items" no portal ML

**Passos:**

1. Vá em **Config. Mercado Livre**
2. Clique em **"Desconectar"** (para remover token antigo)
3. Clique em **"Conectar Mercado Livre"** (para obter token novo com permissões)
4. Autorize no ML
5. Volte para Config. Mercado Livre
6. Clique em **"Executar Diagnóstico"**

**Resultado esperado:**
```
✅ Buscar dados do usuário: OK
✅ Buscar anúncios: OK - Permissão 'Items' ativa
✅ Buscar perguntas: OK
✅ Buscar produto público: OK

Recomendações:
✅ Tudo OK! Conexão e permissões estão corretas.
```

7. Teste com produto real:
   - Digite: MLB4443868923 (ou outro ID)
   - Clique "Testar"
   - Deve mostrar: ✅ "Produto encontrado: ..."

---

## 🎨 VISUAL DA PÁGINA

### Status Conectado (Verde):
```
┌──────────────────────────────────────────────────┐
│ Status da Conexão        [✅ Conectado]          │
│                                                   │
│ Seller ID: 123456789                             │
│ Token expira em: 45 minutos (verde)              │
│ Data de expiração: 10/02/2026 06:30             │
│ Conectado desde: 09/02/2026 18:00                │
│                                                   │
│ [Desconectar] [Atualizar Status]                 │
└──────────────────────────────────────────────────┘
```

### Status Desconectado (Vermelho):
```
┌──────────────────────────────────────────────────┐
│ Status da Conexão     [❌ Desconectado]          │
│                                                   │
│ Nenhuma conta do Mercado Livre conectada.        │
│                                                   │
│ [Conectar Mercado Livre] [Atualizar Status]      │
└──────────────────────────────────────────────────┘
```

### Token Expirando (Amarelo):
```
⏰ Token próximo de expirar
O token será renovado automaticamente. Se houver problemas, 
reconecte manualmente.
```

### Token Expirado (Vermelho):
```
⚠️ Token expirado!
Reconecte sua conta clicando em "Conectar Mercado Livre" acima.
```

---

## 💡 CASOS DE USO

### 1. Debugar "Acesso negado"

**Problema:** Adicionar concorrente retorna "Acesso negado".

**Solução:**
1. Vá em **Config. Mercado Livre**
2. Clique em **"Executar Diagnóstico"**
3. Veja o resultado:
   ```
   ❌ Buscar anúncios: Falhou - Sem permissão 'Publicação e sincronização'
   
   Recomendações:
   💡 Ative permissão 'Publicação e sincronização' (Leitura) no portal ML.
   ```
4. Corrija no portal ML
5. Clique em **"Desconectar"** + **"Conectar"** (atualiza permissões)
6. Execute diagnóstico novamente
7. Deve mostrar: ✅ Tudo OK!

### 2. Testar se produto existe

**Problema:** Não sei se o erro é do sistema ou se o produto não existe.

**Solução:**
1. Vá em **Config. Mercado Livre**
2. Cole o ID no campo "Testar API"
3. Clique em **"Testar"**
4. Resultado:
   - ✅ Produto encontrado → Sistema OK, produto existe
   - ❌ 404 Not Found → Produto não existe ou foi removido
   - ❌ 403 Forbidden → Sem permissão, corrija no portal ML

### 3. Validar Token Após Reconexão

**Problema:** Reconectei mas ainda vejo erros.

**Solução:**
1. Vá em **Config. Mercado Livre**
2. Verifique **"Token expira em":**
   - Se verde (>1h): Token OK
   - Se amarelo (<1h): Próximo de expirar, mas OK
   - Se vermelho (expirado): Reconecte
3. Execute **"Diagnóstico"** para validar permissões

### 4. Monitorar Logs em Tempo Real

**Problema:** Quero ver o que está acontecendo nos bastidores.

**Solução:**
1. Vá em **Config. Mercado Livre**
2. Seção "Logs de Debug" mostra:
   ```
   [09/02/2026 23:45:30] ℹ️ Página de configurações ML carregada
   [09/02/2026 23:45:31] ℹ️ Carregando status da conexão...
   [09/02/2026 23:45:32] ✅ Status carregado: Conectado
   [09/02/2026 23:46:00] ℹ️ Iniciando diagnóstico avançado...
   [09/02/2026 23:46:03] ✅ Diagnóstico concluído
   ```

---

## 🔄 FLUXO DE RECONEXÃO ROBUSTA

### Antes (sem página de config):
```
1. Usuário vê erro "Acesso negado"
2. Não sabe se é token expirado, permissão faltando ou bug
3. Tenta desconectar (mas não tem botão específico)
4. Precisa ir no dashboard → conectar → esperar
5. Não sabe se funcionou
```

### Depois (com página de config):
```
1. Usuário vê erro "Acesso negado"
2. Vai em "Config. Mercado Livre"
3. Vê status: "Conectado, token expira em X minutos"
4. Clica "Executar Diagnóstico"
5. Vê: "❌ Buscar anúncios: Sem permissão"
6. Corrige no portal ML
7. Clica "Desconectar" + "Conectar"
8. Diagnóstico mostra: "✅ Tudo OK!"
9. Testa com produto real: "✅ Produto encontrado"
10. Problema resolvido!
```

**Resultado:** Muito mais fácil de debugar e validar! 🎉

---

## 📋 CHECKLIST DE VALIDAÇÃO

Após fazer deploy:

- [ ] Acessar https://www.mercadoinsights.online/frontend/config-ml.html
- [ ] Ver status da conexão (conectado/desconectado)
- [ ] Executar diagnóstico
- [ ] Ver quais testes passaram/falharam
- [ ] Testar busca de produto (ex: MLB4443868923)
- [ ] Desconectar e reconectar
- [ ] Verificar logs de debug

---

## 🚀 DEPLOY

### Arquivos Modificados:

**Novos:**
- `frontend/config-ml.html` (página de configurações)

**Modificados:**
- `app/main.py` (3 novos endpoints)
- 8 arquivos HTML (link no menu adicionado)

### Comandos:

```bash
git add .
git commit -m "Add: ML config page with disconnect, diagnostic and API testing"
git push origin main
```

---

## 📊 ENDPOINTS CRIADOS

| Método | Rota | Descrição |
|--------|------|-----------|
| `DELETE` | `/api/ml-disconnect` | Desconecta conta ML |
| `GET` | `/api/ml-diagnostic` | Diagnóstico completo |
| `GET` | `/api/ml-test-item/{id}` | Testa busca de produto |

---

## 🎯 BENEFÍCIOS

### Para Você (Desenvolvedor):
- ✅ Diagnóstico preciso de problemas
- ✅ Testes rápidos de permissões
- ✅ Logs visuais de debug
- ✅ Validação de configurações

### Para o Usuário Final:
- ✅ Controle total da conexão ML
- ✅ Entende se está conectado/desconectado
- ✅ Vê quando token expira
- ✅ Pode reconectar facilmente

---

## 💡 DICAS DE USO

### Sempre que mudar permissões no portal ML:

1. Vá em **Config. Mercado Livre**
2. **Desconecte**
3. **Conecte** (para obter token com novas permissões)
4. **Execute diagnóstico** (para validar)

### Para debugar qualquer erro de ML:

1. Vá em **Config. Mercado Livre**
2. **Execute diagnóstico**
3. Veja qual teste falhou
4. Siga as recomendações

### Para validar setup inicial:

1. Conecte conta ML
2. **Execute diagnóstico**
3. Todos os 4 testes devem passar ✅
4. Se algum falhar, corrija no portal ML

---

## 🎉 RESULTADO

Agora você tem **controle total** da conexão com o Mercado Livre!

**Não precisa mais:**
- ❌ Adivinhar se está conectado
- ❌ Procurar onde desconectar
- ❌ Debugar às cegas

**Pode fazer:**
- ✅ Ver status em tempo real
- ✅ Desconectar/reconectar facilmente
- ✅ Diagnosticar problemas precisamente
- ✅ Testar permissões rapidamente

---

**🚀 Faça deploy e teste a nova página!**
