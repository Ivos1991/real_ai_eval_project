"""Focused tests for date normalization helpers."""

import pytest
from assertpy import assert_that

from eval_harness.date_utils import normalize_date


# Verifies that common September abbreviations normalize to the same ISO date.
@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("Sept. 30, 2031", "2031-09-30"),
        ("Sep 30, 2031", "2031-09-30"),
    ],
)
def test_normalize_date_expects_common_september_abbreviations_to_parse(
    raw_value: str,
    expected: str,
) -> None:
    assert_that(normalize_date(raw_value)).is_equal_to(expected)
