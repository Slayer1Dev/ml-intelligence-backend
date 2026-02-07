import json
import re
import logging
from openai import OpenAI

logger = logging.getLogger("LLM")

client = OpenAI()


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
