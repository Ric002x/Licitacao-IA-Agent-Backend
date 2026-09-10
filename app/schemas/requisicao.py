from pydantic import BaseModel


class AtualizarRequisicao(BaseModel):
    enterprise_id: str
    request_id: str
    titulo: str
    palavras_chaves: list[str]
    ufs: list[str]
    modalidades_de_contratacao: list[int]
