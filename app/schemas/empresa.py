from typing import Optional
from pydantic import BaseModel


class BaseEmpresa(BaseModel):
    nome: str
    descricao: str
    palavras_chaves: list[str]
    estados_de_atuacao: list[str]
    modalidades: Optional[list[int]] = None


class AtualizarEmpresa(BaseEmpresa):
    id: str
