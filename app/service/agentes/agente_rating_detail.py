import asyncio

from google import genai
from pathlib import Path


client = genai.Client()


BASE_DIR = Path(__file__).parent


def load_prompt(version="v1") -> str:
    path = BASE_DIR / "prompts" / "rates" / f"rating_{version}.txt"
    return path.read_text(encoding="utf-8")


async def analise_ia_detail(licitacao):
    """
    Avaliação da IA para descrição da licitação
    """
    PROMPT = load_prompt("v1")
    content = PROMPT.format(
        licitacao.filter_payload,
        licitacao.payload
    )

    response = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=content,
        stream=True
    )

    for chunk in response:
        if chunk:
            yield chunk
            await asyncio.sleep(0)
