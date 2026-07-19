import json
import os
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from app.service.agentes.agente_rating_score import analise_ia
from dotenv import load_dotenv
from app.schemas.licitacoes import FiltroLicitacao
from sqlalchemy.orm import Session
from app.models.models import (
    RpaScrapEvent, RpaScrapResult,
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


def create_search_url(filtro: FiltroLicitacao):
    inital_url = os.getenv("PNCP_LINK_SEARCH", "")

    params = {
        "tipos_documento": "edital",
        "ordenacao": "-data",
        "pagina": 1,
        "tam_pagina": 20,
        "status": "recebendo_proposta",
    }

    if filtro.palavra_chave:
        params["q"] = filtro.palavra_chave

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


def update_status(
    db: Session, request_id: str, seq: int,
        total_licit: int, fail: int
):
    total = f"{seq + 1}/{total_licit} processadas. Falhas: {fail}"

    db.query(RpaScrapEvent).filter(
        RpaScrapEvent.request_id == request_id
    ).update({
        RpaScrapEvent.step: RpaRequestStepEnum.PROCESSING,
        RpaScrapEvent.status: RpaRequestStatusEnum.PROCESSING,
        RpaScrapEvent.message: total
    })
    db.commit()


async def get_licit_data(
        db: Session, request_id: str, licitacoes_list: list[dict]
):
    licitacoes = []
    seq = 0
    fail = 0

    for licit in licitacoes_list:
        detail = await get_licit_details(licit)
        itens = await get_licit_itens(licit)

        if not detail:
            fail = fail + 1
            update_status(db, request_id, seq, len(licitacoes_list), fail)

            seq = seq + 1
            continue

        if not itens or not len(itens) > 0:
            fail = fail + 1
            update_status(db, request_id, seq, len(licitacoes_list), fail)

            seq = seq + 1
            continue

        licitacao = {
            "nome": licit.get("title", ""),
            "link": f"https://pncp.gov.br/app/editais/"
            f"{licit.get("orgao_cnpj", "")}/{licit.get("ano", "")}/"
            f"{licit.get("numero_sequencial", "")}",
            "descricao": licit.get("description", ""),
            "orgao_nome": licit.get("orgao_nome", ""),
            "orgao_cnpj": licit.get("orgao_cnpj", ""),
            "unidade_compradora": licit.get("unidade_nome", ""),
            "amparo_legal": detail.get("amparo_legal", "").get("nome"),
            "modalidade_de_contratacao": licit.get(
                "modalidade_licitacao_nome", ""),
            "tipo": licit.get("tipo_nome", ""),
            "data_divulgacao": licit.get("data_publicacao_pncp", ""),
            "situacao": licit.get("situacao_nome", ""),
            "fonte_orcamentaria": detail.get("fonte", ""),
            "informacao_complementar": detail.get(
                "informacao_complementar", ""),
            "valor_estimado": detail.get("valor_estimado", ""),
            "valor_homologado": detail.get("valor_homologado", ""),
            "ano": licit.get("ano", ""),
            "numero_sequencial": licit.get("numero_sequencial", ""),
            "uf": licit.get("uf", ""),
            "uf_nome": detail.get("uf_nome", ""),
            "municipio": licit.get("municipio_nome", ""),
            "link_origem": detail.get("link_origem", ""),
            "propostas_data_inicio": licit.get("data_inicio_vigencia", ""),
            "propostas_data_fim": licit.get("data_fim_vigencia", "")
        }

        licitacoes.append({
            "numero": seq,
            "descricao": licitacao,
            "itens": itens
        })

        update_status(db, request_id, seq, len(licitacoes_list), fail)

        seq = seq + 1

    return licitacoes


async def iniciar_rpa(db: Session, filtro: FiltroLicitacao, request_id: str):
    search_url = create_search_url(filtro)

    try:
        response = await handle_request(search_url)

        # Se a URL falhar, salvar e levantar o erro
        if not response:
            db.query(RpaScrapEvent).filter(
                    RpaScrapEvent.request_id == request_id
                ).update({
                    RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
                    RpaScrapEvent.status: RpaRequestStatusEnum.FAILURE,
                    RpaScrapEvent.message: "Os servidores da PNCP parecem estar sofrendo com instabilidade. Por favor, tente novamente mais tarde."  # noqa: E501
                })
            db.commit()
            raise

        # Caso encontre a página de search carregue, indiciar que as licitações
        # foram encontradas
        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.PROCESSING,
            RpaScrapEvent.status: RpaRequestStatusEnum.PROCESSING,
            RpaScrapEvent.message: "Processando licitações"
        })
        db.commit()

        licitacoes_res = json.loads(response.text)
        res_licit_itens = licitacoes_res.get("items")

        licitacoes = await get_licit_data(db, request_id, res_licit_itens)

        # Atualizar status de inicio de avaliação da IA
        db.query(RpaScrapEvent).filter(
                RpaScrapEvent.request_id == request_id
            ).update({
                RpaScrapEvent.message: "Iniciando a avaliação da IA para as licitacoes encontradas"  # noqa: E501
            })
        db.commit()

        # Deletando resultados antigos, e criando os novos
        rpa_items = []
        for licitacao in licitacoes:
            item = RpaScrapResult(
                request_id=request_id,
                payload=licitacao
            )

            rpa_items.append(item)

        db.query(RpaScrapResult).filter(
            RpaScrapResult.request_id == request_id
        ).delete()

        db.add_all(rpa_items)
        db.commit()

        # avalição IA
        resultados = db.query(
            RpaScrapResult.id, RpaScrapResult.payload).filter(
            RpaScrapResult.request_id == request_id
        ).all()

        analise_ia(db, filtro, resultados)

        db.query(RpaScrapEvent).filter(
                RpaScrapEvent.request_id == request_id
            ).update({
                RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
                RpaScrapEvent.status: RpaRequestStatusEnum.SUCCESS,
                RpaScrapEvent.message: f"Processo concluído com {len(licitacoes)} licitações"  # noqa: E501
            })
        db.commit()

        return licitacoes
    except Exception:  # Atualizar status de erro
        db.query(RpaScrapEvent).filter(
            RpaScrapEvent.request_id == request_id
        ).update({
            RpaScrapEvent.step: RpaRequestStepEnum.COMPLETED,
            RpaScrapEvent.status: RpaRequestStatusEnum.FAILURE,
            RpaScrapEvent.message: "Um erro inesperado ocorreu e as licitações não foram encontradas. Tente novamente mais tarde"  # noqa: E501
        })
        db.commit()
        raise
