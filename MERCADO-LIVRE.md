# Integração Mercado Livre OAuth

## 1. Variáveis de ambiente (Railway)

| Variável        | Descrição                                  | Onde encontrar                 |
|-----------------|--------------------------------------------|--------------------------------|
| `ML_APP_ID`     | App ID do app criado no ML Developers      | Painel do app → Credenciais    |
| `ML_SECRET`     | Secret do app                              | Painel do app → Credenciais    |
| `ML_REDIRECT_URI` | URL de redirect (igual à cadastrada no ML) | Ex: `https://www.mercadoinsights.online/frontend/callback-ml.html` |

## 2. URLs cadastradas no app ML

- **Redirect URI:** `https://www.mercadoinsights.online/frontend/callback-ml.html`
- **URL de notificações:** `https://www.mercadoinsights.online/api/ml-webhook`

## 3. Fluxo

1. Usuário clica em **Conectar Mercado Livre** no dashboard
2. É redirecionado para o OAuth do Mercado Livre
3. Após autorizar, retorna para `callback-ml.html?code=xxx`
4. A página envia o `code` ao backend, que troca por tokens e grava no banco
5. Usuário é redirecionado ao dashboard com mensagem de sucesso

## 4. Webhook de perguntas (implementado)

- **URL de notificações (tópico `questions`):** `https://seu-dominio/api/ml-webhook`
- Cadastre no DevCenter do app ML a URL acima e assine o tópico **questions** para receber avisos de novas perguntas nos anúncios.
- O backend responde 200 em menos de 500 ms e processa em background (gera resposta com IA, enfileira para aprovação, envia notificação Telegram/e-mail).

## 5. Outros endpoints

- Chamadas à API do ML para buscar anúncios, vendas, métricas, **perguntas e respostas** (já implementados).
- Concorrentes: busca por termo (pode retornar 403 sem certificação); **adicionar concorrente por link/ID** (funciona sem certificação).
