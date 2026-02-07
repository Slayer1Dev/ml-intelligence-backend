def normalize_concorrentes(concorrentes):
    normalized = []

    for c in concorrentes:
        try:
            preco = float(c.get("preco", 0))
        except:
            preco = 0.0

        try:
            vendas = int(c.get("vendas", 0))
        except:
            vendas = 0

        lider = str(c.get("lider", "")).lower() in ["sim", "true", "1"]

        score = 0
        score += vendas * 0.5
        score += 50 if lider else 0
        score += 30 if c.get("envio") == "Full" else 0

        normalized.append({
            "anuncio": c.get("anuncio"),
            "preco": preco,
            "vendas": vendas,
            "envio": c.get("envio"),
            "reputacao": c.get("reputacao"),
            "lider": lider,
            "score": round(score, 2)
        })

    return normalized
