"""Eval-suite fixtures and report finalization."""

from collections.abc import Generator

import pytest

from config.settings import Settings
from core.reporting import attach_json
from eval_harness.case_loader import LeaseExpirationCaseLoader
from eval_harness.mock_sut import MockLeaseExpirationExtractor
from eval_harness.models import CaseEvaluationResult, EvalCase
from eval_harness.reporting import EvalReportWriter
from eval_harness.runner import LeaseExpirationEvalRunner


# Loads eval cases through the production case loader.
def _load_cases(settings: Settings) -> list[EvalCase]:
    return LeaseExpirationCaseLoader(settings.eval.cases_path).load()


# Builds readable pytest IDs from case titles and expected outcomes.
def _case_test_id(case: EvalCase) -> str:
    readable_title = case.title.lower().replace("/", " ").replace(":", "").replace("-", " ").replace(" ", "_")
    readable_title = "_".join(part for part in readable_title.split("_") if part)
    return f"{readable_title}_expects_{case.expected_outcome_slug}"


# Parametrizes eval tests with the fabricated case dataset.
def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "case" in metafunc.fixturenames:
        settings = Settings.from_env()
        cases = _load_cases(settings)
        metafunc.parametrize("case", cases, ids=[_case_test_id(case) for case in cases])


# Provides the case loader for eval-suite tests.
@pytest.fixture(scope="session")
def case_loader(settings: Settings) -> LeaseExpirationCaseLoader:
    return LeaseExpirationCaseLoader(settings.eval.cases_path)


# Provides the deterministic mock system under test.
@pytest.fixture(scope="session")
def mock_extractor() -> MockLeaseExpirationExtractor:
    return MockLeaseExpirationExtractor()


# Provides the orchestration layer used by domain-facing eval tests.
@pytest.fixture(scope="session")
def lease_expiration_eval_runner(
    mock_extractor: MockLeaseExpirationExtractor,
    settings: Settings,
) -> LeaseExpirationEvalRunner:
    return LeaseExpirationEvalRunner(mock_extractor, settings)


# Collects eval results so the session teardown can write one summary report.
@pytest.fixture(scope="session")
def evaluation_results() -> list[CaseEvaluationResult]:
    return []


# Provides the summary report writer for the eval suite.
@pytest.fixture(scope="session")
def report_writer(settings: Settings) -> EvalReportWriter:
    return EvalReportWriter(settings.reporting.report_dir)


# Writes the eval summary report after all parametrized cases complete.
@pytest.fixture(scope="session", autouse=True)
def write_eval_report_after_session(
    evaluation_results: list[CaseEvaluationResult],
    settings: Settings,
    report_writer: EvalReportWriter,
) -> Generator[None, None, None]:
    yield
    expected_count = len(_load_cases(settings))
    if len(evaluation_results) == expected_count:
        summary = report_writer.write(evaluation_results)
        attach_json("eval_summary", summary)
