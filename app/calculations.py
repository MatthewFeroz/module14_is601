"""Calculation persistence and arithmetic rules.

Module 14 extends the Module 13 authentication application with user-owned
calculation records.  Keeping these rules separate from the HTTP routes makes
the arithmetic easy to unit test and keeps ownership checks in the API layer.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from functools import reduce
from operator import mul

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


CALCULATION_TYPES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_inputs(calculation_type: str, inputs: list[float]) -> list[float]:
    """Return normalized finite inputs or raise a useful validation error."""
    normalized_type = calculation_type.lower()
    if normalized_type not in CALCULATION_TYPES:
        raise ValueError(f"Unsupported calculation type: {calculation_type}")
    if len(inputs) < 2:
        raise ValueError("At least two numbers are required.")

    normalized = [float(value) for value in inputs]
    if not all(math.isfinite(value) for value in normalized):
        raise ValueError("Every input must be a finite number.")
    if normalized_type == "division" and any(
        divisor == 0 for divisor in normalized[1:]
    ):
        raise ValueError("Cannot divide by zero.")
    return normalized


def calculate_result(calculation_type: str, inputs: list[float]) -> float:
    """Apply one supported operation from left to right."""
    values = validate_inputs(calculation_type, inputs)
    normalized_type = calculation_type.lower()

    if normalized_type == "addition":
        return float(sum(values))
    if normalized_type == "subtraction":
        return float(values[0] - sum(values[1:]))
    if normalized_type == "multiplication":
        return float(reduce(mul, values, 1.0))

    result = values[0]
    for divisor in values[1:]:
        result /= divisor
    return float(result)


class Calculation(Base):
    """A calculation owned by the authenticated Module 13 user identity."""

    __tablename__ = "calculations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    inputs: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    result: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    @classmethod
    def create(
        cls,
        calculation_type: str,
        user_id: str,
        inputs: list[float],
    ) -> "Calculation":
        normalized_type = calculation_type.lower()
        normalized_inputs = validate_inputs(normalized_type, inputs)
        return cls(
            user_id=str(user_id),
            type=normalized_type,
            inputs=normalized_inputs,
            result=calculate_result(normalized_type, normalized_inputs),
        )

    def replace_inputs(self, inputs: list[float]) -> None:
        normalized_inputs = validate_inputs(self.type, inputs)
        self.inputs = normalized_inputs
        self.result = calculate_result(self.type, normalized_inputs)
        self.updated_at = utc_now()
