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


def get_telegram_bot_username() -> Optional[str]:
    """Obtém o @username do bot via getMe. Retorna None se falhar."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") and data.get("result", {}).get("username"):
                return f"@{data['result']['username']}"
    except Exception:
        pass
    return None


def send_telegram_test_message(chat_id: str):
    """Envia mensagem de teste no Telegram. Retorna (sucesso, mensagem)."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN não configurado no servidor."
    if not chat_id or not str(chat_id).strip():
        return False, "Chat ID não vinculado. Vincule primeiro na página de configurações."
    text = "✅ Mercado Insights — Teste de notificação\n\nSua conexão com o Telegram está funcionando corretamente!"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id.strip(), "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "Mensagem enviada! Verifique seu Telegram."
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        raw_msg = err.get("description", resp.text[:200]) or f"Erro {resp.status_code}"
        # Mensagem específica para "chat not found" - causa mais comum
        if "chat not found" in raw_msg.lower() or "chat_id" in raw_msg.lower():
            bot_user = get_telegram_bot_username()
            hint = f" Abra o Telegram, procure o bot {bot_user} e envie /start." if bot_user else " Abra o Telegram, procure o bot do Mercado Insights (criado no @BotFather) e envie /start."
            return False, f"Chat não encontrado. Você precisa iniciar uma conversa com o bot antes.{hint} Depois tente novamente."
        return False, raw_msg
    except Exception as e:
        return False, str(e)


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
