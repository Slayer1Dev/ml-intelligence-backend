# Cloudflare — Firewall, DNS e Proteção

**Projeto:** Mercado Insights  
**Domínio:** mercadoinsights.online  
**Hospedagem:** Railway

---

## O que o Cloudflare faz

| Recurso | Benefício |
|---------|-----------|
| **DNS gerenciado** | DNS rápido + painel centralizado para todos os registros |
| **Proxy reverso** | Esconde o IP real do Railway; tráfego passa pelo Cloudflare |
| **SSL/TLS** | HTTPS automático (certificado Cloudflare + Railway) |
| **WAF (Firewall)** | Bloqueia bots, SQL injection, XSS e ataques automatizados |
| **DDoS Protection** | Mitigação automática de ataques DDoS (gratuito) |
| **Rate Limiting** | Limitar requisições por IP (plano gratuito: regras básicas) |
| **Cache** | Cachear assets estáticos (CSS, JS, imagens) para carregar mais rápido |
| **Analytics** | Painel de tráfego, ameaças bloqueadas, países |

---

## Passo a passo

### 1. Criar conta no Cloudflare

1. Acesse https://dash.cloudflare.com/sign-up
2. Crie a conta (gratuita)

### 2. Adicionar o domínio

1. Clique **"Add a Site"**
2. Digite: `mercadoinsights.online`
3. Escolha o plano **Free** (já inclui DNS, proxy, DDoS, WAF básico)
4. O Cloudflare vai escanear seus registros DNS atuais

### 3. Alterar nameservers

O Cloudflare vai informar 2 nameservers (ex: `xxx.ns.cloudflare.com`).

1. Acesse o painel do seu registrador de domínio (onde comprou `mercadoinsights.online`)
2. Altere os **nameservers** para os fornecidos pelo Cloudflare
3. Aguarde propagação (minutos a 48h)

### 4. Configurar registros DNS

No painel Cloudflare → **DNS → Records**, configure:

| Tipo | Nome | Valor | Proxy |
|------|------|-------|-------|
| CNAME | `@` | URL do Railway (ex: `ml-intelligence-backend-production.up.railway.app`) | ☁️ Proxied |
| CNAME | `www` | `mercadoinsights.online` | ☁️ Proxied |

**Para o Clerk (produção):**

| Tipo | Nome | Valor | Proxy |
|------|------|-------|-------|
| CNAME | `clerk` | `frontend-api.clerk.services` | ❌ DNS Only |
| TXT | `_clerk` | (valor fornecido pelo Clerk Dashboard) | — |

> **Importante:** Registros do Clerk devem estar como **DNS Only** (nuvem cinza), não Proxied.

### 5. Configurar SSL/TLS

Cloudflare → **SSL/TLS**:

- Modo: **Full (Strict)** (Railway já tem SSL)
- Ativar: **Always Use HTTPS**
- Ativar: **Automatic HTTPS Rewrites**

### 6. Configurar Firewall (WAF)

Cloudflare → **Security → WAF**:

**Regras recomendadas (gratuitas):**

1. **Managed Rules** — Ativar "Cloudflare Managed Ruleset" (bloqueia ataques conhecidos)
2. **Rate Limiting** (Security → WAF → Rate limiting rules):
   - Regra: Se IP fizer mais de **100 requisições em 1 minuto** → Block por 10 min
   - Aplica em: `mercadoinsights.online/*`

**Regras customizadas sugeridas:**

| Regra | Condição | Ação |
|-------|----------|------|
| Bloquear bots ruins | `cf.client.bot` AND NOT `cf.bot_management.verified_bot` | Block |
| Proteger API | URI path contains `/api/` AND IP não é do Brasil | Challenge |
| Proteger admin | URI path contains `/api/admin/` | Challenge (CAPTCHA) |

### 7. Configurar Cache

Cloudflare → **Caching → Configuration**:

- **Caching Level**: Standard
- **Browser Cache TTL**: 4 hours

**Page Rules** (até 3 gratuitas):

| URL | Configuração |
|-----|-------------|
| `*mercadoinsights.online/frontend/*.css` | Cache Level: Cache Everything, Edge TTL: 1 day |
| `*mercadoinsights.online/frontend/*.js` | Cache Level: Cache Everything, Edge TTL: 1 day |
| `*mercadoinsights.online/api/*` | Cache Level: Bypass (nunca cachear API) |

---

## Checklist

- [ ] Conta Cloudflare criada
- [ ] Domínio `mercadoinsights.online` adicionado
- [ ] Nameservers alterados no registrador
- [ ] DNS propagou (verificar com `nslookup mercadoinsights.online`)
- [ ] Registros CNAME configurados (@ → Railway, www → @)
- [ ] Registros Clerk configurados (DNS Only)
- [ ] SSL/TLS: Full (Strict) + Always HTTPS
- [ ] WAF: Managed Rules ativadas
- [ ] Rate Limiting configurado
- [ ] Cache: API em bypass, assets cacheados
- [ ] Site acessível em https://www.mercadoinsights.online

---

## Depois do Cloudflare

Com Cloudflare configurado:

1. **O IP do Railway fica escondido** — Atacantes não conseguem acessar direto
2. **DDoS é mitigado automaticamente** — Cloudflare absorve o tráfego
3. **WAF bloqueia ataques** — SQL injection, XSS, bots maliciosos
4. **Assets carregam mais rápido** — Cache global em 300+ datacenters
5. **SSL gerenciado** — Sem se preocupar com renovação de certificado

---

## Custo

O plano **Free** do Cloudflare é suficiente para o estado atual do projeto. Inclui:
- DNS ilimitado
- SSL gratuito
- DDoS protection
- WAF com managed rules
- 3 page rules
- Rate limiting básico
- Analytics

Se precisar de mais no futuro (WAF avançado, rate limiting por rota, etc.), o plano **Pro** custa ~US$ 20/mês.
