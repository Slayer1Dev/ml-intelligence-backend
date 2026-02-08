# app/services/notification_service.py — Notificações (Telegram, e-mail) para perguntas nos anúncios
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import requests

logger = logging.getLogger("ml-intelligence")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FRONTEND_URL = (os.getenv("FRONTEND_URL") or os.getenv("BACKEND_URL") or "").strip().rstrip("/")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SMTP_USER = os.getenv("EMAIL_SMTP_USER")
EMAIL_SMTP_PASSWORD = os.getenv("EMAIL_SMTP_PASSWORD")


def send_question_notification(
    chat_id: str,
    pergunta_preview: str,
    resposta_preview: str,
    link_path: str = "/frontend/perguntas-anuncios.html",
) -> bool:
    """Envia notificação no Telegram sobre nova pergunta com resposta sugerida. Retorna True se enviou."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    text = (
        "📩 Nova pergunta no seu anúncio (ML)\n\n"
        "Pergunta: " + (pergunta_preview[:200] + "…" if len(pergunta_preview) > 200 else pergunta_preview) + "\n\n"
        "Resposta sugerida pela IA:\n" + (resposta_preview[:300] + "…" if len(resposta_preview) > 300 else resposta_preview) + "\n\n"
    )
    if FRONTEND_URL:
        text += "Aprove ou edite: " + FRONTEND_URL + link_path
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("Telegram send failed: %s %s", resp.status_code, resp.text[:200])
            return False
        return True
    except Exception as e:
        logger.warning("Telegram notification error: %s", e)
        return False


def send_question_notification_email(
    to_email: str,
    pergunta_preview: str,
    resposta_preview: str,
    link_path: str = "/frontend/perguntas-anuncios.html",
) -> bool:
    """Fallback: envia e-mail sobre nova pergunta quando Telegram não está vinculado."""
    if not all([EMAIL_FROM, EMAIL_SMTP_HOST, to_email]):
        return False
    link = (FRONTEND_URL + link_path) if FRONTEND_URL else ""
    body = (
        "Nova pergunta no seu anúncio (Mercado Livre)\n\n"
        "Pergunta: " + (pergunta_preview[:300] + "…" if len(pergunta_preview) > 300 else pergunta_preview) + "\n\n"
        "Resposta sugerida pela IA:\n" + (resposta_preview[:500] + "…" if len(resposta_preview) > 500 else resposta_preview) + "\n\n"
    )
    if link:
        body += "Aprove ou edite: " + link + "\n"
    try:
        msg = MIMEMultipart()
        msg["Subject"] = "ML Intelligence — Nova pergunta no anúncio"
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as s:
            if EMAIL_SMTP_USER and EMAIL_SMTP_PASSWORD:
                s.starttls()
                s.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
            s.sendmail(EMAIL_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.warning("Email notification error: %s", e)
        return False
