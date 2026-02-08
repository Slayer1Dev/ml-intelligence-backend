# app/auth.py — Integração Clerk com FastAPI
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi.security import HTTPBearer

load_dotenv()

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY")
CLERK_FRONTEND_API = os.getenv("CLERK_FRONTEND_API")

# Quando Clerk configurado: valida JWT. Senão: permite acesso sem token (dev).
clerk_auth_guard = None
if CLERK_JWKS_URL:
    from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer

    clerk_config = ClerkConfig(jwks_url=CLERK_JWKS_URL)
    clerk_auth_guard = ClerkHTTPBearer(config=clerk_config)
else:
    clerk_auth_guard = HTTPBearer(auto_error=False)


def get_clerk_config() -> dict:
    """Retorna a config do Clerk para o frontend (publishable key e frontend API)."""
    return {
        "publishableKey": CLERK_PUBLISHABLE_KEY or "",
        "frontendApi": CLERK_FRONTEND_API or "",
    }
