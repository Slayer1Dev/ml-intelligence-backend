import os
import requests

ML_APP_ID = os.getenv("ML_APP_ID")
ML_SECRET = os.getenv("ML_SECRET")
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

def get_auth_url():
    return (
        f"https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={ML_APP_ID}"
        f"&redirect_uri={ML_REDIRECT_URI}"
    )

def get_access_token(code):
    url = "https://api.mercadolibre.com/oauth/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_APP_ID,
        "client_secret": ML_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }

    response = requests.post(url, data=payload)
    return response.json()
