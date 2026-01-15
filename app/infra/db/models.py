from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Integer, String, ForeignKey, DateTime, Boolean, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.db.base import Base
from app.domain.enums import (
    OrderStatus,
    OrderStageStatus,
    PaymentStatus,
    ProviderKind,
    ArtifactType,
    StageType,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    orders: Mapped[List["Order"]] = relationship(back_populates="user")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(String, default=OrderStatus.PENDING)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    current_stage: Mapped[Optional[StageType]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="orders")
    stages: Mapped[List["OrderStage"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[List["Payment"]] = relationship(back_populates="order")
    artifacts: Mapped[List["Artifact"]] = relationship(back_populates="order")


class OrderStage(Base):
    __tablename__ = "order_stages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    stage_type: Mapped[StageType] = mapped_column(String, nullable=False)
    status: Mapped[OrderStageStatus] = mapped_column(String, default=OrderStageStatus.PENDING)
    price: Mapped[int] = mapped_column(BigInteger, default=0)
    input_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="stages")
    payments: Mapped[List["Payment"]] = relationship(back_populates="stage")
    artifacts: Mapped[List["Artifact"]] = relationship(back_populates="stage")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    stage_id: Mapped[UUID] = mapped_column(ForeignKey("order_stages.id"), nullable=False)
    yookassa_payment_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(String, default=PaymentStatus.PENDING)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="RUB")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="payments")
    stage: Mapped["OrderStage"] = relationship(back_populates="payments")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    stage_id: Mapped[UUID] = mapped_column(ForeignKey("order_stages.id"), nullable=True)
    type: Mapped[ArtifactType] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="artifacts")
    stage: Mapped["OrderStage"] = relationship(back_populates="artifacts")


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stage_type: Mapped[StageType] = mapped_column(String, nullable=False)
    provider_kind: Mapped[ProviderKind] = mapped_column(String, nullable=False, unique=False)
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    models_cache: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    models_cache_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, default="active")  # active, invalid, error
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Старые поля для совместимости на время миграции (опционально, но лучше обновить сразу)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    api_keys: Mapped[List["APIKey"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_configs.id"), nullable=False)
    key_value: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="active")  # active, invalid, limit_exceeded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    provider: Mapped["ProviderConfig"] = relationship(back_populates="api_keys")


class ProductConfig(Base):
    __tablename__ = "product_configs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ContentPolicy(Base):
    __tablename__ = "content_policies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    policy_type: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    rules_json: Mapped[dict] = mapped_column(JSON, default=dict)