"""Unit coverage for Module 14 calculation business rules."""

from uuid import uuid4

import pytest

from app.calculations import Calculation, calculate_result


@pytest.mark.parametrize(
    ("calculation_type", "inputs", "expected"),
    [
        ("addition", [1, 2, 3], 6),
        ("subtraction", [10, 3, 2], 5),
        ("multiplication", [2, 3, 4], 24),
        ("division", [100, 2, 5], 10),
    ],
)
def test_calculate_result_supports_every_operation(
    calculation_type,
    inputs,
    expected,
):
    assert calculate_result(calculation_type, inputs) == expected


def test_calculation_factory_computes_and_stores_result():
    calculation = Calculation.create(
        "multiplication",
        str(uuid4()),
        [5, 6],
    )

    assert calculation.type == "multiplication"
    assert calculation.inputs == [5.0, 6.0]
    assert calculation.result == 30


@pytest.mark.parametrize(
    ("calculation_type", "inputs", "message"),
    [
        ("unsupported", [1, 2], "Unsupported calculation type"),
        ("addition", [1], "At least two numbers"),
        ("division", [10, 0], "Cannot divide by zero"),
        ("addition", [1, float("inf")], "finite number"),
    ],
)
def test_calculation_rules_reject_invalid_requests(
    calculation_type,
    inputs,
    message,
):
    with pytest.raises(ValueError, match=message):
        calculate_result(calculation_type, inputs)
