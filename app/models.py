# app/models.py — Modelos User, Subscription, ItemCost (dados por usuário)
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id = Column(String(128), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    plan = Column(String(32), default="free")  # free | active
    telegram_chat_id = Column(String(64), nullable=True)  # para notificações de perguntas nos anúncios
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    stripe_subscription_id = Column(String(128), nullable=True)
    status = Column(String(32), default="active")  # active | canceled | past_due
    started_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")


class ItemCost(Base):
    """Custos e dados por anúncio por usuário (custo, embalagem, frete, imposto). Um registro por (user_id, item_id)."""
    __tablename__ = "item_costs"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_item_costs_user_item"),)

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


class AuditLog(Base):
    """Log de eventos (falhas de IA, etc.) para debug e admin."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # ia_insights_fail, ia_perguntas_fail, etc.
    message = Column(String(512), nullable=True)
    extra = Column(String(1024), nullable=True)  # JSON ou texto
    created_at = Column(DateTime, default=datetime.utcnow)


class PendingQuestion(Base):
    """Fila de perguntas (dos anúncios ML) com resposta sugerida pela IA, aguardando aprovação/edição do vendedor."""
    __tablename__ = "pending_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(64), nullable=False, unique=True, index=True)  # ID da pergunta no ML
    item_id = Column(String(64), nullable=True, index=True)
    item_title = Column(String(512), nullable=True)
    pergunta_texto = Column(String(2048), nullable=False)
    resposta_ia_sugerida = Column(String(2048), nullable=True)
    status = Column(String(32), default="pending")  # pending | approved | edited | published
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="pending_questions")


class QuestionAnswerFeedback(Base):
    """Feedback para aprendizado: pergunta + resposta final (aprovada ou editada) publicada no ML."""
    __tablename__ = "question_answer_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(64), nullable=False, index=True)
    item_id = Column(String(64), nullable=True, index=True)
    pergunta_texto = Column(String(2048), nullable=False)
    resposta_ia_sugerida = Column(String(2048), nullable=True)
    resposta_final_publicada = Column(String(2048), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="question_answer_feedback")


class CompetitorItem(Base):
    """Concorrentes cadastrados manualmente pelo vendedor (por link/ID) para comparação."""
    __tablename__ = "competitor_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_id = Column(String(64), nullable=False, index=True)  # ID do anúncio no ML
    nickname = Column(String(128), nullable=True)  # nome opcional para o vendedor identificar
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="competitor_items")
