"""
Modelos SQLAlchemy para RPA Scrap de Licitações
Define as estruturas de dados para requisições, resultados e eventos do
sistema de scraping
"""
import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import (Boolean, Float, String, Text, DateTime, Enum,
                        JSON, ForeignKey, Index, Integer, ARRAY)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base
from app.service.hash import hash_password, verify_password
import enum


class UserStatusEnum(str, enum.Enum):
    """Estados do status do usuário"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    """Modelo para usuários"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatusEnum] = mapped_column(
        Enum(UserStatusEnum, name="user_status"),
        nullable=False,
        default=UserStatusEnum.ACTIVE
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean(), default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now())

    # Relationships
    enterprises: Mapped[list["Enterprise"]] = relationship(
        "Enterprise", back_populates="user", cascade="all, delete-orphan"
    )

    # Índices
    __table_args__ = (
        Index("users_email_idx", "email"),
        Index("users_username_idx", "username"),
        Index("users_status_idx", "status")
    )

    def __repr__(self):
        return (f"<User(id={self.id}, username={self.username},"
                " email={self.email}, status={self.status})>")

    def set_password(self, password: str) -> None:
        self.password = hash_password(password)

    def verify_password(self, password: str) -> bool:
        return verify_password(password, self.password)

    @property
    def data(self) -> dict[str, Any]:
        exclude = {"password", "deleted_at"}
        result = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = str(getattr(self, column.name))
            result[column.name] = value

        return result


class Enterprise(Base):
    """Modelo para empresas"""
    __tablename__ = "enterprises"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="set null"),
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list] = mapped_column(ARRAY(String), nullable=False)
    ufs: Mapped[list] = mapped_column(ARRAY(String), nullable=False)
    contraction_methods: Mapped[list] = mapped_column(
        ARRAY(String), nullable=False, default=[])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="enterprises")
    requests: Mapped[list["RpaScrapRequest"]] = relationship(
        "RpaScrapRequest", back_populates="enterprise",
        cascade="all, delete-orphan"
    )

    @property
    def data(self) -> dict[str, Any]:
        exclude = []
        result = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = getattr(self, column.name)
            result[column.name] = value

        return result


class RpaRequestStepEnum(str, enum.Enum):
    """Estados do passo da requisição de RPA"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"


class RpaRequestStatusEnum(str, enum.Enum):
    """Estados do status da requisição de RPA"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"
    # Sucesso parcial com advertências ou ocorrências durante o processo
    OCCURRENCE = "occurrence"


class RpaScrapRequest(Base):
    """Modelo para requisições de scraping RPA"""
    __tablename__ = "rpa_scrap_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    enterprise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprises.id", ondelete="cascade"),
        nullable=False
    )
    current_page: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # Relationships
    enterprise: Mapped["Enterprise"] = relationship(
        "Enterprise", back_populates="requests")
    results: Mapped[list["RpaScrapResult"]] = relationship(
        "RpaScrapResult", back_populates="request",
        cascade="all, delete-orphan")
    events: Mapped[list["RpaScrapEvent"]] = relationship(
        "RpaScrapEvent", back_populates="request",
        cascade="all, delete-orphan")

    # Índices
    __table_args__ = (
        Index("rpa_scrap_requests_created_at_idx", "created_at"),
        Index("rpa_scrap_requests_enterprise_id_idx",
              "enterprise_id")
    )

    def __repr__(self):
        return f"<RpaScrapRequest(id={self.id}, title={self.title})>"

    @property
    def data(self) -> dict[str, Any]:
        exclude = ["deleted_at"]
        result = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = getattr(self, column.name)

            result[column.name] = value

        return result


class RpaScrapResult(Base):
    """Modelo para resultados de scraping"""
    __tablename__ = "rpa_scrap_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rpa_scrap_requests.id", ondelete="cascade"),
        nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    is_loading: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=True,
        default="inactive"
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False,
        nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    request: Mapped["RpaScrapRequest"] = relationship(
        "RpaScrapRequest", back_populates="results")
    rating: Mapped["RpaIARating"] = relationship(
        "RpaIARating", back_populates="result", uselist=False)

    # Índices
    __table_args__ = (
        Index("rpa_scrap_results_request_id_idx", "request_id"),
    )

    def __repr__(self):
        return f"<RpaScrapResult(id={self.id}, request_id={self.request_id})>"

    @property
    def base_data(self) -> dict[str, Any]:
        exclude = ["request_id", "is_favorite"]
        result = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = str(getattr(self, column.name))
            result[column.name] = value

        return result

    @property
    def data(self) -> dict[str, Any]:
        exclude = ["request_id", "is_loading"]
        result = {}

        for column in self.__table__.columns:
            if column.name in exclude:
                continue

            value = str(getattr(self, column.name))
            result[column.name] = value

        return result


class RpaScrapEvent(Base):
    """Modelo para eventos/logs de scraping"""
    __tablename__ = "rpa_scrap_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(
            "rpa_scrap_requests.id", ondelete="cascade"), nullable=False)
    step: Mapped[RpaRequestStepEnum] = mapped_column(
        Enum(RpaRequestStepEnum, name="rpa_request_step"),
        nullable=False,
        default=RpaRequestStepEnum.PENDING
    )
    status: Mapped[RpaRequestStatusEnum] = mapped_column(
        Enum(RpaRequestStatusEnum, name="rpa_request_status"),
        nullable=False,
        default=RpaRequestStatusEnum.PENDING
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    request: Mapped["RpaScrapRequest"] = relationship(
        "RpaScrapRequest", back_populates="events")

    # Índices
    __table_args__ = (
        Index("rpa_scrap_events_request_id_idx", "request_id"),
    )

    def __repr__(self):
        return (f"<RpaScrapEvent(id={self.id}, request_id={self.request_id},"
                " step={self.step}, status={self.status})>")


class RpaIARating(Base):
    """Modelo para resultado da avalição da IA"""
    __tablename__ = "rpa_ia_ratings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey(
            "rpa_scrap_results.id", ondelete="cascade"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rating_detail: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationships
    result: Mapped["RpaScrapResult"] = relationship(
        "RpaScrapResult", back_populates="rating")

    # Índices
    __table_args__ = (
        Index("rpa_ia_ratings_result_id_idx", "result_id"),
    )

    def __repr__(self):
        return f"<RpaIARating(id={self.id}, result_id={self.result_id})>"
