def market_prompt(produto, concorrentes):
    return f"""
Você é um analista sênior de marketplaces (Mercado Livre Brasil).

Seu papel é transformar dados em decisão prática.

DADOS DISPONÍVEIS:

PRODUTO:
{produto}

CONCORRENTES:
{concorrentes}

OBJETIVO:
Identificar o líder de mercado e gerar ações claras para competir.

REGRAS ABSOLUTAS:
- Não invente dados
- Não use linguagem genérica
- Não explique conceitos
- Não use markdown
- Não inclua texto fora do JSON
- Nunca retorne arrays vazios

FORMATO DE RESPOSTA (JSON VÁLIDO OBRIGATÓRIO):

{{
  "lider": {{
    "anuncio": string,
    "preco": number,
    "vantagens": [string, string, string]
  }},
  "acoes_recomendadas": [
    string,
    string,
    string
  ],
  "alertas": [
    string,
    string
  ]
}}

CRITÉRIOS:
- "vantagens" deve explicar POR QUE o líder vende mais
- "acoes_recomendadas" devem ser executáveis imediatamente
- "alertas" devem indicar riscos reais de mercado

Retorne SOMENTE o JSON.
"""
