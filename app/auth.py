# app/auth.py — Integração Clerk com FastAPI
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi.security import HTTPBearer

# Carrega .env da raiz do projeto (utf-8-sig evita BOM no Windows)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_encoding = "utf-8-sig"
for _env_name in (".env", ".env.txt"):  # .env.txt = comum no Windows (extensões ocultas)
    _env_path = _PROJECT_ROOT / _env_name
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path, encoding=_encoding)
        if os.getenv("CLERK_PUBLISHABLE_KEY"):
            break

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
