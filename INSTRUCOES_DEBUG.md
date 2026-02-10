# 🔍 INSTRUÇÕES DE DEBUG - PESQUISA DE CONCORRÊNCIA

## 📍 Onde Adicionar Console.log no Frontend

### Arquivo: `frontend/concorrentes.html`

#### Local 1: Antes de fazer a requisição (linha ~344)
```javascript
async function doSearch(offset = 0) {
  const q = document.getElementById('search-input').value.trim();
  const sort = document.getElementById('sort-select').value || undefined;
  
  // ✅ ADICIONE AQUI:
  console.log('[DEBUG] Iniciando busca:', { q, sort, offset, limit });
  
  const btn = document.getElementById('btn-search');
  btn.disabled = true;
  // ... resto do código
```

#### Local 2: Após receber a resposta (linha ~347)
```javascript
try {
  let url = `${API_BASE}/api/ml/search?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`;
  if (sort) url += '&sort=' + encodeURIComponent(sort);
  
  // ✅ ADICIONE AQUI:
  console.log('[DEBUG] URL da requisição:', url);
  
  const res = await authFetch(url);
  
  // ✅ ADICIONE AQUI (logo após o fetch):
  console.log('[DEBUG] Status da resposta:', res.status);
  console.log('[DEBUG] Headers da resposta:', Object.fromEntries(res.headers.entries()));
  
  if (res.status === 403) {
    const err = await res.json().catch(() => ({}));
    
    // ✅ ADICIONE AQUI:
    console.error('[DEBUG] Erro 403 recebido:', err);
    
    if (err.detail === 'ml_not_connected') {
      // ...
```

#### Local 3: No bloco de erro (linha ~419)
```javascript
} catch (e) {
  // ✅ ADICIONE AQUI:
  console.error('[DEBUG] Exceção capturada:', {
    message: e.message,
    stack: e.stack,
    error: e
  });
  
  document.getElementById('results-list').innerHTML = 
    '<p style="color: red;">' + (e.message || 'Erro ao buscar. Tente novamente.') + '</p>';
}
```

---

## 🖥️ Como Executar os Testes

### Teste 1: Script Python (Backend)
```bash
# No terminal, na raiz do projeto:
python test_ml_search.py
```

**O que esperar:**
- ✅ Se retornar **200 OK**: A API ML funciona! Problema está no código.
- ❌ Se retornar **403 Forbidden**: App não certificado (esperado, use link/ID).
- ❌ Se retornar **outro erro**: Veja a mensagem específica.

### Teste 2: Frontend (Navegador)

1. Adicione os `console.log` acima no `concorrentes.html`
2. Abra a página de Concorrentes no navegador
3. Abra o **DevTools** (F12) → Aba **Console**
4. Digite um termo de busca e clique em **Buscar**
5. Observe os logs:

**Logs esperados:**
```
[DEBUG] Iniciando busca: {q: "fone bluetooth", sort: undefined, offset: 0, limit: 20}
[DEBUG] URL da requisição: http://localhost:8000/api/ml/search?q=fone%20bluetooth&limit=20&offset=0
[DEBUG] Status da resposta: 503
[DEBUG] Headers da resposta: {content-type: "application/json", ...}
[DEBUG] Erro capturado: {detail: "A busca do Mercado Livre está restrita..."}
```

---

## 📊 Interpretação dos Resultados

### Se o script Python retorna 200 OK:
✅ **A API ML funciona**  
→ Problema: O código não está passando os dados corretamente  
→ Correção: Verificar lógica de parsing da resposta

### Se o script Python retorna 403:
⚠️ **App não é certificado** (esperado)  
→ Não é bug, é limitação da API ML  
→ Correção: Melhorar mensagem de erro para o usuário

### Se o script Python retorna 429:
⚠️ **Rate limit atingido**  
→ Muitas requisições em pouco tempo  
→ Correção: Implementar retry com backoff

### Se o frontend mostra status 503:
❌ **Backend não conseguiu buscar**  
→ Problema: Erro da API ML não foi tratado corretamente  
→ Correção: Passar detalhes do erro real ao frontend

---

## 🎯 Próximo Passo

Após executar os testes e confirmar qual é o erro real:

1. **Se 403 (app não certificado):** Aplicar correção para melhorar mensagem
2. **Se outro erro:** Aplicar correção para passar detalhes ao frontend
3. Validar que a correção não quebra autenticação

Execute os testes e me informe os resultados para eu aplicar a correção apropriada.
