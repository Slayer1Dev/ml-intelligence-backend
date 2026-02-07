import pandas as pd

REQUIRED_COLUMNS = {
    "sku",
    "custo_produto",
    "preco_venda"
}

OPTIONAL_COLUMNS = {
    "frete": 0.0,
    "taxa": 0.0,
    "imposto": 0.0
}


def process_sheet(file_path: str):
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return {
            "error": "read_error",
            "message": str(e)
        }

    # normaliza nomes de coluna
    df.columns = (
        df.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_")
    )

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing:
        return {
            "error": "missing_columns",
            "missing_columns": missing
        }

    # garante colunas opcionais
    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default

    # remove linhas vazias
    df = df.dropna(subset=["sku", "custo_produto", "preco_venda"])

    records = df.to_dict(orient="records")

    return {
        "records": records,
        "rows": len(records)
    }
