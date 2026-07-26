"""Unit coverage for the user-specific calculation insights feature."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.insights import summarize_calculations


def calculation(calculation_type, result, updated_at):
    return SimpleNamespace(
        type=calculation_type,
        result=result,
        updated_at=updated_at,
    )


def test_empty_insights_have_predictable_defaults():
    assert summarize_calculations([]) == {
        "total_calculations": 0,
        "average_result": None,
        "highest_result": None,
        "latest_activity": None,
        "operation_counts": {
            "addition": 0,
            "division": 0,
            "multiplication": 0,
            "subtraction": 0,
        },
    }


def test_insights_compute_counts_and_result_statistics():
    started_at = datetime(2026, 7, 26, 12, tzinfo=timezone.utc)
    records = [
        calculation("addition", 6, started_at),
        calculation("multiplication", 24, started_at + timedelta(minutes=5)),
        calculation("addition", -3, started_at + timedelta(minutes=2)),
    ]

    summary = summarize_calculations(records)

    assert summary["total_calculations"] == 3
    assert summary["average_result"] == 9
    assert summary["highest_result"] == 24
    assert summary["latest_activity"] == started_at + timedelta(minutes=5)
    assert summary["operation_counts"] == {
        "addition": 2,
        "division": 0,
        "multiplication": 1,
        "subtraction": 0,
    }
