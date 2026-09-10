import json
import os
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from uuid import UUID

from app.core.db import SessionLocal
from app.service.agentes.agente_rating_score import analise_ia
from dotenv import load_dotenv
from app.schemas.licitacoes import FiltroLicitacao
from app.models.models import (
    RpaScrapEvent, RpaScrapRequest, RpaScrapResult,
    RpaRequestStepEnum, RpaRequestStatusEnum
)
import httpx


executor = ThreadPoolExecutor(max_workers=4)

load_dotenv()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}


async def handle_request(url: str) -> httpx.Response | None:
    async with httpx.AsyncClient(timeout=20) as client:
        for tentativa in range(3):
            try:
                response = await client.get(url, headers=headers)

                if response.status_code == 429:
                    await asyncio.sleep(15)
                    continue

                response.raise_for_status()
                await asyncio.sleep(random.uniform(1, 10))
                return response

            except httpx.HTTPError:
                if tentativa < 2:
                    await asyncio.sleep(random.uniform(1, 10))

    return None


def create_search_url(filtro: FiltroLicitacao, page: int):
    inital_url = os.getenv("PNCP_LINK_SEARCH", "")

    params = {
        "tipos_documento": "edital",
        "ordenacao": "-data",
        "pagina": page,
        "tam_pagina": 50,
        "status": "recebendo_proposta",
    }

    if filtro.palavras_chaves:
        params["q"] = " ".join(filtro.palavras_chaves)

    if filtro.ufs:
        params["ufs"] = "|".join(filtro.ufs)

    if filtro.modalidades_de_contratacao:
        params["modalidades"] = "|".join(
            map(str, filtro.modalidades_de_contratacao))

    return inital_url + "?" + urlencode(params)


async def get_licit_itens(licitacao):
    url = "https://pncp.gov.br/api/pncp/v1/orgaos/"\
        f"{licitacao.get("orgao_cnpj")}/compras/{licitacao.get("ano")}"\
        f"/{licitacao.get("numero_sequencial")}/itens/"

    itens_request = await handle_request(url)
    if not itens_request:
        return None
    itens_request_json = json.loads(itens_request.text)

    itens_list = []
    for item in itens_request_json:
        itens_list.append({
            "item_num": item.get("numeroItem"),
            "descricao": item.get("descricao"),
            "materialOUservico": item.get("materialOuServicoNome"),
            "valor_unitario": item.get("valorUnitarioEstimado"),
            "valor_total": item.get("valorTotal"),
            "quantidade": item.get("quantidade"),
            "unidade_medida": item.get("unidadeMedida"),
            "item_categoria": item.get("itemCategoriaNome"),
            "criterio_julgamento": item.get("criterioJulgamentoNome"),
            "data_inclusao": item.get("dataInclusao"),
            "data_atualizacao": item.get("dataAtualizacao")
        })

    return itens_list


async def get_licit_details(licitacao):
    url = "https://pncp.gov.br/api/consulta/v1/orgaos/"\
        f"{licitacao.get("orgao_cnpj")}/compras/{licitacao.get("ano")}/"\
        f"{licitacao.get("numero_sequencial")}"

    detail_request = await handle_request(url)
    if not detail_request:
        return None
    detail_request_json = json.loads(detail_request.text)

    return {
        "valor_estimado": detail_request_json.get("valorTotalEstimado",),
        "valor_homologado": detail_request_json.get("valorTotalHomologado"),
        "link_origem": detail_request_json.get("linkSistemaOrigem"),
        "uf_nome": detail_request_json.get("unidadeOrgao").get("ufNome"),
        "amparo_legal": detail_request_json.get("amparoLegal"),
        "informacao_complementar": detail_request_json.get(
            "informacaoComplementar"),
        "fonte": detail_request_json.get("usuarioNome")
    }


async def pegar_licitacoes_base(
        filtro: FiltroLicitacao,
        request: RpaScrapRequest, page: int
):
    db = SessionLocal()
    search_url = create_search_url(filtro, page)
    print(search_url)

    try:
        response = await handle_request(search_url)

        if not response:
            db.query(RpaScrapEvent).filter(
                    RpaScrapEvent.request_id == request.id
                ).update({
                    RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
                    RpaScrapEvent.status: RpaRequestStatusEnum.FAILURE,
                    RpaScrapEvent.message: "Os servidores da PNCP parecem estar sofrendo com instabilidade. Por favor, tente novamente mais tarde."  # noqa: E501
                })
            db.commit()
            return

        if response.status_code == 200:
            response_json: dict = response.json()
            if response_json.get("total", 0) == 0:
                db.query(RpaScrapEvent).filter(
                        RpaScrapEvent.request_id == request.id
                    ).update({
                        RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
                        RpaScrapEvent.status: RpaRequestStatusEnum.OCCURRENCE,
                        RpaScrapEvent.message: "Nenhuma licitação encontrada para essa busca. Tente fazer alterações nas suas requisições, e tente novamente."  # noqa: E501
                    })
                db.commit()
                return

        licitacoes_res = json.loads(response.text)
        res_licit_itens = licitacoes_res.get("items")

        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request.id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.PROCESSING,
            RpaScrapEvent.status: RpaRequestStatusEnum.PROCESSING,
            RpaScrapEvent.message: "Processando licitações"
        })

        db.commit()

        licitacoes = []
        seq = 0
        fail = 0

        for licit in res_licit_itens:

            try:
                licitacao = {
                    "id_pncp": licit.get("id", ""),
                    "nome": licit.get("title", ""),
                    "link": f"https://pncp.gov.br/app/editais/"
                    f"{licit.get("orgao_cnpj", "")}/{licit.get("ano", "")}/"
                    f"{licit.get("numero_sequencial", "")}",
                    "descricao": licit.get("description", ""),
                    "orgao_nome": licit.get("orgao_nome", ""),
                    "orgao_cnpj": licit.get("orgao_cnpj", ""),
                    "unidade_compradora": licit.get("unidade_nome", ""),
                    "modalidade_de_contratacao": licit.get(
                        "modalidade_licitacao_nome", ""),
                    "tipo": licit.get("tipo_nome", ""),
                    "data_divulgacao": licit.get("data_publicacao_pncp", ""),
                    "situacao": licit.get("situacao_nome", ""),
                    "ano": licit.get("ano", ""),
                    "numero_sequencial": licit.get("numero_sequencial", ""),
                    "uf": licit.get("uf", ""),
                    "municipio": licit.get("municipio_nome", ""),
                    "propostas_data_inicio": licit.get(
                        "data_inicio_vigencia", ""),
                    "propostas_data_fim": licit.get("data_fim_vigencia", ""),
                    "uf_nome": None,
                    "amparo_legal": None,
                    "fonte_orcamentaria": None,
                    "informacao_complementar": None,
                    "valor_estimado": None,
                    "valor_homologado": None,
                    "link_origem": None,
                }

                licitacoes.append({
                    "numero": seq,
                    "descricao": licitacao,
                    "items": []
                })
                seq = seq + 1

            except Exception:
                fail = fail + 1

        db.query(RpaScrapEvent).filter(
                RpaScrapEvent.request_id == request.id
            ).update({
                RpaScrapEvent.message: "Iniciando a avaliação da IA para as licitacoes encontradas"  # noqa: E501
            })
        db.commit()

        rpa_items: list[RpaScrapResult] = []
        for licitacao in licitacoes:
            item = RpaScrapResult(
                request_id=request.id,
                payload=licitacao
            )

            rpa_items.append(item)

        db.add_all(rpa_items)
        db.commit()

        analise_ia(db, filtro, rpa_items)

        db.query(RpaScrapEvent).filter(
                RpaScrapEvent.request_id == request.id
            ).update({
                RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
                RpaScrapEvent.status: RpaRequestStatusEnum.SUCCESS,
                RpaScrapEvent.message: f"Processo concluído com {len(licitacoes)} licitações"  # noqa: E501
            })

        db.query(RpaScrapRequest).filter(
            RpaScrapRequest.id == request.id
        ).update({
            RpaScrapRequest.total: len(licitacoes)
        })
        db.commit()

        return

    except Exception:
        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request.id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
            RpaScrapEvent.status: RpaRequestStatusEnum.FAILURE,
            RpaScrapEvent.message: "Um erro inesperado ocorreu e as licitações não foram encontradas. Tente novamente mais tarde"  # noqa: E501
        })
        db.commit()
        return

    finally:
        db.close()


async def pegar_detalhes_licitacao(licitacao_id: str | UUID):
    db = SessionLocal()

    licitacao_q = (
        db.query(RpaScrapResult)
        .filter(RpaScrapResult.id == licitacao_id)
        .first()
    )

    if not licitacao_q:
        return

    licitacao_q.status = "processing"
    db.commit()
    db.refresh(licitacao_q)

    payload = licitacao_q.payload
    new_description: dict = payload.get("descricao", {})
    payload_items: list = payload.get("items", [])

    try:
        detail = None
        if not new_description.get("uf_nome"):
            detail = await get_licit_details(new_description)
            if detail:
                new_description.update(detail)

        items = None
        if not payload_items:
            items = await get_licit_itens(new_description)
            if items:
                payload_items.extend(items)

        new_payload = {
            "numero": payload.get("numero"),
            "descricao": new_description,
            "items": items or []
        }

        licitacao_q.payload = new_payload

        if items and detail:
            db.query(RpaScrapResult).filter(
                RpaScrapResult.id == licitacao_id).update({
                    RpaScrapResult.payload: payload,
                    RpaScrapResult.is_complete: True,
                    RpaScrapResult.is_loading: False
                })

        elif not items and not detail:
            db.query(RpaScrapResult).filter(
                RpaScrapResult.id == licitacao_id).update({
                    RpaScrapResult.is_complete: False,
                    RpaScrapResult.status: "failure",
                })

        else:
            db.query(RpaScrapResult).filter(
                RpaScrapResult.id == licitacao_id).update({
                    RpaScrapResult.payload: payload,
                    RpaScrapResult.is_complete: False,
                    RpaScrapResult.status: "incomplete",
                })

        db.commit()
        return licitacao_q

    except Exception:
        db.rollback()

        # Rebusca a instância dentro da sessão atual
        licitacao_q = (
            db.query(RpaScrapResult)
            .filter(RpaScrapResult.id == licitacao_id)
            .first()
        )

        if licitacao_q:
            licitacao_q.is_complete = False
            licitacao_q.is_loading = False
            licitacao_q.status = "failure"
            db.commit()

        return

    finally:
        db.close()
