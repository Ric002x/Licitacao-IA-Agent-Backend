"""
Router para rotas de licitações
"""
import asyncio

from app.service.agentes.agente_rating_detail import analise_ia_detail
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.licitacoes import DescricaoIA, FiltroLicitacao
from app.service.scrapping import iniciar_rpa_background
from app.api.deps import SessionDep, CurrentUser
from app.models.models import (
    RpaIARating, RpaScrapRequest, RpaScrapEvent, RpaRequestStepEnum,
    RpaRequestStatusEnum, RpaScrapResult
)
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/licitacoes", tags=["licitacoes"])


@router.get("/")
async def listar_licitacoes(db: SessionDep):
    """Lista todas as licitações"""
    return {"message": "Lista de licitações", "data": []}


@router.post("/procurar")
async def procurar_licitacoes(
    filtro: FiltroLicitacao, current_user: CurrentUser,
    db: SessionDep
):
    """
    Solicita uma requisição para procurar licitações em background.

    O usuário logado pode criar uma nova requisição ou tentar novamente uma
    existente com os mesmos filtros.
    A busca ocorre em segundo plano enquanto o status é retornado imediatamente

    Args:
        filtro: Filtros para a busca de licitações.
        current_user: Usuário autenticado.
        db: Sessão do banco de dados.

    Returns:
        Status da requisição com ID para acompanhamento.
    """
    # Pesquisa se há uma solicitação de busca existente, se não, cria uma nova.
    filter_payload = {
        "palavra_chave": filtro.palavra_chave,
        "ufs": filtro.ufs,
        "modalidades": filtro.modalidades_de_contratacao,
        "descriccao_para_ia": filtro.descricao_analise_ia
    }

    if filtro.request_id:
        requisicao = db.query(RpaScrapRequest).filter(
            RpaScrapRequest.requested_by_user_id == current_user.id,
            RpaScrapRequest.id == filtro.request_id
        ).first()

        if not requisicao:
            raise HTTPException(
                status_code=404,
                detail="Requisição não encontrada para este id")

        requisicao.filter_payload = filter_payload
        db.commit()
        db.refresh(requisicao)

        status = db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == str(requisicao.id)
        ).first()

        if not status:
            raise HTTPException(
                status_code=404, detail="Status da requisição não encontrado")

        status.step = RpaRequestStepEnum.PENDING
        status.status = RpaRequestStatusEnum.PENDING
        status.message = "reiniciando..."

    else:
        requisicao = RpaScrapRequest(
            title=f"Busca: {filtro.palavra_chave or 'Sem filtro'}",
            requested_by_user_id=current_user.id,
            filter_payload=filter_payload
        )
        db.add(requisicao)
        db.commit()
        db.refresh(requisicao)

        status = RpaScrapEvent(
            request_id=str(requisicao.id),
            message="iniciando...",
            step=RpaRequestStepEnum.PENDING,
            status=RpaRequestStatusEnum.PENDING
        )
        db.add(status)

    db.commit()
    db.refresh(status)

    asyncio.create_task(
        iniciar_rpa_background(db, filtro, str(requisicao.id))
    )

    return {
        "request_id": str(requisicao.id),
        "status": status.status.value,
        "step": status.step.value,
        "message": status.message,
        "created_at": requisicao.created_at.isoformat()
    }


@router.get("/status/{request_id}")
async def status_licitacao(
        current_user: CurrentUser, request_id: str, db: SessionDep):
    """Obtém os detalhes de uma licitação específica"""
    status = db.query(RpaScrapEvent).filter(
        RpaScrapEvent.request_id == request_id,
        RpaScrapRequest.requested_by_user_id == current_user.id

    ).first()

    if not status:
        raise HTTPException(
            404,
            f"Detalhes da solicitação de id {request_id} não foram encontrados"
        )

    return {
        "message": f"Detalhes da solicitação de id {request_id}",
        "data": status
    }


@router.get("/resultado/{request_id}")
async def resultado_licitacoes(
        current_user: CurrentUser, request_id: str, db: SessionDep):
    resultados = (
        db.query(
            RpaScrapResult.id,
            RpaScrapResult.payload,
            RpaScrapResult.created_at,
            RpaIARating.score,
            RpaIARating.rating_detail,
        )
        .join(RpaIARating, RpaIARating.result_id == RpaScrapResult.id)
        .filter(RpaScrapResult.request_id == request_id,
                RpaScrapRequest.requested_by_user_id == current_user.id)
        .order_by(RpaIARating.score.desc())
        .all()
    )

    if not resultados:
        return {"message": "requisição não encontrada para esse id"}

    return [
        {
            "id": str(r.id),
            "payload": r.payload,
            "created_at": r.created_at,
            "score": r.score,
            "rating_detail": r.rating_detail
        }
        for r in resultados
    ]


@router.post("/descricao_ia")
async def gerar_descricao_ia(
    current_user: CurrentUser, db: SessionDep, descricao_ia: DescricaoIA,
    background_tasks: BackgroundTasks
):
    resultado = (
        db.query(
            RpaScrapResult.payload,
            RpaScrapRequest.filter_payload,
            RpaIARating.rating_detail
        )
        .join(RpaScrapResult.request)
        .filter(
            RpaScrapResult.id == descricao_ia.result_id,
            RpaScrapRequest.requested_by_user_id == current_user.id
        )
        .first()
    )

    if not resultado:
        raise HTTPException(
            404, "Licitacão não encontrada"
        )

    def salvar_no_banco(texto_completo: str):
        rating = db.query(RpaIARating).filter(
            RpaIARating.result_id == descricao_ia.result_id).first()
        if rating:
            rating.rating_detail = texto_completo
            db.commit()

    async def gerador_resposta():
        texto_acumulado = []

        for chunk in analise_ia_detail(resultado):
            texto_acumulado.append(chunk)
            yield chunk

        texto_final = "".join(texto_acumulado)
        background_tasks.add_task(salvar_no_banco, texto_final)

    return StreamingResponse(gerador_resposta(), media_type="text/plain")
