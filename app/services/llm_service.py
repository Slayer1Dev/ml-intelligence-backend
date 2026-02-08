import json
import os
import re
import logging
from openai import OpenAI

logger = logging.getLogger("LLM")

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Cria o client OpenAI de forma lazy; evita crash na inicialização se OPENAI_API_KEY não existir."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY não configurada. Configure a variável de ambiente no Railway ou no .env."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def extract_json(text: str):
    logger.debug("RAW LLM TEXT:\n%s", text)

    text = (text or "").strip()

    # remove ```json e ```
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    logger.debug("SANITIZED TEXT:\n%s", text)

    return json.loads(text)


def run_market_analysis(prompt: str):
    """Envia prompt ao LLM e retorna JSON. Tenta Responses API, fallback para Chat Completions."""
    logger.info("Enviando prompt ao LLM")
    client = _get_client()
    raw_text = ""

    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        for output in response.output:
            if output.type == "message":
                for content in output.content:
                    if content.type == "output_text":
                        raw_text += content.text
    except Exception as e1:
        logger.warning("Responses API falhou (%s), tentando Chat Completions", e1)
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = (r.choices[0].message.content or "").strip()
        except Exception as e2:
            raise RuntimeError(f"LLM indisponível: {e2}") from e2

    if not raw_text:
        raise RuntimeError("LLM retornou resposta vazia")
    logger.debug("Resposta bruta do LLM:\n%s", raw_text)
    try:
        return extract_json(raw_text)
    except Exception as e:
        logger.exception("Falha ao converter resposta do LLM para JSON")
        return {"error": "Resposta da IA não é JSON válido", "raw": raw_text}


def run_chat(prompt: str, system_hint: str | None = None) -> str:
    """Envia prompt ao LLM e retorna resposta em texto livre (para perguntas, respostas a clientes)."""
    logger.info("Enviando prompt ao LLM (chat)")
    client = _get_client()
    messages = []
    if system_hint:
        messages.append({"role": "system", "content": system_hint})
    messages.append({"role": "user", "content": prompt})

    try:
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        raw_text = (r.choices[0].message.content or "").strip()
    except Exception as e:
        raise RuntimeError(f"LLM indisponível: {e}") from e

    if not raw_text:
        raise RuntimeError("LLM retornou resposta vazia")
    return raw_text
