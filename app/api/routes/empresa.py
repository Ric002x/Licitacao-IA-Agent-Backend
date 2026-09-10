from datetime import datetime

from app.api.deps.session import SessionDep
from app.api.deps.auth import CurrentUser
from app.models.models import Enterprise
from fastapi import APIRouter, HTTPException
from app.schemas.empresa import AtualizarEmpresa, BaseEmpresa


router = APIRouter(prefix="/empresa", tags=["empresas"])


@router.post("/nova-empresa", status_code=201)
async def criar_empresa(
        db: SessionDep, current_user: CurrentUser, data: BaseEmpresa):
    empresa = db.query(Enterprise).filter(
        Enterprise.user_id == current_user.id
    ).first()
    if empresa:
        raise HTTPException(
            400, "usuário já possui uma empresa"
        )

    nova_empresa = Enterprise(
        user_id=current_user.id,
        name=data.nome,
        description=data.descricao,
        keywords=data.palavras_chaves,
        ufs=data.estados_de_atuacao,
        contraction_methods=data.modalidades or []
    )

    try:
        db.add(nova_empresa)
        db.commit()
    except Exception:
        return HTTPException(
            500, "Erro ao adicionar empresa"
        )

    return nova_empresa.data


@router.put("/atualizar-empresa")
async def atualizar_empresa(
    db: SessionDep, current_user: CurrentUser, data: AtualizarEmpresa
):
    empresa = db.query(Enterprise).filter(
        Enterprise.user_id == current_user.id,
        Enterprise.id == data.id,
        Enterprise.user_id == current_user.id
    ).first()
    if not empresa:
        raise HTTPException(
            404, "Empresa não encontrada"
        )

    empresa.name = data.nome
    empresa.description = data.descricao
    empresa.keywords = data.palavras_chaves
    empresa.ufs = data.estados_de_atuacao
    empresa.contraction_methods = data.modalidades or []

    db.commit()
    db.refresh(empresa)

    return empresa.data


@router.get("/listar")
async def buscar_empresas(db: SessionDep, current_user: CurrentUser):
    empresas = db.query(Enterprise).filter(
        Enterprise.user_id == current_user.id,
        Enterprise.deleted_at.is_(None)
    ).order_by(Enterprise.created_at.desc()).all()

    if not empresas or len(empresas) <= 0:
        raise HTTPException(
            404, "nenhuma empresa encontrada"
        )

    return {"enterprises": [
        empresa.data for empresa in empresas
    ]}


@router.delete("/{enterprise_id}/deletar")
async def deletar_empresa(
        db: SessionDep, current_user: CurrentUser, enterprise_id: str):
    empresas = db.query(Enterprise).filter(
        Enterprise.user_id == current_user.id
    ).all()

    if empresas and len(empresas) == 1:
        raise HTTPException(
            404, "o usuário deve manter ao menos 1 empresa"
        )

    empresa = db.query(Enterprise).filter(
        Enterprise.id == enterprise_id,
        Enterprise.user_id == current_user.id
    ).first()

    if not empresa:
        raise HTTPException(
            404, "empresa não encontrada"
        )

    empresa.deleted_at = datetime.now()
    db.commit()
    db.refresh(empresa)

    return {
        "message": "empresa deletada com sucesso"
    }
