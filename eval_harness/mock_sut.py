"""Local mock system under test for lease expiration extraction."""

import re

from eval_harness.date_utils import candidate_dates, normalize_date
from eval_harness.models import ExtractionResult
from eval_harness.tracing import get_tracer


class MockLeaseExpirationExtractor:
    """Deterministic mock that simulates useful and explainable AI extraction behavior."""

    # Extracts a lease expiration value, confidence, citation, and reasoning from document text.
    def extract(self, document_text: str) -> ExtractionResult:
        with get_tracer().start_as_current_span("mock_sut.extract_lease_expiration") as span:
            span.set_attribute("document.length", len(document_text))
            lower = document_text.lower()

            if "not a lease" in lower or "maintenance schedule" in lower:
                return ExtractionResult(
                    value=None,
                    confidence=0.1,
                    citations=[],
                    reasoning="The document is not a lease and does not establish a lease expiration date.",
                )

            if "no stated expiration date" in lower or "month-to-month" in lower:
                return ExtractionResult(
                    value=None,
                    confidence=0.2,
                    citations=[],
                    reasoning="The lease text does not state a fixed expiration date.",
                )

            selected_line = self._select_best_line(document_text)
            dates = candidate_dates(selected_line)
            value = self._select_best_date(dates)
            confidence = 0.92
            reasoning = "Selected the lease expiration date from the most authoritative clause."

            if "amendment" in lower and "overrides" in lower:
                confidence = 0.96
                reasoning = "The amendment explicitly overrides the original expiration date."
            elif "do not use this date" in lower:
                confidence = 0.9
                reasoning = "Ignored the decoy date and used the clause marked as the controlling expiration date."
            elif "conflicting" in lower or "verify before closing" in lower:
                confidence = 0.82
                reasoning = "The document contains conflicting dates; selected the final signed amendment date."
            elif "ocr" in lower or "exp1ration" in lower:
                confidence = 0.78
                reasoning = "Handled OCR noise and used the legible expiration sentence."

            return ExtractionResult(
                value=value,
                confidence=confidence if value else 0.25,
                citations=[selected_line.strip()] if value else [],
                reasoning=reasoning if value else "No reliable expiration date could be extracted.",
            )

    # Chooses the most authoritative line that contains a candidate expiration date.
    def _select_best_line(self, document_text: str) -> str:
        lines = [line.strip() for line in document_text.splitlines() if line.strip()]
        priority_terms = [
            "controlling expiration date",
            "amendment overrides",
            "final signed amendment",
            "lease expiration date",
            "expiration date",
            "expires",
            "term ends",
        ]
        ignored_terms = ["do not use this date", "not the lease expiration", "proposal"]
        scored: list[tuple[int, int, str]] = []
        for index, line in enumerate(lines):
            lowered = line.lower()
            if any(term in lowered for term in ignored_terms):
                continue
            if not candidate_dates(line):
                continue
            score = sum(10 for term in priority_terms if term in lowered)
            if "amendment" in lowered or "controlling" in lowered or "final signed" in lowered:
                score += 20
            if re.search(r"exp[il1]ration|expires|term ends", lowered):
                score += 5
            scored.append((score, index, line))
        if not scored:
            return ""
        return sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)[0][2]

    # Normalizes candidate dates and returns the latest one as the selected value.
    def _select_best_date(self, dates: list[str]) -> str | None:
        normalized = [date for date in (normalize_date(item) for item in dates) if date is not None]
        if not normalized:
            return None
        return sorted(normalized)[-1]
