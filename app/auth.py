# app/auth.py — Integração Clerk com FastAPI
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, List
import logging

if TYPE_CHECKING:
    from app.models import User

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import requests

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
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")

logger = logging.getLogger(__name__)

# Lista de e-mails admin (separados por vírgula) — lida em tempo de execução para refletir env após restart
def _get_admin_emails() -> List[str]:
    raw = os.getenv("ADMIN_EMAILS", "")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


ADMIN_EMAILS: List[str] = _get_admin_emails()  # usado por debug-admin e outros que precisam da lista

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


def _get_claims(credentials: HTTPAuthorizationCredentials | None):
    """Extrai claims do JWT. Requer credentials com .decoded (ClerkHTTPBearer)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )
    decoded = getattr(credentials, "decoded", None)
    if not decoded or not isinstance(decoded, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    return decoded


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(clerk_auth_guard)):
    """Retorna o User do banco a partir do JWT. Sincroniza com Clerk via get_or_create_user."""
    from app.models import User
    from app.services.user_service import get_or_create_user

    claims = _get_claims(credentials)
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de usuário",
        )
    email = _extract_email_from_claims(claims)
    if not email and CLERK_SECRET_KEY:
        # Session token may not include email by default in production; fallback to Clerk Backend API.
        email = _fetch_email_from_clerk_api(clerk_user_id)
    return get_or_create_user(clerk_user_id, email)


def _extract_email_from_claims(claims: dict) -> str | None:
    """Extrai email dos claims do JWT em vários formatos possíveis."""
    raw = claims.get("email")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        s = raw.get("email_address") or raw.get("email")
        if isinstance(s, str) and s.strip():
            return s.strip()
    if isinstance(claims.get("email_addresses"), list) and claims["email_addresses"]:
        first = claims["email_addresses"][0]
        if isinstance(first, dict):
            s = first.get("email_address") or first.get("email")
            if isinstance(s, str) and s.strip():
                return s.strip()
    raw = claims.get("primary_email") or claims.get("primaryEmail")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _fetch_email_from_clerk_api(clerk_user_id: str) -> str | None:
    """Fetch user email from Clerk Backend API when JWT claims do not include it."""
    if not CLERK_SECRET_KEY:
        return None
    try:
        resp = requests.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            timeout=8,
        )
        if not resp.ok:
            logger.warning("Clerk user lookup failed: status=%s user_id=%s", resp.status_code, clerk_user_id)
            return None
        data = resp.json() or {}

        primary_id = data.get("primary_email_address_id")
        email_addresses = data.get("email_addresses")
        if isinstance(email_addresses, list):
            if primary_id:
                for item in email_addresses:
                    if isinstance(item, dict) and item.get("id") == primary_id:
                        value = item.get("email_address")
                        if isinstance(value, str) and value.strip():
                            return value.strip()
            for item in email_addresses:
                if isinstance(item, dict):
                    value = item.get("email_address")
                    if isinstance(value, str) and value.strip():
                        return value.strip()
    except Exception as e:
        logger.warning("Clerk user lookup error for %s: %s", clerk_user_id, e)
    return None


def get_admin_emails() -> List[str]:
    """Retorna a lista atual de e-mails admin (para diagnóstico)."""
    return _get_admin_emails()


def is_admin(email: str | None) -> bool:
    """Verifica se o e-mail está na lista de admins (lê ADMIN_EMAILS do env a cada chamada)."""
    if not email:
        return False
    admin_list = _get_admin_emails()
    return email.strip().lower() in admin_list


def admin_guard(user: "User" = Depends(get_current_user)):
    """Dependency que garante que o usuário é admin."""
    if not is_admin(user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user
