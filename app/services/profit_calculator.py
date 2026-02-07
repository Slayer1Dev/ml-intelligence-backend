def calculate_profit(item, settings):
    preco = item["preco_venda"]
    custo = item["custo_produto"]

    taxa = preco * settings["taxa_padrao_percentual"] / 100
    imposto = preco * settings["imposto_padrao"] / 100
    frete = settings["frete_padrao"]

    lucro = preco - custo - taxa - imposto - frete

    margem = (lucro / preco) * 100 if preco else 0

    return {
        "sku": item["sku"],
        "lucro_unitario": round(lucro, 2),
        "margem_percentual": round(margem, 2)
    }
