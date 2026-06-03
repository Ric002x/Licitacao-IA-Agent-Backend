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

    response = client.models.generate_content_stream(
        model="gemini-3-flash-preview",
        contents=content
    )

    for chunk in response:
        if chunk.text:
            yield chunk.text
            await asyncio.sleep(0)
