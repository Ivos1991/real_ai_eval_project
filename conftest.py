"""Global pytest fixtures for the REAL.dev eval harness."""

from collections.abc import Generator

import pytest

from config.settings import Settings
from eval_harness.tracing import configure_tracing


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture(scope="session", autouse=True)
def tracing(settings: Settings) -> Generator[None, None, None]:
    provider = configure_tracing(settings.tracing.service_name, settings.tracing.console_exporter_enabled)
    yield
    provider.shutdown()
