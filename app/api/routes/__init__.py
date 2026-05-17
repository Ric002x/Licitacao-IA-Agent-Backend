"""
Módulo de rotas da API
"""
from fastapi import APIRouter
from app.api.routes import user, licitacoes, auth

# Router principal que agrupa todas as rotas
api_router = APIRouter()

# Incluir rotas
api_router.include_router(user.router)
api_router.include_router(licitacoes.router)
api_router.include_router(auth.router)
