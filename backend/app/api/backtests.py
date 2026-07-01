"""Authenticated user backtests: run+save, list, get, delete (FR-05, FR-06)."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.backtesting.engine import run_backtest
from app.backtesting.schemas import BacktestRequest
from app.config import get_settings
from app.db import get_db
from app.models import SavedBacktest, User
from app.usage import monthly_count

settings = get_settings()
router = APIRouter(tags=["user-backtests"])


def _limit_for(user: User) -> int | None:
    """None == unlimited (Pro)."""
    return None if user.tier == "pro" else settings.free_monthly_limit


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    limit = _limit_for(user)
    used = monthly_count(db, user.id)
    return {
        "id": str(user.id),
        "email": user.email,
        "tier": user.tier,
        "usage_this_month": used,
        "monthly_limit": limit,
        "remaining": None if limit is None else max(0, limit - used),
    }


@router.post("/backtests", status_code=201)
def create_backtest(
    req: BacktestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Run a backtest, enforce the free-tier limit, and persist the result."""
    limit = _limit_for(user)
    if limit is not None and monthly_count(db, user.id) >= limit:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Free-tier limit reached ({limit} backtests/month). "
                f"Upgrade to Pro for unlimited backtests."
            ),
        )

    try:
        result = run_backtest(
            symbol=req.symbol,
            interval=req.interval,
            strategy=req.strategy,
            params=req.params,
            start=req.start,
            end=req.end,
            cash=req.cash,
            fee_pct=req.fee_pct,
            slippage_pct=req.slippage_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    saved = SavedBacktest(
        user_id=user.id,
        name=req.name,
        symbol=req.symbol,
        interval=req.interval,
        strategy=req.strategy,
        params=result["request"]["params"],
        start_date=datetime.fromisoformat(result["request"]["start"]),
        end_date=datetime.fromisoformat(result["request"]["end"]),
        # Persist stats + curve + assumptions (not the heavy trade list).
        results={
            "stats": result["stats"],
            "equity_curve": result["equity_curve"],
            "assumptions": result["assumptions"],
        },
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return {"id": str(saved.id), **result}


@router.get("/backtests")
def list_backtests(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict]:
    rows = db.execute(
        select(SavedBacktest)
        .where(SavedBacktest.user_id == user.id)
        .order_by(SavedBacktest.created_at.desc())
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "symbol": r.symbol,
            "interval": r.interval,
            "strategy": r.strategy,
            "params": r.params,
            "created_at": r.created_at.isoformat(),
            "stats": r.results.get("stats", {}),
        }
        for r in rows
    ]


def _owned_or_404(db: Session, user: User, backtest_id: uuid.UUID) -> SavedBacktest:
    row = db.get(SavedBacktest, backtest_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Backtest not found.")
    return row


@router.get("/backtests/{backtest_id}")
def get_backtest(
    backtest_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    r = _owned_or_404(db, user, backtest_id)
    return {
        "id": str(r.id),
        "name": r.name,
        "symbol": r.symbol,
        "interval": r.interval,
        "strategy": r.strategy,
        "params": r.params,
        "start": r.start_date.isoformat(),
        "end": r.end_date.isoformat(),
        "created_at": r.created_at.isoformat(),
        **r.results,
    }


@router.delete("/backtests/{backtest_id}", status_code=204)
def delete_backtest(
    backtest_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    r = _owned_or_404(db, user, backtest_id)
    db.delete(r)
    db.commit()
