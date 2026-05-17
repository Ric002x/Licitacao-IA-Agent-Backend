"""
Rotas gerais da API
"""
from fastapi import APIRouter

router = APIRouter(tags=["root"])


@router.get("/")
async def home():
    """Endpoint raiz da API"""
    return {"message": "Bem-vindo à API de Licitações", "version": "1.0.0"}


@router.get("/health")
async def health_check():
    """Health check da API"""
    return {"status": "healthy"}
