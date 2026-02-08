# app/services/stripe_service.py — Integração Stripe
import os
from datetime import datetime
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from app.models import Subscription, User

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(clerk_user_id: str, success_url: str, cancel_url: str) -> Optional[str]:
    """Cria sessão Stripe Checkout e retorna a URL. Retorna None se Stripe não configurado."""
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return None
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=clerk_user_id,
        metadata={"clerk_user_id": clerk_user_id},
    )
    return session.url


def handle_checkout_completed(session: dict, db: Session) -> None:
    """Processa checkout.session.completed: ativa o usuário e cria/atualiza subscription."""
    clerk_user_id = session.get("client_reference_id") or session.get("metadata", {}).get("clerk_user_id")
    if not clerk_user_id:
        return
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        return
    user.plan = "active"
    user.updated_at = datetime.utcnow()

    sub_id = session.get("subscription")
    if sub_id:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if sub:
            sub.stripe_subscription_id = sub_id
            sub.status = "active"
            sub.started_at = datetime.utcnow()
        else:
            db.add(Subscription(
                user_id=user.id,
                stripe_subscription_id=sub_id,
                status="active",
                started_at=datetime.utcnow(),
            ))
    db.commit()


def handle_subscription_deleted(subscription: dict, db: Session) -> None:
    """Processa customer.subscription.deleted: desativa o usuário."""
    sub_id = subscription.get("id")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    if not sub or not sub.user:
        return
    sub.user.plan = "free"
    sub.user.updated_at = datetime.utcnow()
    sub.status = "canceled"
    sub.ends_at = datetime.utcnow()
    db.commit()


def handle_subscription_updated(subscription: dict, db: Session) -> None:
    """Processa customer.subscription.updated: atualiza status da assinatura."""
    sub_id = subscription.get("id")
    status = subscription.get("status")
    sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == sub_id).first()
    if not sub or not sub.user:
        return
    sub.status = status
    if status in ("canceled", "unpaid", "past_due"):
        sub.user.plan = "free"
        sub.user.updated_at = datetime.utcnow()
        if subscription.get("canceled_at"):
            sub.ends_at = datetime.fromtimestamp(subscription["canceled_at"])
    else:
        sub.user.plan = "active"
        sub.user.updated_at = datetime.utcnow()
    db.commit()
