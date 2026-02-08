import os
from datetime import datetime, timedelta
from typing import Optional

import requests

ML_APP_ID = os.getenv("ML_APP_ID")
ML_SECRET = os.getenv("ML_SECRET")
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI")
ML_API = "https://api.mercadolibre.com"


def get_auth_url() -> Optional[str]:
    """Retorna URL para iniciar OAuth do Mercado Livre."""
    if not ML_APP_ID or not ML_REDIRECT_URI:
        return None
    return (
        f"https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={ML_APP_ID}"
        f"&redirect_uri={ML_REDIRECT_URI}"
    )


def exchange_code_for_tokens(code: str) -> Optional[dict]:
    """Troca code por access_token e refresh_token."""
    if not ML_APP_ID or not ML_SECRET or not ML_REDIRECT_URI:
        return None
    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_APP_ID,
        "client_secret": ML_SECRET,
        "code": code,
        "redirect_uri": ML_REDIRECT_URI,
    }
    resp = requests.post(f"{ML_API}/oauth/token", data=payload, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    """Atualiza access_token usando refresh_token."""
    if not ML_APP_ID or not ML_SECRET:
        return None
    payload = {
        "grant_type": "refresh_token",
        "client_id": ML_APP_ID,
        "client_secret": ML_SECRET,
        "refresh_token": refresh_token,
    }
    resp = requests.post(f"{ML_API}/oauth/token", data=payload, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()
