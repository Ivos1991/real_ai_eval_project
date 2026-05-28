"""Load fabricated eval cases from local JSON."""

import json
from pathlib import Path

from eval_harness.models import EvalCase
from eval_harness.tracing import get_tracer

MIN_ASSIGNMENT_CASES = 5
MAX_ASSIGNMENT_CASES = 10


class LeaseExpirationCaseLoader:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[EvalCase]:
        with get_tracer().start_as_current_span("cases.load") as span:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            cases = [EvalCase.model_validate(item) for item in payload]
            if not MIN_ASSIGNMENT_CASES <= len(cases) <= MAX_ASSIGNMENT_CASES:
                raise ValueError(
                    f"Option B requires {MIN_ASSIGNMENT_CASES}-{MAX_ASSIGNMENT_CASES} cases; "
                    f"loaded {len(cases)} from {self._path}."
                )
            span.set_attribute("cases.path", str(self._path))
            span.set_attribute("cases.count", len(cases))
            return cases
