"""OpenTelemetry setup for local console tracing and Allure trace evidence."""

from collections.abc import Sequence
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)


class InMemorySpanExporter(SpanExporter):
    """Stores finished spans so tests can attach a focused trace to Allure."""

    def __init__(self) -> None:
        self._spans: list[ReadableSpan] = []
        self._lock = Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def spans_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        with self._lock:
            spans = [
                span_to_dict(span)
                for span in self._spans
                if f"{span.context.trace_id:032x}" == trace_id
            ]
        return sorted(spans, key=lambda item: item["start_time_unix_nano"])


_memory_exporter = InMemorySpanExporter()


def configure_tracing(service_name: str, console_exporter_enabled: bool) -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(SimpleSpanProcessor(_memory_exporter))
    if console_exporter_enabled:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer():
    return trace.get_tracer("real_ai_eval_harness")


def get_trace_spans(trace_id: str) -> list[dict[str, Any]]:
    return _memory_exporter.spans_for_trace(trace_id)


def span_to_dict(span: ReadableSpan) -> dict[str, Any]:
    parent_span_id = f"{span.parent.span_id:016x}" if span.parent else None
    start_time = span.start_time or 0
    end_time = span.end_time or 0
    return {
        "name": span.name,
        "trace_id": f"{span.context.trace_id:032x}",
        "span_id": f"{span.context.span_id:016x}",
        "parent_span_id": parent_span_id,
        "start_time": _iso_from_unix_nano(start_time),
        "end_time": _iso_from_unix_nano(end_time),
        "start_time_unix_nano": start_time,
        "end_time_unix_nano": end_time,
        "duration_ms": round((end_time - start_time) / 1_000_000, 3),
        "attributes": dict(span.attributes or {}),
        "status": span.status.status_code.name,
    }


def _iso_from_unix_nano(value: int) -> str:
    if value <= 0:
        return ""
    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC).isoformat().replace("+00:00", "Z")
