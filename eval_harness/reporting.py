"""Pandas-backed summary report generation."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from eval_harness.models import CaseEvaluationResult
from eval_harness.tracing import get_tracer


class EvalReportWriter:
    def __init__(self, report_dir: Path) -> None:
        self._report_dir = report_dir

    def write(self, results: list[CaseEvaluationResult]) -> dict[str, Any]:
        with get_tracer().start_as_current_span("report.generate") as span:
            self._report_dir.mkdir(parents=True, exist_ok=True)
            summary = self._build_summary(results)
            json_path = self._report_dir / "eval_summary.json"
            csv_path = self._report_dir / "eval_summary.csv"
            json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
            pd.DataFrame([summary]).to_csv(csv_path, index=False)
            span.set_attribute("report.json_path", str(json_path))
            span.set_attribute("report.csv_path", str(csv_path))
            return summary

    def _build_summary(self, results: list[CaseEvaluationResult]) -> dict[str, Any]:
        total_cases = len(results)
        passed_cases = sum(result.passed for result in results)
        failed_cases = total_cases - passed_cases
        average_score = round(sum(result.total_score for result in results) / total_cases, 3) if total_cases else 0.0

        metric_names = sorted({metric.name for result in results for metric in result.rule_metrics})
        metric_pass_rates = {
            metric_name: round(
                sum(
                    metric.passed
                    for result in results
                    for metric in result.rule_metrics
                    if metric.name == metric_name
                )
                / total_cases,
                3,
            )
            for metric_name in metric_names
        }
        metric_pass_rates["mock_llm_judge"] = round(sum(result.judge.passed for result in results) / total_cases, 3)

        return {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "average_score": average_score,
            "metric_level_pass_rates": metric_pass_rates,
            "failed_case_ids": [result.case_id for result in results if not result.passed],
            "case_scores": {result.case_id: result.total_score for result in results},
        }
