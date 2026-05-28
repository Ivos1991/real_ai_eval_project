"""Shared pytest fixtures for the REAL.dev eval harness."""

from collections.abc import Generator

import pytest

from config.settings import Settings
from core.reporting import attach_json
from eval_harness.case_loader import LeaseExpirationCaseLoader
from eval_harness.mock_sut import MockLeaseExpirationExtractor
from eval_harness.models import CaseEvaluationResult, EvalCase
from eval_harness.reporting import EvalReportWriter
from eval_harness.runner import LeaseExpirationEvalRunner
from eval_harness.tracing import configure_tracing


def _load_cases_for_parametrization() -> list[EvalCase]:
    settings = Settings.from_env()
    return LeaseExpirationCaseLoader(settings.eval.cases_path).load()


def _case_test_id(case: EvalCase) -> str:
    readable_title = (
        case.title.lower()
        .replace("/", " ")
        .replace(":", "")
        .replace("-", " ")
        .replace(" ", "_")
    )
    readable_title = "_".join(part for part in readable_title.split("_") if part)
    return f"{readable_title}_expects_{_case_expected_outcome(case)}"


def _case_expected_outcome(case: EvalCase) -> str:
    return case.expected_outcome_slug


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "case" in metafunc.fixturenames:
        cases = _load_cases_for_parametrization()
        metafunc.parametrize("case", cases, ids=[_case_test_id(case) for case in cases])


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture(scope="session", autouse=True)
def tracing(settings: Settings) -> Generator[None, None, None]:
    provider = configure_tracing(settings.tracing.service_name, settings.tracing.console_exporter_enabled)
    yield
    provider.shutdown()


@pytest.fixture(scope="session")
def case_loader(settings: Settings) -> LeaseExpirationCaseLoader:
    return LeaseExpirationCaseLoader(settings.eval.cases_path)


@pytest.fixture(scope="session")
def mock_extractor() -> MockLeaseExpirationExtractor:
    return MockLeaseExpirationExtractor()


@pytest.fixture(scope="session")
def lease_expiration_eval_runner(
    mock_extractor: MockLeaseExpirationExtractor,
    settings: Settings,
) -> LeaseExpirationEvalRunner:
    return LeaseExpirationEvalRunner(mock_extractor, settings)


@pytest.fixture(scope="session")
def evaluation_results() -> list[CaseEvaluationResult]:
    return []


@pytest.fixture(scope="session")
def report_writer(settings: Settings) -> EvalReportWriter:
    return EvalReportWriter(settings.reporting.report_dir)


@pytest.fixture(scope="session", autouse=True)
def write_eval_report_after_session(
    evaluation_results: list[CaseEvaluationResult],
    report_writer: EvalReportWriter,
) -> Generator[None, None, None]:
    yield
    expected_count = len(_load_cases_for_parametrization())
    if len(evaluation_results) == expected_count:
        summary = report_writer.write(evaluation_results)
        attach_json("eval_summary", summary)
