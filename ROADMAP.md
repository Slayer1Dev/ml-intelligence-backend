# ML Intelligence — Plano de Estrutura e Próximas Ações

Documento de planejamento. Objetivo: ter uma base sólida antes de integrar a API do Mercado Livre, para que depois seja só "ligar a tomada".

---

## 1. Visão geral da estrutura

```
Landing (pública)
    ↓
Login (Clerk - Google)
    ↓
Dashboard do usuário (área logada)
    ├── Calculadora de Lucro
    ├── Painel Financeiro (planilhas → depois API)
    ├── Meus Anúncios (placeholder → API)
    ├── Performance (placeholder → API)
    └── Concorrentes (placeholder → API)

Admin (sua área privada)
    ├── Usuários (free vs paid)
    ├── Assinaturas (Stripe)
    └── Pontos a revisar do sistema
```

---

## 2. O que construir agora (independente do ML)

### 2.1 Login e autenticação

| Item | Responsável | Descrição |
|------|-------------|-----------|
| **Clerk** | Você (config) + Código | Login com Google |
| **Middleware no backend** | Código | Validar token JWT do Clerk em rotas protegidas |
| **Páginas protegidas** | Frontend | Se não logado → redireciona para login |
| **Logout** | Frontend | Botão que encerra sessão |

**Como ligar o login ao usuário:**
- Clerk retorna um `user_id` (ex: `user_2abc123`)
- Backend recebe o token no header `Authorization`
- Toda ação (salvar dados, Stripe, etc.) fica associada a esse `user_id`

---

### 2.2 Stripe — um produto para começar a vender

| Item | Descrição |
|------|-----------|
| **Produto no Stripe** | Ex: "ML Intelligence — Plano Mensal" |
| **Checkout** | Página/botão "Assinar" → redireciona para Stripe Checkout |
| **Webhook** | Stripe avisa o backend quando o pagamento foi feito |
| **Status do usuário** | Backend grava: `user_id` + `status: free | active` |
| **Banco de dados** | Tabela `users` ou `subscriptions` para guardar quem é free e quem é pago |

**Fluxo simples:**
1. Usuário clica "Assinar"
2. Vai para Stripe, paga
3. Stripe chama seu webhook
4. Backend marca o `user_id` como `active`
5. Usuário volta ao site e acessa as funções pagas

---

### 2.3 Área de Admin — sua área

| Bloco | O que ter |
|-------|-----------|
| **Usuários** | Lista de usuários, filtro free / paid |
| **Assinaturas** | Quem assinou, quando, valor |
| **Pontos a revisar** | Checklist interno do sistema (bugs, melhorias, deudas técnicas) |

**Acesso:** só você. Duas opções:
- Lista fixa de e-mails admins no backend
- Ou role `admin` no Clerk (se usar Organizations)

---

### 2.4 Pontos a revisar do sistema (checklist interno)

Lista que você controla e que pode virar uma tela dentro do admin:

| Categoria | Exemplo |
|-----------|---------|
| **Bugs** | "Calculadora não aceita X" |
| **Melhorias** | "Adicionar filtro por período no painel" |
| **Deudas técnicas** | "Migrar HTML para React" |
| **Integrações pendentes** | "API ML — vendas", "API ML — anúncios" |
| **UX** | "Melhorar mensagem quando não há custos" |

Isso pode ser:
- Um arquivo (ex: `TODO.md`) no repo, ou
- Uma tela no admin que lista itens (com prioridade, status, etc.)

---

## 3. Banco de dados

Para guardar usuários, plano e assinaturas:

| Tabela | Campos principais |
|--------|-------------------|
| `users` | `id`, `clerk_user_id`, `email`, `plan` (free/active), `created_at` |
| `subscriptions` | `id`, `user_id`, `stripe_subscription_id`, `status`, `started_at`, `ends_at` |
| `admin_notes` (opcional) | `id`, `category`, `title`, `status`, `created_at` |

**Sugestão:** SQLite para começar (simples, sem servidor). Depois migrar para PostgreSQL quando subir na Railway.

---

## 4. Ordem sugerida de implementação

### Fase A — Fundação (antes de vender)

1. **Clerk** — configurar e integrar no frontend
2. **Proteção de rotas** — backend valida token
3. **Banco de dados** — `users` + `subscriptions`
4. **Páginas protegidas** — dashboard só para logados

### Fase B — Monetização

5. **Stripe** — produto, checkout, webhook
6. **Lógica free vs paid** — free vê só calculadora; paid vê todo o resto
7. **Admin — usuários** — ver quem é free e quem é paid

### Fase C — Sua área de controle

8. **Admin — painel** — área /admin com menu
9. **Admin — pontos a revisar** — checklist interno (arquivo ou tela)
10. **Admin — assinaturas** — histórico de quem pagou

### Fase D — API ML (depois)

11. OAuth ML
12. Endpoints de vendas, anúncios, etc.
13. Trocar dados de planilha por dados da API onde fizer sentido

---

## 5. Como fica o fluxo do usuário

```
1. Acessa landing
2. Clica "Entrar" → Clerk (Google)
3. Volta logado → Dashboard
4. Se FREE: vê Calculadora + aviso para assinar
5. Se PAID: vê todas as ferramentas
6. Clica "Assinar" → Stripe Checkout → paga
7. Webhook atualiza status → usuário vira PAID
8. Próximo login: já vê tudo liberado
```

---

## 6. Próxima ação concreta

Sugestão de primeiro passo:

1. Criar estrutura de pastas e modelos para `users` e `subscriptions`
2. Adicionar Clerk no frontend (botão de login)
3. Proteger uma rota de exemplo no backend
4. Criar a rota `/admin` (protegida só para você) com uma página simples

Depois disso, vem Stripe e a lógica free/paid.

---

## 7. Resumo

| O que | Depende do ML? | Quando fazer |
|-------|----------------|--------------|
| Login (Clerk) | Não | Agora |
| Stripe (1 produto) | Não | Logo após login |
| Admin — usuários | Não | Junto com Stripe |
| Admin — pontos a revisar | Não | Quando quiser organizar |
| Banco de dados | Não | Agora |
| API ML | Sim | Depois da base pronta |

Você pode começar a vender com login + Stripe + admin, mesmo antes de integrar o ML. Quando a API estiver pronta, é só conectar nas ferramentas que já existem.
