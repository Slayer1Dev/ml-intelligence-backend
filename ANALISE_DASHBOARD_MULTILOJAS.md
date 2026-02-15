# Analise Tecnica: Dashboard Automatizado Multi-Lojas

**Data:** 2026-02-14
**Autor:** Equipe de desenvolvimento Mercado Insights
**Status:** Documento de especificacao para construcao

---

## 1. Visao Geral do Projeto

### O que existe hoje (processo manual)

O operador mantem uma planilha Excel (`Dashboard.xlsx`) com 8 abas e ~195 produtos, onde:

1. Insere custos, impostos, frete e embalagem manualmente
2. Copia precos do Mercado Livre manualmente
3. Registra vendas do mes e calcula margens com formulas
4. Pesquisa concorrentes e anota precos
5. Calcula tendencias (subindo/caindo) comparando periodos
6. Decide acoes (comprar estoque, ajustar preco, etc.)
7. Anota observacoes e marca como "feito"

**Tempo estimado:** Varias horas por semana, por loja. Com mais lojas, fica insustentavel.

### O que queremos construir

Um sistema que:

- **Puxa dados automaticamente** da API do Mercado Livre (e futuramente Shopee)
- **Aceita dados manuais** via upload de planilha simples (SKU + Custo)
- **Gerencia multiplas lojas** (cada uma com seus dados, API ou manual)
- **Calcula tudo automaticamente** (margem, lucro, tendencia, estoque critico)
- **Gera graficos e analises** visuais
- **Oferece visao geral** (todas as lojas) e **isolada** (por loja)
- **Escala** para novos marketplaces (Shopee, Amazon, etc.)

---

## 2. Analise Detalhada da Planilha

### 2.1 Aba "Pagina1" (Dashboard Principal) -- 26 colunas

| Coluna | Nome | Tipo | Fonte Possivel |
|--------|------|------|----------------|
| A | COD. DO PROD. | MLB ID | API ML: `item.id` |
| B | SKU | Codigo interno | API ML: `item.seller_custom_field` ou input manual |
| C | Descricao | Texto longo | API ML: `item.title` |
| D | Custo | R$ | **INPUT MANUAL** (planilha custos) |
| E | Valor de Venda | R$ | API ML: `item.price` |
| F | Preco Promocao | R$ | API ML: deals/promos ou input manual |
| G | Tarifa de venda | % | API ML: `listing_type` -> calculo ou input |
| H | Imposto | % | **INPUT MANUAL** (planilha impostos) |
| I | Custo Frete | R$ | API ML: `shipping` ou input manual |
| J | Custo Embalagem | R$ | **INPUT MANUAL** |
| K | Margem Atual | % | **CALCULADO**: `(Preco - CustoTotal) / Preco` |
| L | Lucro em Reais | R$ | **CALCULADO**: `Preco - Custo - Taxa - Imposto - Frete - Embalagem` |
| M | Menor Preco Concorrente | R$ | API ML: `search` (limitado) ou input manual |
| N | Maior Preco Concorrente | R$ | API ML: `search` (limitado) ou input manual |
| O | Preco Medio Concorrente | R$ | **CALCULADO** a partir de M e N |
| P | Preco do Mais Vendido | R$ | API ML: `search` sort=sold_quantity (limitado) |
| Q | Vendas Mes Concorrente | Qtd | Input manual |
| R | Quantidade em Estoque | Qtd | API ML: `item.available_quantity` |
| S | Tempo Medio de Duracao | Dias | **CALCULADO**: `Estoque / Media Diaria Vendas` |
| T | Tempo Medio Estoque Atual | Dias | **CALCULADO** |
| U | Sugestao de Compra | Texto | **CALCULADO**: regra baseada no tempo de estoque |
| V | Vendas no Mes | Qtd | API ML: `orders/search` filtrado por data |
| W | Acoes Propostas | Texto | IA ou input manual |
| X | OBS. | Texto | Input manual |
| Y | FEITO | Bool | Input manual (checklist) |
| Z | ATENCAO | Texto | **CALCULADO** ou input manual |

### 2.2 Aba "Analise" -- Tendencias de Vendas

| Coluna | Nome | Calculo |
|--------|------|---------|
| A | CODIGO | MLB ID |
| B | VENDAS PERIODO LONGO | Total de vendas em ~120 dias |
| C | DIAS PERIODO LONGO | Dias do periodo (ex: 123) |
| D | MEDIA DIARIA LONGO | B / C |
| E | VENDAS MES ATUAL | Vendas nos ultimos ~30 dias |
| F | DIAS DECORRIDOS MES | Dias do mes ate agora |
| G | MEDIA DIARIA ATUAL | E / F |
| H | VARIACAO % | `(G - D) / D` |
| I | STATUS | SUBINDO se H > 0, CAINDO se H < 0 |
| J | Ordem | Ranking por variacao |

**Insight:** Tudo isso pode ser calculado automaticamente com dados de `orders/search` da API ML.

### 2.3 Abas Auxiliares (Dados de Entrada)

| Aba | Colunas | Registros | Finalidade |
|-----|---------|-----------|------------|
| ESTOQUE | SKU + Qtd | 189 | Redundante com API ML (`available_quantity`) |
| Custos | SKU + Valor | 393 | **Essencial** -- nao existe na API |
| Impostos | SKU + % | 463 | **Essencial** -- varia por NCM |
| Frete | MLB + Valor | 206 | Parcialmente na API |
| Preco Promocional | Codigo + Preco | 48 | Parcialmente na API |
| Vendas Mes 02 | Codigo + Vendas | 34 | Substituido por `orders/search` |

---

## 3. Arquitetura Multi-Lojas

### 3.1 Problema atual: modelo single-store

Hoje, `MlToken` tem `unique=True` em `user_id` -- ou seja, **1 usuario = 1 conta ML**.
`ItemCost` vincula custos a `user_id` + `item_id`, sem distincao de loja.

### 3.2 Solucao: conceito de "Store" (Loja)

Introduzir um modelo `Store` que representa uma loja/conta em qualquer marketplace:

```
User (1) ---< Store (N)
                |
                |- name: "Lar das Fitas ML"
                |- platform: "mercado_livre" | "shopee" | "manual"
                |- connection_type: "api" | "manual"
                |- ml_token_id: FK (nullable, so para ML com API)
                |- seller_id: (para ML)
                |- shopee_shop_id: (futuro)
                |
                |---< StoreItem (produtos da loja)
                |       |- store_id
                |       |- external_id (MLB..., Shopee ID, ou gerado)
                |       |- sku
                |       |- title
                |       |- price, cost, tax_pct, shipping, packaging
                |       |- stock, sales_month, sales_long
                |       |- margin, profit (calculados)
                |       |- trend_status, trend_pct
                |       |- data_source: "api" | "manual" | "csv"
                |       |- last_synced_at
```

### 3.3 Tipos de loja

| Tipo | Platform | Dados | Exemplo |
|------|----------|-------|---------|
| **ML com API** | `mercado_livre` | Automatico via OAuth | Loja principal (ja funciona) |
| **ML Manual** | `mercado_livre` | Upload de planilha | Segunda loja (teste) |
| **Shopee com API** | `shopee` | Automatico via OAuth (futuro) | Quando integrado |
| **Manual generico** | `manual` | Tudo via planilha | Qualquer marketplace |

### 3.4 Fluxo para Loja Manual (segunda loja -- teste)

```
1. Usuario clica "Adicionar Loja" -> tipo: "Manual / Planilha"
2. Nomeia a loja: "Lar das Fitas ML - Conta 2"
3. Faz upload da planilha Dashboard.xlsx (ou CSV simplificado)
4. Sistema importa os dados para StoreItem:
   - SKU, titulo, preco, custo, imposto, frete, embalagem
   - Vendas do mes, estoque
5. Sistema calcula automaticamente:
   - Margem, lucro, tempo de estoque, sugestao de compra
6. Dashboard mostra graficos e analise da loja
```

### 3.5 Fluxo para Loja com API ML

```
1. Usuario conecta conta ML via OAuth (ja funciona)
2. Sistema cria Store automaticamente com platform="mercado_livre", connection="api"
3. Dados puxados automaticamente (anuncios, precos, estoque, vendas)
4. Usuario complementa com custos via upload CSV (SKU + Custo)
5. Dashboard mostra graficos com dados atualizados em tempo real
```

---

## 4. Visoes de Analise

### 4.1 Visao Geral (todas as lojas)

Dashboard que consolida:

- **Receita total estimada** (soma de todas as lojas)
- **Lucro total estimado**
- **Margem media ponderada**
- **Total de produtos** (por loja e total)
- **Estoque total valorizado**
- **Produtos criticos** (estoque baixo, margem negativa) de todas as lojas
- **Grafico comparativo**: lucro por loja
- **Grafico**: tendencia geral (subindo vs caindo)

### 4.2 Visao Isolada (por loja)

Cada loja tem seu proprio dashboard com:

- **Cards de metricas**: total produtos, margem media, lucro, estoque critico
- **Grafico de barras**: Top 10 por lucro
- **Grafico pizza**: Distribuicao de margem (alta > 30%, media 15-30%, baixa 0-15%, negativa < 0%)
- **Grafico barras**: Produtos SUBINDO vs CAINDO
- **Grafico**: Estoque critico (< 30 dias)
- **Tabela completa**: todos os produtos com filtros e ordenacao
- **Sugestoes automaticas**: comprar estoque, ajustar preco, pausar anuncio

### 4.3 Visao de Mercado (futura)

Quando houver API Shopping de Precos e/ou certificacao ML:

- **Posicionamento de preco**: seu preco vs mercado
- **Oportunidades**: produtos onde voce esta muito acima ou abaixo
- **Tendencias de mercado**: categorias crescendo ou caindo

---

## 5. Dados: o que vem da API vs o que precisa de input

### Mercado Livre (com API conectada)

| Dado | Fonte | Automatico? |
|------|-------|-------------|
| ID do anuncio (MLB) | `item.id` | Sim |
| SKU | `item.seller_custom_field` | Sim |
| Titulo | `item.title` | Sim |
| Preco de venda | `item.price` | Sim |
| Estoque | `item.available_quantity` | Sim |
| Status (ativo/pausado) | `item.status` | Sim |
| Thumbnail | `item.secure_thumbnail` | Sim |
| Tipo de listagem | `item.listing_type_id` | Sim |
| Vendas no mes | `orders/search` com filtro de data | Sim |
| Vendas periodo longo | `orders/search` com filtro de data | Sim |
| Frete | `item.shipping` (parcial) | Parcial |
| **Custo do produto** | Nao existe na API | **Upload** |
| **Imposto %** | Nao existe na API | **Upload** |
| **Embalagem** | Nao existe na API | **Upload** |

### Mercado Livre (manual / sem API)

Todos os dados via upload de planilha (formato da Dashboard.xlsx ou CSV simplificado).

### Shopee (futuro, com API)

| Dado | Endpoint Shopee |
|------|----------------|
| Produtos | `GET /api/v2/product/get_item_list` |
| Detalhes | `GET /api/v2/product/get_item_base_info` |
| Pedidos | `GET /api/v2/order/get_order_list` |
| Logistica | `GET /api/v2/logistics/get_shipping_parameter` |

---

## 6. Upload de Custos -- Formato Simplificado

### Opcao 1: CSV minimo (2 colunas)

```csv
SKU,CUSTO
FR00391,22.55
DV00331,7.00
KIT000018,33.55
```

O sistema faz match por SKU com os anuncios da loja e atualiza automaticamente.

### Opcao 2: CSV completo (6 colunas)

```csv
SKU,CUSTO,IMPOSTO_PCT,EMBALAGEM,FRETE,OBS
FR00391,22.55,9.0,1.00,0,Kit croche
DV00331,7.00,9.0,25.00,0,Estilete
```

### Opcao 3: Upload da planilha Dashboard.xlsx completa

O sistema le todas as abas e importa:
- Aba "Custos" -> custo por SKU
- Aba "Impostos" -> imposto por SKU
- Aba "Frete" -> frete por MLB
- Aba "Pagina1" -> dados completos (preco, estoque, vendas)
- Aba "Analise" -> tendencias

**Para loja manual**: importa tudo da Pagina1 e cria produtos no StoreItem.
**Para loja com API**: usa apenas custos/impostos e ignora dados que ja vem da API.

---

## 7. Calculos Automaticos

### Financeiros (por produto)

```
Taxa ML (R$) = Preco * (Tarifa / 100)
Imposto (R$) = Preco * (Imposto% / 100)
Custo Total  = Custo + Taxa ML + Imposto + Frete + Embalagem
Lucro (R$)   = Preco - Custo Total
Margem (%)   = (Lucro / Preco) * 100
```

### Estoque

```
Media Diaria (longo)  = Vendas Periodo Longo / Dias do Periodo
Media Diaria (atual)  = Vendas Mes Atual / Dias Decorridos
Tempo de Estoque      = Estoque / Media Diaria (atual ou longo)

Sugestao:
  Se Tempo < 15 dias  -> "COMPRAR URGENTE"
  Se Tempo < 30 dias  -> "COMPRAR"
  Se Tempo < 60 dias  -> "ESTOQUE PARA 1 MES"
  Senao               -> "ESTOQUE SUFICIENTE"
```

### Tendencia

```
Variacao % = ((Media Atual - Media Longo) / Media Longo) * 100

Status:
  Se Variacao > 10%   -> "SUBINDO"
  Se Variacao < -10%  -> "CAINDO"
  Senao               -> "ESTAVEL"
```

---

## 8. Mudancas no Banco de Dados

### Novos modelos necessarios

```python
class Store(Base):
    __tablename__ = "stores"
    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    name          = Column(String(255), nullable=False)         # "Lar das Fitas ML"
    platform      = Column(String(32), nullable=False)          # mercado_livre | shopee | manual
    connection    = Column(String(16), default="manual")        # api | manual
    ml_token_id   = Column(Integer, ForeignKey("ml_tokens.id"), nullable=True)
    seller_id     = Column(String(64), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

class StoreItem(Base):
    __tablename__ = "store_items"
    __table_args__ = (UniqueConstraint("store_id", "external_id"),)
    id              = Column(Integer, primary_key=True)
    store_id        = Column(Integer, ForeignKey("stores.id"), nullable=False)
    external_id     = Column(String(64), nullable=False)        # MLB..., SHOP..., ou gerado
    sku             = Column(String(128), nullable=True)
    title           = Column(String(512), nullable=True)
    description     = Column(String(2048), nullable=True)
    price           = Column(Float, nullable=True)
    promo_price     = Column(Float, nullable=True)
    cost            = Column(Float, nullable=True)
    fee_pct         = Column(Float, nullable=True)
    tax_pct         = Column(Float, nullable=True)
    shipping_cost   = Column(Float, default=0)
    packaging_cost  = Column(Float, default=0)
    margin_pct      = Column(Float, nullable=True)              # calculado
    profit          = Column(Float, nullable=True)              # calculado
    stock           = Column(Integer, default=0)
    sales_month     = Column(Integer, default=0)
    sales_long      = Column(Integer, default=0)
    days_long       = Column(Integer, default=120)
    trend_pct       = Column(Float, nullable=True)              # calculado
    trend_status    = Column(String(16), nullable=True)         # SUBINDO | ESTAVEL | CAINDO
    stock_days      = Column(Float, nullable=True)              # calculado
    restock_status  = Column(String(32), nullable=True)         # calculado
    notes           = Column(String(1024), nullable=True)
    data_source     = Column(String(16), default="manual")      # api | manual | csv
    thumbnail       = Column(String(512), nullable=True)
    last_synced_at  = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Migracao do modelo atual

O modelo `ItemCost` existente **continua funcionando** para a loja ML principal (retrocompatibilidade). A migracao sera gradual:

1. Criar tabelas `stores` e `store_items`
2. Ao conectar ML via API, criar Store automaticamente
3. Ao adicionar loja manual, criar Store + importar StoreItems
4. Futuramente, migrar `ItemCost` para `StoreItem` e deprecar

---

## 9. API -- Novos Endpoints

### Gerenciar lojas

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/stores` | Listar lojas do usuario |
| POST | `/api/stores` | Criar loja (manual ou vincular ML) |
| GET | `/api/stores/{id}` | Detalhes da loja |
| DELETE | `/api/stores/{id}` | Remover loja |

### Analise por loja

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/stores/{id}/dashboard` | Dashboard completo da loja (metricas + items calculados) |
| GET | `/api/stores/{id}/items` | Produtos da loja com filtros |
| POST | `/api/stores/{id}/import` | Upload planilha/CSV (custos ou dados completos) |
| POST | `/api/stores/{id}/sync` | Sincronizar dados da API (lojas com API) |

### Visao geral

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/analytics/overview` | Consolidado de todas as lojas |

---

## 10. Frontend -- Paginas

### 10.1 Pagina "Minhas Lojas" (`lojas.html`)

- Lista de lojas cadastradas com nome, plataforma, tipo de conexao
- Botao "Adicionar Loja" (modal: nome, plataforma, tipo)
- Card por loja com metricas resumidas

### 10.2 Pagina "Analise da Loja" (`analise-loja.html?store={id}`)

- Seletor de loja no topo
- Cards de metricas (total produtos, margem media, lucro, estoque critico)
- Graficos (Chart.js):
  - Top 10 lucro (barras horizontal)
  - Distribuicao de margem (pizza)
  - Tendencia: subindo vs estavel vs caindo (barras)
  - Estoque critico (barras)
- Tabela completa com filtros e ordenacao
- Botao "Importar Custos" (upload CSV)
- Botao "Exportar Analise" (download CSV)

### 10.3 Pagina "Visao Geral" (`analise-geral.html`)

- Consolidado de todas as lojas
- Grafico comparativo: lucro por loja
- Alertas: estoque critico, margem negativa, tendencia de queda
- Link para cada loja individual

---

## 11. Fases de Implementacao

### Fase 1: Loja Manual (MVP) -- Prioridade imediata

**Objetivo:** Importar dados da planilha Dashboard.xlsx e gerar analise automatica.

1. Criar modelos `Store` e `StoreItem` no banco
2. Endpoint para criar loja manual
3. Endpoint para importar planilha XLSX (ler todas as abas)
4. Calculos automaticos (margem, lucro, tendencia, estoque)
5. Pagina frontend com graficos e tabela
6. Upload de custos via CSV

**Resultado:** Segunda loja operando com dados da planilha, graficos e analises.

### Fase 2: Multi-Store ML -- Curto prazo

**Objetivo:** Suportar multiplas contas ML via API.

1. Alterar `MlToken` para suportar N tokens por usuario (remover `unique=True`)
2. Vincular cada token a uma Store
3. Adaptar endpoints existentes para receber `store_id`
4. Criar Store automaticamente ao conectar ML

### Fase 3: Analise Consolidada -- Medio prazo

**Objetivo:** Visao geral cross-store.

1. Endpoint `/api/analytics/overview` consolidando dados
2. Pagina frontend com comparativo entre lojas
3. Alertas cross-store

### Fase 4: Shopee -- Futuro

**Objetivo:** Integrar com Shopee API.

1. OAuth Shopee (partner API)
2. Sync de produtos, pedidos, estoque
3. Criar Store com platform="shopee"
4. Dados fluem para o mesmo StoreItem

### Fase 5: Mercado / Shopping de Precos -- Futuro

**Objetivo:** Analise de mercado cruzada.

1. Integrar API de Shopping de Precos (quando disponivel)
2. Comparar precos do usuario vs mercado
3. Oportunidades de repricing
4. Dashboard de mercado

---

## 12. Consideracoes Tecnicas

### Retrocompatibilidade

Todo o sistema atual (Painel Financeiro, Meus Anuncios, Performance, etc.) continua funcionando sem alteracao. A feature de multi-lojas e **aditiva** -- nao quebra nada existente.

### Seguranca

- Cada Store pertence a um `user_id` -- isolamento total
- StoreItems sao acessiveis apenas pelo dono da Store
- Upload de planilha: validacao de formato, limite de tamanho, saneamento

### Escalabilidade

- StoreItem armazena dados calculados (evita recalcular a cada request)
- Sync de API ML pode ser agendado (APScheduler, ja existe)
- Graficos renderizados no frontend (Chart.js) -- nao sobrecarrega backend

---

## 13. Resumo para a equipe de desenvolvimento

### O que construir primeiro (Fase 1)

1. **Banco:** Modelos `Store` e `StoreItem` (ver secao 8)
2. **Backend:** 4 endpoints (`/api/stores`, `POST import`, `GET dashboard`, `GET items`)
3. **Import:** Parsear Dashboard.xlsx e popular StoreItem com calculos
4. **Frontend:** 1 pagina com graficos (Chart.js) + tabela + upload
5. **Sidebar:** Link "Analise" em todas as paginas

### O que NAO fazer agora

- Nao alterar modelos existentes (`MlToken`, `ItemCost`)
- Nao mexer nas paginas existentes (Financeiro, Anuncios, etc.)
- Nao integrar Shopee (futuro)
- Nao integrar Shopping de Precos (futuro)

### Resultado esperado

O operador para de manter a planilha manualmente. Em vez disso:

1. Abre "Analise" no sistema
2. Ve todas as lojas com graficos e metricas
3. Importa custos via CSV quando necessario
4. Toma decisoes baseadas em dados calculados automaticamente
5. Economiza horas por semana
