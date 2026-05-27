"""Typed runtime settings for the local eval harness."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

TraceEvidenceMode = Literal["always", "failure_only", "off"]


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _trace_evidence_mode(value: str | None) -> TraceEvidenceMode:
    raw = (value or "failure_only").strip().lower()
    aliases = {
        "always": "always",
        "all": "always",
        "failure": "failure_only",
        "failures": "failure_only",
        "failure_only": "failure_only",
        "on_failure": "failure_only",
        "off": "off",
        "none": "off",
    }
    try:
        return aliases[raw]  # type: ignore[return-value]
    except KeyError as error:
        raise ValueError("EVAL_TRACE_EVIDENCE_MODE must be one of: always, failure_only, off") from error


@dataclass(slots=True)
class EvalSettings:
    cases_path: Path
    total_score_threshold: float
    citation_similarity_threshold: float


@dataclass(slots=True)
class ReportingSettings:
    report_dir: Path

    @property
    def summary_json_path(self) -> Path:
        return self.report_dir / "eval_summary.json"

    @property
    def summary_csv_path(self) -> Path:
        return self.report_dir / "eval_summary.csv"


@dataclass(slots=True)
class TracingSettings:
    service_name: str
    console_exporter_enabled: bool
    evidence_mode: TraceEvidenceMode


@dataclass(slots=True)
class ApiSettings:
    extraction_endpoint: str
    request_timeout_seconds: float


@dataclass(slots=True)
class Settings:
    eval: EvalSettings
    reporting: ReportingSettings
    tracing: TracingSettings
    api: ApiSettings

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            eval=EvalSettings(
                cases_path=Path(os.getenv("EVAL_CASES_PATH", "cases/lease_expiration_cases.json")),
                total_score_threshold=float(os.getenv("EVAL_TOTAL_SCORE_THRESHOLD", "0.80")),
                citation_similarity_threshold=float(os.getenv("EVAL_CITATION_SIMILARITY_THRESHOLD", "80")),
            ),
            reporting=ReportingSettings(report_dir=Path(os.getenv("EVAL_REPORT_DIR", "reports"))),
            tracing=TracingSettings(
                service_name=os.getenv("OTEL_SERVICE_NAME", "real-ai-eval-harness"),
                console_exporter_enabled=_to_bool(os.getenv("OTEL_CONSOLE_EXPORTER_ENABLED"), True),
                evidence_mode=_trace_evidence_mode(os.getenv("EVAL_TRACE_EVIDENCE_MODE")),
            ),
            api=ApiSettings(
                extraction_endpoint=os.getenv("EXTRACTION_API_ENDPOINT", "http://localhost:8080/extract"),
                request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
            ),
        )
