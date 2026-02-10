# 📚 ÍNDICE DE DOCUMENTAÇÃO - MERCADO INSIGHTS

**Sistema:** Mercado Insights  
**Site:** https://www.mercadoinsights.online  
**Data:** 09/02/2026

---

## 🎯 COMECE AQUI

### Você acabou de ver os prints do console?

👉 **Leia:** `RELATORIO_FINAL.md`  
→ Resumo de tudo: o que foi feito, o que está corrigido, próximos passos

### Vai fazer deploy agora?

👉 **Leia:** `DEPLOY_INSTRUCOES.md`  
→ Passo a passo completo de deploy na Railway

### Quer entender a estratégia técnica?

👉 **Leia:** `ESTRATEGIA_CONCORRENCIA.md`  
→ Como comparadores funcionam, validação da nossa abordagem

---

## 📖 GUIA DE LEITURA POR SITUAÇÃO

### 🚨 ESTOU COM ERRO NO SITE

1. **`RELATORIO_FINAL.md`** → Resumo dos problemas e soluções
2. **`DEPLOY_INSTRUCOES.md`** → Como fazer deploy das correções
3. **`RELATORIO_BUGS.md`** → Lista completa de problemas (se precisar de detalhes)

### 🚀 VOU FAZER DEPLOY

1. **`DEPLOY_INSTRUCOES.md`** → Passo a passo completo
2. **`RELATORIO_FINAL.md`** → Checklist de validação pós-deploy

### 🔧 VOU MELHORAR O SISTEMA

1. **`ESTRATEGIA_CONCORRENCIA.md`** → Validação da abordagem atual
2. **`MELHORIAS_FUTURAS.md`** → Roadmap de otimizações (Multiget, cache, etc.)
3. **`RELATORIO_BUGS.md`** → Problemas pendentes (#4, #7, #9)

### 🐛 VOU DEBUGAR UM PROBLEMA

1. **`RELATORIO_BUGS.md`** → Lista de problemas conhecidos
2. **`FLUXO_DADOS_ML.md`** → Diagramas técnicos de fluxo de dados
3. **`CORRECAO_APLICADA_PESQUISA.md`** → Exemplo de correção aplicada

### ⚙️ VOU CONFIGURAR CREDENCIAIS ML

1. **`CONFIGURACAO_ML.md`** → Como obter e configurar credenciais
2. **`DEPLOY_INSTRUCOES.md`** → Seção de configuração Clerk

---

## 📚 TODOS OS DOCUMENTOS

### 📊 Principais

| Documento | Conteúdo | Quando usar |
|-----------|----------|-----------|
| **`LEIA-ME.md`** | **Este arquivo** - Índice de navegação | Sempre (começo) |
| **`RELATORIO_FINAL.md`** | Resumo executivo completo | Primeiro |
| **`DEPLOY_INSTRUCOES.md`** | Passo a passo de deploy | Antes de deploy |
| **`ESTRATEGIA_CONCORRENCIA.md`** | Validação técnica + Roadmap | Planejamento |

### 🔍 Diagnóstico

| Documento | Conteúdo | Quando usar |
|-----------|----------|-----------|
| **`RELATORIO_BUGS.md`** | 12 problemas identificados (status atualizado) | Referência técnica |
| **`FLUXO_DADOS_ML.md`** | Diagramas de fluxo de dados | Debug avançado |
| **`CORRECAO_APLICADA_PESQUISA.md`** | Exemplo de correção detalhada | Aprender padrão |

### ⚙️ Configuração

| Documento | Conteúdo | Quando usar |
|-----------|----------|-----------|
| **`CONFIGURACAO_ML.md`** | Como obter credenciais ML | Setup inicial |
| **`MELHORIAS_FUTURAS.md`** | Roadmap de otimizações | Planejamento futuro |

### 🧪 Scripts

| Script | Função | Como usar |
|--------|--------|-----------|
| **`test_ml_search.py`** | Testa busca na API ML | `python test_ml_search.py` |
| **`rename_brand.py`** | Renomeia "ML Intelligence" | Já executado ✅ |

---

## 🎓 PRINCIPAIS CONCLUSÕES

### ✅ Nossa abordagem está correta

Pesquisa confirmou que **comparadores profissionais** (Zoom, Buscapé) usam:
- API oficial (não scraping)
- Adição por ID/link individual
- Cache inteligente
- Rate limiting

**Nossa estratégia está alinhada com o mercado!**

### ✅ Correções aplicadas

- 6 problemas corrigidos (de 12 identificados)
- Console limpo (sem erros de localhost)
- Mensagens de erro específicas
- Nome "Mercado Insights" atualizado

### ⚠️ Próximos passos

1. **Deploy** (obrigatório)
2. **Clerk produção** (recomendado)
3. **Multiget** (otimização #1)
4. **Cache** (otimização #2)

---

## 🔗 LINKS RÁPIDOS

### Dashboards
- [Site em Produção](https://www.mercadoinsights.online)
- [Railway](https://railway.app)
- [Clerk](https://dashboard.clerk.com)
- [ML Developers](https://developers.mercadolivre.com.br/apps/home)

### Documentação ML
- [API Docs](https://developers.mercadolivre.com.br/pt_br/api-docs-pt-br)
- [Itens e Buscas](https://developers.mercadolivre.com.br/pt_br/itens-e-buscas)
- [OAuth](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)

---

## 🎯 PRÓXIMA AÇÃO

### VOCÊ PRECISA FAZER AGORA:

1. **Leia:** `RELATORIO_FINAL.md` (5 minutos)
2. **Execute:** Deploy conforme `DEPLOY_INSTRUCOES.md` (10 minutos)
3. **Teste:** Site em produção (5 minutos)
4. **Planeje:** Melhorias conforme `MELHORIAS_FUTURAS.md` (futuro)

---

**📖 Documentação completa e atualizada. Tudo pronto para deploy!**
