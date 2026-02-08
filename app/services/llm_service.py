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
    logger.info("Enviando prompt ao LLM")

    client = _get_client()
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    # ✅ EXTRAÇÃO CORRETA DO TEXTO
    raw_text = ""

    for output in response.output:
        if output.type == "message":
            for content in output.content:
                if content.type == "output_text":
                    raw_text += content.text

    if not raw_text:
        raise RuntimeError("LLM retornou resposta vazia")

    logger.debug("Resposta bruta do LLM:\n%s", raw_text)

    try:
        return extract_json(raw_text)
    except Exception as e:
        logger.exception("Falha ao converter resposta do LLM para JSON")
        return {
            "error": "Resposta da IA não é JSON válido",
            "raw": raw_text
        }
