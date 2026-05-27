"""Requests-based extraction client boundary for a future REAL API integration."""

from typing import Any

import requests

from eval_harness.models import ExtractionResult
from eval_harness.tracing import get_tracer


class ExtractionApiClient:
    """HTTP client shape that can replace the local mock SUT later."""

    def __init__(self, endpoint: str, timeout_seconds: float) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds

    def extract_lease_expiration(self, document_text: str) -> ExtractionResult:
        with get_tracer().start_as_current_span("api.extract_lease_expiration") as span:
            span.set_attribute("http.method", "POST")
            span.set_attribute("http.url", self._endpoint)
            response = requests.post(
                self._endpoint,
                json={"field": "lease_expiration_date", "document_text": document_text},
                timeout=self._timeout_seconds,
            )
            span.set_attribute("http.status_code", response.status_code)
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            return ExtractionResult.model_validate(payload)
