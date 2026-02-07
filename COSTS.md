# Custos para ter o ML Intelligence funcionando

Guia didático do que você precisa desembolsar e configurar. Valores aproximados em reais (2025).

---

## O que você já tem

| Item | Situação |
|------|----------|
| Railway | ✅ Assinatura ativa — basta subir o projeto |
| Código | ✅ Backend e frontend base prontos |

---

## O que você precisa pagar/comprar

### 1. Domínio (opcional no início, essencial depois)

- **O que é:** endereço fixo tipo `mlinteligence.com.br`
- **Por que:** usuário acessa sempre o mesmo link; Clerk/Stripe exigem URL fixa em produção
- **Custo:** ~R$ 40–60/ano (.com.br) ou ~R$ 50–80/ano (.com)
- **Onde:** Registro.br (.br), Namecheap, Google Domains, etc.
- **Quando:** pode testar primeiro com URL do Railway (ex: `seu-projeto.up.railway.app`) e depois apontar o domínio

---

### 2. Clerk (login com Google)

- **O que é:** serviço de autenticação — login com Google, gerenciamento de sessão
- **Custo:** plano gratuito até ~10.000 usuários ativos/mês
- **Quando paga:** só se ultrapassar o free tier (improvável no início)
- **Onde:** [clerk.com](https://clerk.com)

---

### 3. Stripe (pagamentos)

- **O que é:** cobrança por cartão, assinaturas recorrentes
- **Custo:** ~2,9% + R$ 0,39 por transação (aprox.)
- **Quando paga:** só quando recebe — não há mensalidade no plano básico
- **Onde:** [stripe.com](https://stripe.com)

---

### 4. OpenAI (análises com IA)

- **O que é:** API para análise de descrições, insights etc.
- **Custo:** por uso (alguns centavos por análise)
- **Exemplo:** GPT-4o-mini ~R$ 0,01–0,05 por análise simples
- **Quando paga:** só quando alguém usa as funções de IA
- **Onde:** [platform.openai.com](https://platform.openai.com)

---

### 5. App no Mercado Livre

- **O que é:** aplicativo que você cria no painel de desenvolvedores do ML para acessar a API
- **Custo:** gratuito
- **Onde:** [developers.mercadolivre.com.br](https://developers.mercadolivre.com.br)
- **O que fazer:** criar app, configurar OAuth e obter Client ID e Secret

---

### 6. Railway (hosting)

- **Situação:** você já tem assinatura
- **Custo:** conforme seu plano atual
- **Observação:** o plano gratuito costuma ter limites; plano pago tende a ser estável para produção

---

## Resumo rápido

| Item | Custo inicial | Custo recorrente |
|------|---------------|------------------|
| Domínio | ~R$ 50/ano | Anual |
| Clerk | R$ 0 | R$ 0 (free tier) |
| Stripe | R$ 0 | % da venda |
| OpenAI | R$ 0 | Por uso |
| App ML | R$ 0 | R$ 0 |
| Railway | Já pago | Mensal (seu plano) |

**Para começar:** você pode rodar com **R$ 0** além do Railway, usando a URL gerada por eles. O domínio pode vir quando for lançar de fato.

---

## Ordem sugerida de configuração

1. **Rodar local** — backend + frontend (sem auth, sem Stripe)
2. **Clerk** — criar conta, configurar login com Google
3. **Stripe** — criar conta, configurar produto/plano de assinatura
4. **App ML** — criar app e obter credenciais OAuth
5. **Domínio** — comprar e apontar para o Railway
6. **Deploy** — subir na Railway e configurar variáveis de ambiente

---

## O que depende de você (não é só pagamento)

- Configurar o app no Mercado Livre (Client ID, Secret, redirect URI)
- Criar conta em Clerk e configurar Google OAuth
- Criar conta no Stripe e configurar produto/assinatura
- Adicionar variáveis de ambiente no Railway (.env em produção)
- Configurar domínio e apontar para a Railway (quando tiver)

Se quiser, podemos ir passo a passo em qualquer um desses itens.
