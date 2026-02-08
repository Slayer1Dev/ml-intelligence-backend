# app/services/user_service.py — Sincroniza usuários Clerk com o banco local
from app.database import SessionLocal
from app.models import User


def get_or_create_user(clerk_user_id: str, email: str | None = None) -> User:
    """Retorna usuário existente ou cria novo. Use após validar JWT do Clerk."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if user:
            if email and user.email != email:
                user.email = email
                db.commit()
                db.refresh(user)
            return user
        user = User(clerk_user_id=clerk_user_id, email=email, plan="free")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()
