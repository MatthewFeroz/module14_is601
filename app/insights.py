"""User-specific aggregate calculations for the Module 14 final feature."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calculations import CALCULATION_TYPES, Calculation


def summarize_calculations(
    calculations: Iterable[Any],
) -> dict[str, Any]:
    """Summarize only the records supplied by the ownership-aware caller."""
    records = list(calculations)
    operation_counts = {
        operation: 0 for operation in sorted(CALCULATION_TYPES)
    }
    for calculation in records:
        operation_counts[calculation.type] += 1

    results = [float(calculation.result) for calculation in records]
    return {
        "total_calculations": len(records),
        "average_result": (
            sum(results) / len(results) if results else None
        ),
        "highest_result": max(results) if results else None,
        "latest_activity": max(
            (calculation.updated_at for calculation in records),
            default=None,
        ),
        "operation_counts": operation_counts,
    }


def build_user_insights(db: Session, user_id: str) -> dict[str, Any]:
    """Load and summarize calculations belonging to one authenticated user."""
    records = db.scalars(
        select(Calculation).where(Calculation.user_id == str(user_id))
    ).all()
    return summarize_calculations(records)
