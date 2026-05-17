from fastapi import FastAPI
from app.api.routes import api_router
from app.inital_data import main
from app.core.config import settings

# Criar super usuário
main()

api = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Incluir rotas
api.include_router(api_router, prefix=settings.API_V1_STR)
