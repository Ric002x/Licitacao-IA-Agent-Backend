from datetime import datetime

from app.models.models import Enterprise, RpaScrapRequest
from app.schemas.requisicao import AtualizarRequisicao
from fastapi import APIRouter, HTTPException
from app.api.deps.session import SessionDep
from app.api.deps.auth import CurrentUser

router = APIRouter(prefix="/requisicoes", tags=["requisicoes"])


@router.get("/listar")
async def listar_requisicoes(
    db: SessionDep, current_user: CurrentUser, enterprise_id: str = ""
):
    requisicoes = db.query(RpaScrapRequest).filter(
        RpaScrapRequest.enterprise_id == enterprise_id,
        Enterprise.user_id == current_user.id,
        RpaScrapRequest.deleted_at.is_(None)
    ).join(Enterprise.user).order_by(RpaScrapRequest.created_at.desc()).all()

    if not requisicoes or len(requisicoes) <= 0:
        raise HTTPException(
            404, "nenhuma requisicao encontrada"
        )

    return [
        requisicao.data for requisicao in requisicoes
    ]


@router.put("/atualizar")
async def atualizar_requisicao(
    db: SessionDep, current_user: CurrentUser, data: AtualizarRequisicao
):
    requisicao = db.query(RpaScrapRequest).filter(
        RpaScrapRequest.enterprise_id == data.enterprise_id,
        RpaScrapRequest.id == data.request_id,
        Enterprise.user_id == current_user.id
    ).join(RpaScrapRequest.enterprise).first()

    if not requisicao:
        raise HTTPException(
            404, "Requisição não encontrada"
        )

    filter_payload = {
        "palavras_chaves": data.palavras_chaves,
        "ufs": data.ufs,
        "modalidades_de_contratacao": data.modalidades_de_contratacao,
        "descricao_analise_ia": requisicao.enterprise.description
    }

    requisicao.title = data.titulo
    requisicao.filter_payload = filter_payload
    db.commit()
    db.refresh(requisicao)

    return requisicao.data


@router.delete("/deletar")
async def soft_delete_requisicao(
    db: SessionDep, current_user: CurrentUser,
    enterprise_id: str, request_id: str
):
    requisicao = db.query(RpaScrapRequest).filter(
        RpaScrapRequest.id == request_id,
        RpaScrapRequest.enterprise_id == enterprise_id,
        Enterprise.user_id == current_user.id,
        RpaScrapRequest.deleted_at.is_(None)
    ).join(RpaScrapRequest.enterprise).join(Enterprise.user).first()

    if not requisicao:
        raise HTTPException(
            404, "Requisição não encontrada"
        )

    requisicao.deleted_at = datetime.now()
    db.commit()
    db.refresh(requisicao)

    return {"message": "requisição deletada com sucesso"}
