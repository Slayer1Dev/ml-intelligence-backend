# app/services/mercado_pago_service.py — Integração Mercado Pago (Assinaturas)
import os
from datetime import datetime
from typing import Optional

import requests
from sqlalchemy.orm import Session

from app.models import Subscription, User

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
_raw_value = (os.getenv("MP_PLAN_VALUE") or "29.90").strip().replace(",", ".")
MP_PLAN_VALUE = float(_raw_value) if _raw_value else 29.90
MP_PLAN_REASON = os.getenv("MP_PLAN_REASON", "ML Intelligence - Plano Pro Mensal")

MP_API = "https://api.mercadopago.com"


def create_checkout_url(
    clerk_user_id: str, success_url: str, cancel_url: str, webhook_url: Optional[str] = None
) -> Optional[str]:
    """Cria plano de assinatura no Mercado Pago e retorna URL do checkout (init_point)."""
    if not MP_ACCESS_TOKEN:
        return None

    payload = {
        "reason": MP_PLAN_REASON,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": MP_PLAN_VALUE,
            "currency_id": "BRL",
        },
        "payment_methods_allowed": {
            "payment_types": [],
            "payment_methods": [],
        },
        "back_url": success_url,
        "external_reference": clerk_user_id,
    }
    if webhook_url:
        payload["notification_url"] = webhook_url

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    resp = requests.post(f"{MP_API}/preapproval_plan", json=payload, headers=headers, timeout=15)
    if resp.status_code != 201:
        return None

    data = resp.json()
    return data.get("init_point")


def get_preapproval(preapproval_id: str) -> Optional[dict]:
    """Busca dados de uma assinatura (preapproval) no Mercado Pago."""
    if not MP_ACCESS_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    resp = requests.get(f"{MP_API}/preapproval/{preapproval_id}", headers=headers, timeout=10)
    if resp.status_code != 200:
        return None
    return resp.json()


def get_preapproval_plan(plan_id: str) -> Optional[dict]:
    """Busca dados de um plano no Mercado Pago."""
    if not MP_ACCESS_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    resp = requests.get(f"{MP_API}/preapproval_plan/{plan_id}", headers=headers, timeout=10)
    if resp.status_code != 200:
        return None
    return resp.json()


def handle_preapproval_created(preapproval: dict, db: Session) -> None:
    """Processa assinatura criada/authorized: ativa o usuário."""
    preapproval_id = preapproval.get("id")
    status = preapproval.get("status", "")
    if status not in ("authorized", "pending"):
        return

    clerk_user_id = preapproval.get("external_reference")
    if not clerk_user_id:
        plan_id = preapproval.get("preapproval_plan_id")
        if plan_id:
            plan = get_preapproval_plan(plan_id)
            if plan:
                clerk_user_id = plan.get("external_reference")

    if not clerk_user_id:
        return

    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        return

    user.plan = "active"
    user.updated_at = datetime.utcnow()

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub:
        sub.stripe_subscription_id = preapproval_id  # reusando coluna para MP
        sub.status = "active"
        sub.started_at = datetime.utcnow()
    else:
        db.add(Subscription(
            user_id=user.id,
            stripe_subscription_id=preapproval_id,
            status="active",
            started_at=datetime.utcnow(),
        ))
    db.commit()


def handle_preapproval_updated(preapproval: dict, db: Session) -> None:
    """Processa atualização de assinatura (cancelada, etc)."""
    preapproval_id = preapproval.get("id")
    status = preapproval.get("status", "")

    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == preapproval_id).first()
    if not sub or not sub.user:
        return

    if status in ("cancelled", "paused", "pending"):
        sub.user.plan = "free"
        sub.user.updated_at = datetime.utcnow()
        sub.status = "canceled"
        sub.ends_at = datetime.utcnow()
    else:
        sub.user.plan = "active"
        sub.user.updated_at = datetime.utcnow()
        sub.status = status
    db.commit()
