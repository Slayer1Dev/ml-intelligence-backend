# 🔧 CONFIGURAÇÃO MERCADO LIVRE - PASSO A PASSO

## 📋 Problema Identificado

As credenciais do Mercado Livre **NÃO ESTÃO CONFIGURADAS** no arquivo `.env`, causando falha em todas as integrações.

---

## ✅ SOLUÇÃO: Adicionar Credenciais no .env

### 1. Obter Credenciais no Mercado Livre

Acesse o [Portal de Desenvolvedores do Mercado Livre](https://developers.mercadolivre.com.br/apps/home):

1. Faça login com sua conta vendedor
2. Clique em **"Criar aplicação"** ou selecione uma existente
3. Anote os seguintes dados:
   - **App ID** (Client ID)
   - **Secret Key** (Client Secret)
4. Configure a **URL de Redirect** (Redirect URI):
   - Em desenvolvimento: `http://localhost:8000/frontend/callback-ml.html`
   - Em produção: `https://seu-dominio.com/frontend/callback-ml.html`

---

### 2. Adicionar no Arquivo .env

Abra o arquivo `.env` na raiz do projeto e adicione:

```env
# Mercado Livre - Integração OAuth
ML_APP_ID=SEU_APP_ID_AQUI
ML_SECRET=SUA_SECRET_KEY_AQUI
ML_REDIRECT_URI=http://localhost:8000/frontend/callback-ml.html
```

**Exemplo com dados fictícios:**

```env
# Mercado Livre - Integração OAuth
ML_APP_ID=1234567890123456
ML_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
ML_REDIRECT_URI=http://localhost:8000/frontend/callback-ml.html
```

---

### 3. Arquivo .env Completo (Exemplo)

```env
# Clerk - Autenticação
CLERK_PUBLISHABLE_KEY=pk_test_ZW5qb3llZC1wZXJjaC0zOS5jbGVyay5hY2NvdW50cy5kZXYk
CLERK_SECRET_KEY=sk_test_VW3SuqqNvDDxOfvztyUQ7eQ6sIFcWgSRT2bdndmrUB
CLERK_FRONTEND_API=https://enjoyed-perch-39.clerk.accounts.dev
CLERK_JWKS_URL=https://enjoyed-perch-39.clerk.accounts.dev/.well-known/jwks.json

# Mercado Livre - Integração OAuth
ML_APP_ID=1234567890123456
ML_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz1234567890
ML_REDIRECT_URI=http://localhost:8000/frontend/callback-ml.html

# Admin / acesso total
ADMIN_EMAILS=lucasgabrielbarbosa84@gmail.com
```

---

### 4. Reiniciar o Backend

Após adicionar as credenciais, **reinicie o servidor backend**:

```bash
# Se estiver rodando localmente
uvicorn app.main:app --reload

# Ou no terminal onde o servidor está rodando
# Pressione Ctrl+C e rode novamente
```

---

## 🧪 Testar a Configuração

### Teste 1: Verificar URL de OAuth

Faça login no app e acesse a página de **Concorrentes** ou **Dashboard**. Clique em **"Conectar Mercado Livre"**.

**✅ Esperado:** Deve redirecionar para a página de autorização do Mercado Livre.  
**❌ Se falhar:** Verifique se `ML_APP_ID` e `ML_REDIRECT_URI` estão corretos.

### Teste 2: Callback OAuth

Após autorizar no Mercado Livre, você será redirecionado de volta para o app.

**✅ Esperado:** Mensagem de sucesso "Conta conectada".  
**❌ Se falhar:** Verifique se `ML_SECRET` está correto.

### Teste 3: Buscar Dados do ML

Acesse **Concorrentes** > **Adicionar concorrente por link ou ID**.

Cole um link ou ID de produto do ML (ex: `MLB1234567890`).

**✅ Esperado:** Produto é adicionado à lista.  
**❌ Se falhar:** Verifique logs em `logs/backend.log`.

---

## 🔍 Verificar Se Funcionou

### Comando de Teste (Python)

Rode este script para verificar se as variáveis estão carregadas:

```python
import os
from dotenv import load_dotenv

load_dotenv()

print("ML_APP_ID:", os.getenv("ML_APP_ID"))
print("ML_SECRET:", os.getenv("ML_SECRET")[:10] + "..." if os.getenv("ML_SECRET") else "AUSENTE")
print("ML_REDIRECT_URI:", os.getenv("ML_REDIRECT_URI"))
```

**✅ Esperado:**
```
ML_APP_ID: 1234567890123456
ML_SECRET: AbCdEfGhIj...
ML_REDIRECT_URI: http://localhost:8000/frontend/callback-ml.html
```

**❌ Se mostrar AUSENTE:** O arquivo `.env` não está sendo lido ou está em outro local.

---

## 🚨 Problemas Comuns

### 1. ".env não está sendo lido"

**Causa:** Arquivo está em outro diretório ou tem nome errado.

**Solução:**
- Verifique se o arquivo `.env` está na **raiz do projeto** (mesma pasta que `app/`)
- Certifique-se de que o nome é **`.env`** (não `.env.txt` ou `env`)

### 2. "Redirect URI inválida"

**Causa:** A URL configurada no portal do ML não bate com `ML_REDIRECT_URI` no `.env`.

**Solução:**
- No portal do ML, configure a mesma URL que está no `.env`
- Exemplo: Se `.env` tem `http://localhost:8000/frontend/callback-ml.html`, configure exatamente isso no portal

### 3. "Token não renova automaticamente"

**Causa:** `ML_SECRET` incorreto ou token expirou e refresh_token é inválido.

**Solução:**
- Desconecte e reconecte a conta ML no dashboard
- Verifique se `ML_SECRET` está correto no portal do ML

---

## 📚 Documentação Adicional

- [Guia OAuth Mercado Livre](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)
- [Criar App no ML](https://developers.mercadolivre.com.br/apps/home)
- [Scopes necessários](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao#Scopes): `offline_access read` (já configurado no código)

---

## ✅ Checklist de Configuração

- [ ] Criar/acessar app no portal do ML
- [ ] Copiar **App ID** e **Secret Key**
- [ ] Configurar **Redirect URI** no portal
- [ ] Adicionar `ML_APP_ID`, `ML_SECRET`, `ML_REDIRECT_URI` no `.env`
- [ ] Reiniciar servidor backend
- [ ] Testar conexão (botão "Conectar Mercado Livre")
- [ ] Verificar se token é salvo no banco de dados (`ml_tokens` table)
- [ ] Testar funcionalidades: busca, perguntas, concorrentes

---

**IMPORTANTE:** Nunca compartilhe suas credenciais (`ML_APP_ID` e `ML_SECRET`) publicamente. Adicione `.env` no `.gitignore` para não subir para o GitHub.

---

**Próximo passo:** Após configurar, execute os testes do `RELATORIO_BUGS.md` seção "🧪 TESTES SUGERIDOS".
