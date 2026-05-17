
from typing import Optional
from pydantic import BaseModel


class FiltroLicitacao(BaseModel):
    palavra_chave: Optional[str] = None
    request_id: Optional[str] = None
    ufs: Optional[list[str]] = []
    modalidades_de_contratacao: Optional[list[str]] = []
    descricao_analise_ia: str


class DescricaoIA(BaseModel):
    result_id: str
