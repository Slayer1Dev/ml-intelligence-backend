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
        # Busca active + paused + closed + under_review (inclui "inativo para revisar")
        all_results: List[str] = []
        all_paging = {"total": 0, "offset": 0, "limit": limit}
        for st in ["active", "paused", "closed", "under_review"]:
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
    Retorna dict com 'error' se houver falha, para melhor diagnóstico.
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
            # Tenta extrair mensagem de erro do ML
            error_detail = "Erro desconhecido"
            try:
                error_json = resp.json()
                error_detail = error_json.get("message") or error_json.get("error") or resp.text[:200]
            except Exception:
                error_detail = resp.text[:200]
            
            _log.warning("ML search failed: status=%s body=%s", resp.status_code, error_detail)
            
            # Retorna dict com informações do erro para diagnóstico
            return {
                "error": True,
                "status_code": resp.status_code,
                "message": error_detail,
                "detail": f"API ML retornou {resp.status_code}: {error_detail}"
            }
        return resp.json()
    except requests.RequestException as e:
        _log.warning("ML search request error: %s", e)
        return {
            "error": True,
            "status_code": 0,
            "message": str(e),
            "detail": f"Erro de conexão: {type(e).__name__}"
        }


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


# ------------------------------------------------------------------
# Perguntas e respostas nos anúncios (API ML)
# ------------------------------------------------------------------
def get_questions_search(
    access_token: str,
    seller_id: Optional[str] = None,
    item_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Optional[dict]:
    """Lista perguntas recebidas nos anúncios do vendedor.
    GET /questions/search?seller_id=... ou ?item=...&api_version=4
    """
    if not access_token or (not seller_id and not item_id):
        return None
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"api_version": "4", "limit": min(limit, 50), "offset": offset}
    if seller_id:
        params["seller_id"] = seller_id
    if item_id:
        params["item"] = item_id
    if status:
        params["status"] = status
    try:
        resp = requests.get(f"{ML_API}/questions/search", headers=headers, params=params, timeout=15)
        if resp.status_code != 200:
            _log.warning("ML questions search failed: status=%s body=%s", resp.status_code, resp.text[:200])
            return None
        return resp.json()
    except requests.RequestException as e:
        _log.warning("ML questions search error: %s", e)
        return None


def get_question_detail(access_token: str, question_id: str) -> Optional[dict]:
    """Detalhe de uma pergunta (inclui dados do comprador quando aplicável)."""
    if not access_token or not question_id:
        return None
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(f"{ML_API}/questions/{question_id}", headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        return resp.json()
    except requests.RequestException as e:
        _log.warning("ML question detail error: %s", e)
        return None


def post_answer(access_token: str, question_id: str, text: str) -> Optional[dict]:
    """Publica resposta a uma pergunta. POST /answers."""
    if not access_token or not question_id or not (text or "").strip():
        return None
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"question_id": question_id, "text": (text or "").strip()}
    try:
        resp = requests.post(f"{ML_API}/answers", headers=headers, json=payload, timeout=15)
        if resp.status_code not in (200, 201):
            _log.warning("ML post answer failed: status=%s body=%s", resp.status_code, resp.text[:200])
            return None
        return resp.json() if resp.text else {}
    except requests.RequestException as e:
        _log.warning("ML post answer error: %s", e)
        return None


def get_item_by_id(access_token: Optional[str], item_id: str) -> Optional[dict]:
    """Busca um item por ID. Tenta com token; se 403, tenta sem token (itens públicos).
    Retorna dict com 'error' se houver falha, para melhor diagnóstico."""
    if not item_id:
        return None
    headers = {"User-Agent": "MLIntelligence/1.0 (https://mercadoinsights.online)"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        resp = requests.get(f"{ML_API}/items/{item_id}", headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 403 and access_token:
            headers.pop("Authorization", None)
            resp2 = requests.get(f"{ML_API}/items/{item_id}", headers=headers, timeout=15)
            if resp2.status_code == 200:
                return resp2.json()
            _log.warning("ML get item %s failed (public): status=%s", item_id, resp2.status_code)
            # Retorna dict com informações do erro
            error_detail = "Erro desconhecido"
            try:
                error_json = resp2.json()
                error_detail = error_json.get("message") or error_json.get("error") or resp2.text[:200]
            except Exception:
                error_detail = resp2.text[:200]
            
            return {
                "error": True,
                "status_code": resp2.status_code,
                "message": error_detail,
                "detail": f"API ML retornou {resp2.status_code}: {error_detail}"
            }
        
        # Extrai detalhes do erro
        error_detail = "Erro desconhecido"
        try:
            error_json = resp.json()
            error_detail = error_json.get("message") or error_json.get("error") or resp.text[:200]
        except Exception:
            error_detail = resp.text[:200]
        
        _log.warning("ML get item %s failed: status=%s body=%s", item_id, resp.status_code, error_detail)
        return {
            "error": True,
            "status_code": resp.status_code,
            "message": error_detail,
            "detail": f"API ML retornou {resp.status_code}: {error_detail}"
        }
    except requests.RequestException as e:
        _log.warning("ML get item error: %s", e)
        return {
            "error": True,
            "status_code": 0,
            "message": str(e),
            "detail": f"Erro de conexão: {type(e).__name__}"
        }
