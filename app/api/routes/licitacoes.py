"""
Router para rotas de licitações
"""
import asyncio

from app.service.agentes.agente_rating_detail import analise_ia_detail
from app.service.scrapping import (
    pegar_detalhes_licitacao, pegar_licitacoes_base)
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.licitacoes import (
    AtualizarBusca, BuscaLicitacoes, DescricaoIA, FiltroLicitacao,
    RepetirBuscaLicitacoes)
from app.api.deps.session import SessionDep
from app.api.deps.auth import CurrentUser
from app.models.models import (
    Enterprise, RpaIARating, RpaRequestStatusEnum, RpaRequestStepEnum,
    RpaScrapRequest, RpaScrapEvent, RpaScrapResult
)
from fastapi.responses import JSONResponse, StreamingResponse


router = APIRouter(prefix="/licitacoes", tags=["licitacoes"])


@router.post("/nova-busca", status_code=201)
async def buscar_novas_licitacoes(
    data: BuscaLicitacoes, current_user: CurrentUser,
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
    empresa = db.query(Enterprise).filter(
        Enterprise.id == data.enterprise_id,
        Enterprise.user_id == str(current_user.id),
        Enterprise.deleted_at.is_(None)
    ).first()

    if not empresa:
        raise HTTPException(
            404, "Empresa não encontrada"
        )

    filter_payload = {
        "palavras_chaves": empresa.keywords,
        "ufs": empresa.ufs,
        "modalidades_de_contratacao": empresa.contraction_methods,
        "descricao_analise_ia": empresa.description
    }

    requisicao = RpaScrapRequest(
        title=empresa.keywords[0] or 'Sem filtro',
        enterprise_id=empresa.id,
        filter_payload=filter_payload
    )
    db.add(requisicao)
    db.commit()

    status = RpaScrapEvent(
        request_id=str(requisicao.id),
        message="iniciando...",
        step=RpaRequestStepEnum.PENDING,
        status=RpaRequestStatusEnum.PENDING
    )

    db.add(status)
    db.commit()

    novo_filtro = FiltroLicitacao(**filter_payload)

    asyncio.create_task(
        pegar_licitacoes_base(novo_filtro, requisicao, page=1)
    )

    return requisicao.data


@router.put("/resetar-busca")
async def repetir_busca_licitacoes(
        data: RepetirBuscaLicitacoes,
        current_user: CurrentUser, db: SessionDep):

    requisicao = (
        db.query(RpaScrapRequest)
        .join(RpaScrapRequest.enterprise)
        .join(Enterprise.user)
        .filter(
            RpaScrapRequest.id == data.request_id,
            RpaScrapRequest.enterprise_id == data.enterprise_id,
            Enterprise.user_id == current_user.id,
            RpaScrapRequest.deleted_at.is_(None)
        ).first()
    )

    if not requisicao:
        raise HTTPException(
            404, "Requisição não encontrada")

    status = db.query(RpaScrapEvent).filter(
        RpaScrapEvent.request_id == str(requisicao.id)
    ).first()

    if not status:
        status = RpaScrapEvent(
            request_id=str(requisicao.id),
            message="reiniciando...",
            step=RpaRequestStepEnum.PENDING,
            status=RpaRequestStatusEnum.PENDING
        )
        db.add(status)

    status.step = RpaRequestStepEnum.PENDING
    status.status = RpaRequestStatusEnum.PENDING
    status.message = "reiniciando..."

    db.query(RpaScrapResult).filter(
        RpaScrapResult.request_id == requisicao.id
    ).delete()

    db.commit()
    db.refresh(requisicao)
    db.refresh(status)

    requisicao_payload = FiltroLicitacao(**requisicao.filter_payload)

    asyncio.create_task(
        pegar_licitacoes_base(requisicao_payload, requisicao, page=1)
    )

    return requisicao.data


@router.put("/atualizar-busca", status_code=201)
async def atualizar_busca(
        data: AtualizarBusca,
        current_user: CurrentUser, db: SessionDep
):
    requisicao = (
        db.query(RpaScrapRequest)
        .join(RpaScrapRequest.enterprise)
        .join(Enterprise.user)
        .filter(
            RpaScrapRequest.id == data.request_id,
            RpaScrapRequest.enterprise_id == data.enterprise_id,
            Enterprise.user_id == current_user.id,
            RpaScrapRequest.deleted_at.is_(None)
        ).first()
    )

    if not requisicao:
        raise HTTPException(
            404, "Requisição não encontrada")

    status = db.query(RpaScrapEvent).filter(
        RpaScrapEvent.request_id == str(requisicao.id)
    ).first()

    if not status:
        status = RpaScrapEvent(
            request_id=str(requisicao.id),
            message="buscando mais licitacoes...",
            step=RpaRequestStepEnum.PENDING,
            status=RpaRequestStatusEnum.PENDING
        )
        db.add(status)

    status.step = RpaRequestStepEnum.PENDING
    status.status = RpaRequestStatusEnum.PENDING
    status.message = "buscando mais licitacoes..."

    requisicao.current_page = requisicao.current_page + 1
    db.commit()
    db.refresh(requisicao)

    requisicao_payload = FiltroLicitacao(**requisicao.filter_payload)

    asyncio.create_task(
        pegar_licitacoes_base(
            requisicao_payload, requisicao,
            requisicao.current_page)
    )

    return {"message": "buscando por mais licitações"}


@router.get("/status-busca")
async def status_licitacao(
        current_user: CurrentUser, enterprise_id: str,
        request_id: str, db: SessionDep):
    """Obtém os detalhes de uma licitação específica"""
    status = (
        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id,
            RpaScrapRequest.enterprise_id == enterprise_id,
            Enterprise.user_id == current_user.id,
            RpaScrapRequest.deleted_at.is_(None)
        )
        .join(RpaScrapEvent.request).join(RpaScrapRequest.enterprise)
        .join(Enterprise.user).first()
    )

    if not status:
        raise HTTPException(
            404,
            f"Detalhes da solicitação de id {request_id} não foram encontrados"
        )

    return {
        "request_id": str(status.request_id),
        "step": status.step.value,
        "status": status.status.value,
        "message": status.message,
    }


@router.get("/listar")
async def resultado_licitacoes(
        current_user: CurrentUser, enterprise_id: str,
        request_id: str, db: SessionDep):
    resultados_q = (
        db.query(RpaScrapResult)
        .join(RpaScrapResult.request)
        .join(RpaScrapRequest.enterprise)
        .join(RpaScrapResult.rating)
        .filter(
            RpaScrapResult.request_id == request_id,
            RpaScrapRequest.enterprise_id == enterprise_id,
            Enterprise.user_id == current_user.id,
            RpaScrapRequest.deleted_at.is_(None)
        )
        .order_by(RpaIARating.score.desc(), RpaScrapResult.id.desc(),)
        .all()
    )

    total = len(resultados_q)

    if not resultados_q or not len(resultados_q) > 0:
        raise HTTPException(
            404, "resultados não encontrados para essa requisição"
        )

    return {
        "total": total,
        "licitacoes": [
            {
                "id": str(r.id),
                "payload": r.payload,
                "score": r.rating.score,
                "is_favorite": r.is_favorite,
            }
            for r in resultados_q
        ]
    }


@router.get("/detalhes")
async def detalhes_licitacao(
        db: SessionDep, current_user: CurrentUser,
        licitacao_id: str, search: str):
    licitacao = (
        db.query(RpaScrapResult)
        .join(RpaScrapResult.request)
        .join(RpaScrapRequest.enterprise)
        .join(Enterprise.user)
        .filter(
            RpaScrapResult.id == licitacao_id,
            Enterprise.user_id == current_user.id,
        )
        .first()
    )

    if not licitacao:
        raise HTTPException(
            404, "Licitação não encontrada"
        )

    if search == "true":
        if not licitacao.is_complete and not licitacao.is_loading:
            licitacao.is_loading = True
            licitacao.status = "processing"
            db.commit()
            db.refresh(licitacao)

            asyncio.create_task(
                pegar_detalhes_licitacao(licitacao.id)
            )

    return JSONResponse({
        "id": str(licitacao.id),
        "payload": licitacao.payload,
        "is_favorite": licitacao.is_favorite,
        "score": licitacao.rating.score,
        "rating_detail": licitacao.rating.rating_detail or "",
    })


@router.get("/detalhes/status")
async def detalhes_licitacao_status(
        db: SessionDep, current_user: CurrentUser, licitacao_id: str):
    licitacao = (
        db.query(RpaScrapResult)
        .join(RpaScrapResult.request)
        .join(RpaScrapRequest.enterprise)
        .join(Enterprise.user)
        .filter(
            RpaScrapResult.id == licitacao_id,
            Enterprise.user_id == current_user.id,
        )
        .first()
    )
    if not licitacao:
        raise HTTPException(
            404, "Licitação não encontrada"
        )

    return JSONResponse({
        "is_complete": licitacao.is_complete,
        "is_loading": licitacao.is_loading,
        "status": licitacao.status,
    })


@router.post("/descricao_ia")
async def gerar_descricao_ia(
    current_user: CurrentUser, db: SessionDep, descricao_ia: DescricaoIA,
    background_tasks: BackgroundTasks
):
    rating = db.query(RpaIARating).filter(
        RpaIARating.result_id == descricao_ia.result_id
    ).first()
    if not rating:
        raise HTTPException(
            404, "Licitacão não encontrada"
        )

    if rating.rating_detail:
        return {
            "message": "Descrição IA já feita para essa Licitação"
        }

    resultado = (
        db.query(
            RpaScrapResult.payload,
            RpaScrapRequest.filter_payload,
            RpaIARating.rating_detail
        )
        .join(RpaScrapResult.request)
        .join(RpaScrapRequest.enterprise)
        .join(Enterprise.user)
        .filter(
            RpaScrapResult.id == descricao_ia.result_id,
            Enterprise.user_id == current_user.id,
            RpaScrapRequest.deleted_at.is_(None)
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
        texto_acumulado: list[str] = []

        async for event in analise_ia_detail(resultado):  # noqa
            if getattr(event, "event_type", None) != "step.delta":
                continue

            delta = getattr(event, "delta", None)
            texto = getattr(delta, "text", None)
            if not isinstance(texto, str):
                continue

            texto_acumulado.append(texto)
            yield texto

        texto_final = "".join(texto_acumulado)
        background_tasks.add_task(salvar_no_banco, texto_final)

    return StreamingResponse(gerador_resposta(), media_type="text/plain")
