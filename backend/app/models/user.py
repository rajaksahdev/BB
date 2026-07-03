"""Application user.

Identity is owned by Supabase Auth (Phase 3); ``id`` mirrors the Supabase
``auth.users.id`` UUID. This local row holds product state Supabase does not:
subscription tier and the billing provider (Lemon Squeezy) links (Phase 5).
Empty until Phase 3.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    # Matches the Supabase auth user UUID.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)

    # 'free' | 'pro'. Drives the backtest-limit gate (Phase 3) and billing (Phase 5).
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    # Lemon Squeezy customer id (provider-neutral name so the column survives a
    # future provider change).
    billing_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Set while a Pro subscription is active; used to reconcile webhook events.
    billing_subscription_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    backtests: Mapped[list["SavedBacktest"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
