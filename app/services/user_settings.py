# app/services/user_settings.py

# memória simples (por enquanto)
USER_SETTINGS = {}

def get_settings(user_id: str):
    return USER_SETTINGS.get(user_id, {
        "taxa_padrao_percentual": 11,
        "frete_padrao": 20,
        "imposto_padrao": 5,
        "margem_desejada": 20
    })

def save_settings(user_id: str, data: dict):
    USER_SETTINGS[user_id] = data
    return data
