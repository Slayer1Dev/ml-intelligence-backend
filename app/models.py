# app/models.py — Modelos User e Subscription
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    plan = Column(String(32), default="free")  # free | active
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    ml_token = relationship("MlToken", back_populates="user", uselist=False)


class MlToken(Base):
    """Tokens OAuth do Mercado Livre por usuário."""
    __tablename__ = "ml_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    access_token = Column(String(512), nullable=False)
    refresh_token = Column(String(512), nullable=False)
    seller_id = Column(String(64), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ml_token")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = Column(String(128), nullable=True)
    status = Column(String(32), default="active")  # active | canceled | past_due
    started_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")


class ItemCost(Base):
    """Custos customizados por anúncio (embalagem, frete, imposto, custo) — painel financeiro."""
    __tablename__ = "item_costs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(String(64), nullable=False, index=True)
    sku = Column(String(128), nullable=True)
    custo_produto = Column(Float, nullable=True)
    embalagem = Column(Float, default=0)
    frete = Column(Float, default=0)
    taxa_pct = Column(Float, nullable=True)
    imposto_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="item_costs")
