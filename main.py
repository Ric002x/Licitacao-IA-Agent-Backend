from fastapi import FastAPI
from app.api.routes import api_router
from app.inital_data import main
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

# Criar super usuário
main()

api = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redocs" if settings.ENVIRONMENT == "development" else None
)

origins = ["*"]

api.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
api.include_router(api_router, prefix=settings.API_V1_STR)
