# Análise: API Mercado Livre para Busca de Concorrentes

**Data:** 09/02/2025  
**Objetivo:** Revisar a implementação atual, comparar com projetos no GitHub e avaliar se a API pública do ML é suficiente para busca por concorrentes.

---

## 1. Resumo Executivo

| Aspecto | Conclusão |
|---------|-----------|
| **Nossa implementação** | Correta. Usamos `GET /sites/MLB/search?q=...` conforme documentação. |
| **Erro 403** | Esperado para apps **não certificados** pelo Mercado Livre. |
| **API pública suficiente?** | Sim – o endpoint deveria bastar. Na prática, o ML restringe apps não certificados. |
| **Alternativa scraping** | Desaconselhada – documentação ML proíbe web crawling explicitamente. |

---

## 2. O Que Estamos Fazendo

### 2.1 Fluxo atual (`app/services/ml_api.py`)

```
search_public(site_id="MLB", q=termo, limit=50, offset=0, access_token=None)
    → GET https://api.mercadolibre.com/sites/MLB/search?q=termo&limit=50&offset=0
    → Headers: User-Agent: MLIntelligence/1.0 (https://mercadoinsights.online)
    → Opcional: Authorization: Bearer {access_token}
```

- Primeiro tenta **sem token** (busca “pública”).
- Se retornar erro (ex.: 403), tenta **com token** do usuário conectado.
- Em ambos os casos, apps não certificados costumam receber **403 Forbidden**.

### 2.2 Endpoints documentados (Itens e Buscas)

| Endpoint | Uso | Token obrigatório na doc |
|----------|-----|--------------------------|
| `/sites/{SITE_ID}/search?q=...` | Busca por termo | Sim (exemplos mostram Bearer) |
| `/sites/{SITE_ID}/search?seller_id=...` | Itens por vendedor | Sim |
| `/users/{USER_ID}/items/search` | Itens da conta do vendedor | Sim |
| `GET /items/{ITEM_ID}` | Detalhe de um item | Pode funcionar público |

A documentação fala em “recursos públicos”, mas os exemplos sempre usam `Authorization: Bearer`.  
Na prática, o endpoint `/sites/MLB/search?q=...` retorna 403 para apps que não passaram pela certificação do ML.

---

## 3. Comparação com Projetos no GitHub

### 3.1 Los-had/mercado-livre-api

- **URL:** https://github.com/Los-had/mercado-livre-api  
- **Técnica:** Web scraping com BeautifulSoup na página de listagem pública.
- **Código típico:**
  ```python
  url = f'https://lista.mercadolivre.com.br/{product_name}'
  website = requests.get(url).text
  soup = BeautifulSoup(website, 'lxml')
  # Extrai título, preço, link de cada card
  ```
- **Diferença:** Não usa a API do Mercado Livre. Acessa o HTML de `lista.mercadolivre.com.br` como um navegador.
- **Por que “funciona”:** O site público não bloqueia requisições como a API bloqueia apps não certificados.

**Importante:** A documentação do ML diz explicitamente:

> *"Não fazer web crawling, e sim sempre trabalhar com la API de MeLi."*  
> (https://developers.mercadolivre.com.br/pt_br/boas-praticas-para-usar-a-plataforma)

Ou seja: scraping não é recomendado e pode violar os Termos e Condições.

### 3.2 VulcanoAhab/pyMerli

- **URL:** https://github.com/VulcanoAhab/pyMerli  
- **Descrição:** Wrapper da Search API do Mercado Livre.
- **Conclusão:** Usa a API oficial; sujeito às mesmas restrições que o nosso app (incluindo 403 para apps não certificados).

### 3.3 Conclusão da comparação

- Projetos que “funcionam” para busca em massa costumam usar **scraping**, não a API.
- Projetos que usam a API oficial enfrentam os mesmos 403 que nós.
- Nossa abordagem está alinhada com a API oficial; o bloqueio vem da política do ML, não de erro na implementação.

---

## 4. Reclame Aqui – Caso similar (dez/2025)

Um desenvolvedor relatou exatamente o mesmo problema:

- Endpoint: `GET https://api.mercadolibre.com/sites/MLB/search?q={consulta}`
- Retorno: **403 Forbidden**, mesmo com:
  - Token válido
  - Escopo correto
  - site_id MLB
  - Query documentada

Situação: app completo (site + backend + integrações), mas bloqueado nesse endpoint “público” sem explicação clara na documentação.

Isso reforça que o problema é institucional/estrutural do ML, não de implementação nossa.

---

## 5. A API Pública É Suficiente para Busca por Concorrentes?

**Em teoria: SIM.**

O endpoint `/sites/{SITE_ID}/search?q=...` é o adequado para:

- Buscar anúncios por termo
- Comparar preços
- Encontrar concorrentes

**Na prática: NÃO, para apps não certificados.**

O Mercado Livre restringe esse endpoint para aplicações que não passaram pelo processo de certificação, retornando 403 sem documentar claramente essa regra.

---

## 6. Opções Disponíveis

### 6.1 Certificação do app (recomendado)

- Processo formal no [Developer Center](https://developers.mercadolivre.com.br/) do ML.
- Após aprovação, o endpoint de busca tende a funcionar normalmente.
- Solução dentro dos termos oficiais.

### 6.2 Adicionar concorrente por link/ID (já implementado)

- Usuário informa URL ou ID (ex.: `MLB123456`).
- Usamos `GET /items/{ITEM_ID}` (item individual).
- Este endpoint costuma funcionar mesmo sem certificação.
- Limitação: não permite busca em massa; o usuário precisa ter o link/ID do concorrente.

### 6.3 Web scraping (desaconselhado)

- Técnica usada por projetos como Los-had/mercado-livre-api.
- ML documenta: não fazer web crawling, usar a API.
- Risco de bloqueio, violação de ToS e instabilidade (mudanças no HTML).
- Não recomendado para produção.

### 6.4 Contato com suporte do ML

- Canal de suporte técnico para desenvolvedores.
- Pode esclarecer requisitos para acesso ao endpoint de busca.
- Reclame Aqui indica dificuldade em obter respostas objetivas.

---

## 7. Recomendações

1. **Manter a implementação atual** – Está correta e compatível com a documentação.
2. **Priorizar “Adicionar por link/ID”** – Funciona sem certificação e é a saída imediata para usuários.
3. **Iniciar processo de certificação** – Para desbloquear busca por termo no futuro.
4. **Não implementar scraping** – Mesmo que funcione em outros projetos, vai contra as boas práticas do ML.
5. **Melhorar UX da alternativa** – Enfatizar no frontend a opção “Adicionar concorrente por link” e explicar por que a busca por termo pode estar indisponível.

---

## 8. Arquivos Relevantes no Projeto

| Arquivo | Função |
|---------|--------|
| `app/services/ml_api.py` | `search_public()`, `get_item_by_id()` |
| `app/main.py` | Rotas `/api/ml/search`, `/api/ml/competitors` |
| `frontend/concorrentes.html` | Interface de busca e adicionar por link |
| `test_ml_search.py` | Script de diagnóstico da busca |
| `ACAO_URGENTE.md` | Ações pendentes no portal ML |

---

## 9. Referências

- [Itens e Buscas – Documentação ML](https://developers.mercadolivre.com.br/pt_br/itens-e-buscas)
- [Buscador de Produtos](https://developers.mercadolivre.com.br/pt_br/buscador-de-produtos)
- [Erro 403](https://developers.mercadolivre.com.br/pt_br/erro-403)
- [Boas Práticas – Não fazer web crawling](https://developers.mercadolivre.com.br/pt_br/boas-praticas-para-usar-a-plataforma)
- [Los-had/mercado-livre-api](https://github.com/Los-had/mercado-livre-api) – usa scraping
- [Reclame Aqui – Bloqueio endpoint busca](https://www.reclameaqui.com.br/mercado-livre/acesso-bloqueado-ao-endpoint-de-busca-publica-da-api-do-mercado-livre_fvb1Z5Wo3WaRD94a/)
