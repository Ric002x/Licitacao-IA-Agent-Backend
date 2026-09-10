
from pydantic import BaseModel


class FiltroLicitacao(BaseModel):
    palavras_chaves: list[str]
    ufs: list[str]
    modalidades_de_contratacao: list[int]
    descricao_analise_ia: str


class BuscaLicitacoes(BaseModel):
    enterprise_id: str


class RepetirBuscaLicitacoes(BaseModel):
    enterprise_id: str
    request_id: str


class AtualizarBusca(BaseModel):
    enterprise_id: str
    request_id: str


class DescricaoIA(BaseModel):
    result_id: str
