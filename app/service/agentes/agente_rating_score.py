from app.models.models import RpaIARating
from app.schemas.licitacoes import FiltroLicitacao
from google import genai
from sqlalchemy.orm import Session
import json
from pathlib import Path


client = genai.Client()


BASE_DIR = Path(__file__).parent


def load_prompt(version="v1") -> str:
    path = BASE_DIR / "prompts" / "scores" / f"scoring_{version}.txt"
    return path.read_text(encoding="utf-8")


def analise_ia(db: Session, filtro: FiltroLicitacao, resultados: list):
    """
    Avalição da IA atribuindo score para as licitações
    """
    lista = []
    for resultado in resultados:
        descricao = resultado.payload["descricao"]
        res_id = str(resultado.id)
        lista.append({
            "result_id": str(res_id),
            "descricao": descricao.get("descricao"),
            "modalidade_de_contratacao": descricao.get(
                "modalidade_de_contratacao"),
            "valor": descricao.get("valor_estimado"),
            "informacao_complementar": descricao.get("informacao_complementar")
        })

    PROMPT = load_prompt("v1")

    content = PROMPT.format(
        filtro.descricao_analise_ia,
        filtro.palavra_chave,
        lista
    )

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=content
    )

    if not response.text:
        return

    # Caso a IA traga a resposta do jeito correto:
    scores = json.loads(response.text)

    ratings = [
        RpaIARating(
            result_id=item["result_id"],
            score=item["score"]
        )
        for item in scores
    ]

    db.add_all(ratings)
    db.commit()
