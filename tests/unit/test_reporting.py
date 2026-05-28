"""Focused tests for eval summary report writing."""

import shutil
from pathlib import Path

import pytest
from assertpy import assert_that

from eval_harness.reporting import EvalReportWriter


# Verifies that report generation remains stable when no eval cases ran.
@pytest.mark.unit
def test_report_writer_expects_empty_result_set_to_still_write_summary() -> None:
    report_dir = Path("reports/test-report-writer")
    if report_dir.exists():
        shutil.rmtree(report_dir)

    summary = EvalReportWriter(report_dir).write([])

    try:
        assert_that(summary["total_cases"]).is_equal_to(0)
        assert_that(summary["metric_level_pass_rates"]["mock_llm_judge"]).is_equal_to(0.0)
        assert_that(report_dir.joinpath("eval_summary.json").exists()).is_true()
        assert_that(report_dir.joinpath("eval_summary.csv").exists()).is_true()
    finally:
        shutil.rmtree(report_dir, ignore_errors=True)
