def analyze_market(produto, concorrentes):
    if not concorrentes:
        return {
            "resumo": "Nenhum concorrente encontrado para análise.",
            "insights": []
        }

    concorrentes_ordenados = sorted(
        concorrentes,
        key=lambda x: x.get("vendas", 0),
        reverse=True
    )

    lider = concorrentes_ordenados[0]

    insights = []

    insights.append(
        f"O anúncio líder é '{lider.get('anuncio')}' com {lider.get('vendas')} vendas."
    )

    if lider.get("envio") == "Full":
        insights.append("O líder utiliza Mercado Envios Full, o que melhora conversão.")

    if lider.get("preco") and produto:
        try:
            preco_produto = float(produto[0].get("preco", 0))
            preco_lider = float(lider.get("preco", 0))

            if preco_lider < preco_produto:
                insights.append(
                    f"O líder vende mais barato (R${preco_lider}) que seu produto (R${preco_produto})."
                )
        except Exception:
            pass

    return {
        "lider": lider,
        "insights": insights
    }
from app.services.profit_calculator import calculate_profit
from app.services.user_settings import get_settings

def analyze_uploaded_sheet(records, user_id=None):
    settings = get_settings(user_id or "")

    results = []

    for item in records:
        results.append(calculate_profit(item, settings))

    return results
