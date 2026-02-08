import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import requests

_log = logging.getLogger("ml-intelligence")

ML_APP_ID = os.getenv("ML_APP_ID")
ML_SECRET = os.getenv("ML_SECRET")
ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI")
ML_API = "https://api.mercadolibre.com"


def get_auth_url() -> Optional[str]:
    """Retorna URL para iniciar OAuth do Mercado Livre."""
    if not ML_APP_ID or not ML_REDIRECT_URI:
        return None
    # scope read+offline_access pode ajudar em endpoints como search
    return (
        f"https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code"
        f"&client_id={ML_APP_ID}"
        f"&redirect_uri={ML_REDIRECT_URI}"
        f"&scope=offline_access%20read"
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


def get_user_info(access_token: str) -> Optional[dict]:
    """Busca informações do usuário autenticado."""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{ML_API}/users/me", headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def get_user_items(access_token: str, user_id: str, status: str = "active", limit: int = 50, offset: int = 0) -> Optional[dict]:
    """Lista anúncios do usuário.
    
    Args:
        access_token: Token de acesso
        user_id: ID do usuário (seller_id)
        status: Status dos anúncios (active, paused, closed). Use "all" para buscar todos.
        limit: Quantidade de resultados por página (máx 50)
        offset: Offset para paginação
    """
    if status == "all":
        # Busca active + paused + closed e mescla (inclui "inativo para revisar" em paused)
        all_results: List[str] = []
        all_paging = {"total": 0, "offset": 0, "limit": limit}
        for st in ["active", "paused", "closed"]:
            r = get_user_items(access_token, user_id, status=st, limit=50, offset=0)
            if r and r.get("results"):
                all_results.extend(r["results"])
                p = r.get("paging", {})
                all_paging["total"] = all_paging.get("total", 0) + p.get("total", 0)
        return {"results": all_results, "paging": {"total": len(all_results), "offset": 0, "limit": limit}}
    
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "status": status,
        "limit": min(limit, 50),
        "offset": offset,
    }
    resp = requests.get(f"{ML_API}/users/{user_id}/items/search", headers=headers, params=params, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def get_item_details(access_token: str, item_id: str) -> Optional[dict]:
    """Busca detalhes de um anúncio específico."""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{ML_API}/items/{item_id}", headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def get_item_description(access_token: str, item_id: str) -> Optional[str]:
    """Busca a descrição de um anúncio."""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{ML_API}/items/{item_id}/description", headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    return data.get("plain_text", "")


def get_orders(access_token: str, seller_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> Optional[dict]:
    """Busca pedidos/vendas do vendedor.
    
    Args:
        access_token: Token de acesso
        seller_id: ID do vendedor
        status: Status do pedido (paid, confirmed, etc) - opcional
        limit: Quantidade de resultados por página
        offset: Offset para paginação
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "seller": seller_id,
        "limit": limit,
        "offset": offset,
    }
    if status:
        params["order.status"] = status
    
    resp = requests.get(f"{ML_API}/orders/search", headers=headers, params=params, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def get_order_details(access_token: str, order_id: str) -> Optional[dict]:
    """Busca detalhes de um pedido específico."""
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{ML_API}/orders/{order_id}", headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    return resp.json()


def search_public(
    site_id: str = "MLB",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    sort: Optional[str] = None,
    access_token: Optional[str] = None,
) -> Optional[dict]:
    """Busca no Mercado Livre. Funciona com ou sem token; com token tende a ser mais estável.
    
    Retorna anúncios do marketplace com: id, title, price, sold_quantity, permalink, etc.
    """
    if not q or not q.strip():
        return None
    params = {
        "q": q.strip()[:100],
        "limit": min(limit, 50),
        "offset": offset,
    }
    if sort:
        params["sort"] = sort
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    headers["User-Agent"] = "MLIntelligence/1.0 (https://mercadoinsights.online)"
    try:
        resp = requests.get(f"{ML_API}/sites/{site_id}/search", params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            _log.warning("ML search failed: status=%s body=%s", resp.status_code, resp.text[:200])
            return None
        return resp.json()
    except requests.RequestException as e:
        _log.warning("ML search request error: %s", e)
        return None


def get_multiple_items(access_token: str, item_ids: List[str]) -> Optional[List[dict]]:
    """Busca múltiplos itens de uma vez (máx 20 por requisição).
    
    A API do ML retorna [{code: 200, body: {...}}, ...]. Esta função
    extrai o body de cada resposta e retorna lista de itens.
    """
    if not item_ids:
        return []
    
    headers = {"Authorization": f"Bearer {access_token}"}
    ids_str = ",".join(item_ids[:20])  # ML limita a 20 por vez
    resp = requests.get(f"{ML_API}/items", headers=headers, params={"ids": ids_str}, timeout=15)
    if resp.status_code != 200:
        return None
    
    raw = resp.json()
    if not isinstance(raw, list):
        return []
    
    items = []
    for obj in raw:
        if isinstance(obj, dict) and obj.get("code") == 200 and "body" in obj:
            items.append(obj["body"])
    
    return items
