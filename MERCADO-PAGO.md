# Integração Mercado Pago (Assinaturas)

## 1. Criar conta e aplicação

1. Acesse [Mercado Pago Developers](https://www.mercadopago.com.br/developers)
2. Crie uma conta de vendedor (ou use a existente)
3. Em **Suas integrações** → crie uma nova aplicação
4. Anote o **Access Token** (credenciais de produção)

## 2. Variáveis de ambiente (Railway)

| Variável        | Descrição                           | Exemplo                     |
|-----------------|-------------------------------------|-----------------------------|
| `MP_ACCESS_TOKEN` | Access Token da aplicação Mercado Pago | `APP_USR-xxxx...`           |
| `MP_PLAN_VALUE`   | Valor mensal em BRL (opcional)       | `29.90` (padrão)            |
| `MP_PLAN_REASON`  | Nome do plano (opcional)             | `ML Intelligence - Plano Pro Mensal` |
| `BACKEND_URL`     | URL base do backend para webhook     | `https://www.mercadoinsights.online` |

## 3. Webhook

O webhook é configurado **automaticamente** ao criar cada plano de assinatura. A URL usada é:

```
{BACKEND_URL}/api/mercado-pago-webhook
```

Se `BACKEND_URL` não estiver definida, usa a URL da requisição. Em produção, defina `BACKEND_URL` para garantir que o webhook aponte para o domínio correto.

**Alternativa:** Se o Mercado Pago exigir configuração manual, acesse Suas integrações → Webhooks e adicione a URL acima com o evento **Planos e assinaturas** (`subscription_preapproval`).

## 4. Testar

1. Deploy no Railway com as variáveis configuradas
2. Acesse o dashboard como usuário free
3. Clique em **Assinar agora** → redireciona para o checkout Mercado Pago
4. Use cartões de teste: [Cartões de teste Mercado Pago](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/test/cards)
5. Após o pagamento, você retorna ao dashboard e o plano é ativado via webhook

## 5. Diferença em relação ao Stripe

- Não exige comprovante de residência para abrir conta
- Pagamentos em BRL nativos
- Aceita Pix, cartão, boleto
- Integração com ecossistema Mercado Livre
