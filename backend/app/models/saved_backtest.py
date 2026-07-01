"""A backtest run saved to a user's account.

Stores the *inputs* (symbol, interval, strategy, params, date range) and the
*results* (stats + equity curve) as JSONB so the schema does not churn every
time a strategy gains a parameter. created_at lets us derive the free-tier
monthly count without a separate counter table.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SavedBacktest(Base):
    __tablename__ = "saved_backtests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Optional user-facing label.
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Inputs
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(5), nullable=False)
    strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Outputs (stats + equity curve series). Populated in Phase 2/3.
    results: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="backtests")  # noqa: F821
