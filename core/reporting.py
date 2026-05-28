"""Small Allure attachment helpers shared by eval tests."""

import json
from typing import Any

import allure


# Attaches structured JSON evidence to the Allure report.
def attach_json(name: str, payload: Any) -> None:
    allure.attach(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


# Attaches plain-text evidence to the Allure report.
def attach_text(name: str, text: str) -> None:
    allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)
