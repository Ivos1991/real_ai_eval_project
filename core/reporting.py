"""Small Allure attachment helpers shared by eval tests."""

import json
from pathlib import Path
from typing import Any

import allure


def attach_json(name: str, payload: Any) -> None:
    allure.attach(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def attach_text(name: str, text: str) -> None:
    allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_file(name: str, path: Path, attachment_type: allure.attachment_type = allure.attachment_type.TEXT) -> None:
    allure.attach.file(str(path), name=name, attachment_type=attachment_type)
