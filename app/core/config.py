"""
Configurações da aplicação
"""
import os
from dotenv import load_dotenv
from pydantic import EmailStr, PostgresDsn, computed_field
from pydantic_core import MultiHostUrl

load_dotenv()


class Settings:
    """Configurações globais da aplicação"""

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Licitações RPA API"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "API para buscar e analisar licitações"

    # Segurança
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "INSECURE"
    )
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60*24*15)
    )

    # Banco de dados
    POSTGRES_HOST: str = os.getenv("DB_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("DB_PORT", 5432))
    POSTGRES_USER: str = os.getenv("DB_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("DB_NAME", "licitacoes_db")

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        url = MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB
        )
        return PostgresDsn(url)

    FIRST_SUPERUSER: EmailStr = os.environ.get(
        'FIRST_SUPERUSER', "test@example.com")
    FIRST_SUPERUSER_PASSWORD: str = os.environ.get(
        'FIRST_SUPERUSER_PASSWORD', "senha12345")
    FIRST_SUPERUSER_USERNAME: str = "ricvenicius"


settings = Settings()
