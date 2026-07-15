"""Processed billing webhook events (idempotency ledger).

The primary key is the SHA-256 of the raw webhook payload: provider retries
resend the identical body, so a replayed event hashes to an existing row and
is skipped instead of re-applied.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 hex
    event_name: Mapped[str] = mapped_column(String(80))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
