#!/usr/bin/env python3
"""Project schema model and strict validation for MVP CLI flow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProjectValidationError(ValueError):
    """Deterministic validation error with stable code + message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Stock:
    id: str
    width: float
    height: float
    quantity: int


@dataclass(frozen=True)
class Part:
    id: str
    width: float
    height: float
    quantity: int
    allow_rotation: bool


@dataclass(frozen=True)
class ProjectModel:
    version: str
    name: str
    seed: int
    time_limit_s: int
    stocks: list[Stock]
    parts: list[Part]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "seed": self.seed,
            "time_limit_s": self.time_limit_s,
            "stocks": [
                {
                    "id": stock.id,
                    "width": stock.width,
                    "height": stock.height,
                    "quantity": stock.quantity,
                }
                for stock in self.stocks
            ],
            "parts": [
                {
                    "id": part.id,
                    "width": part.width,
                    "height": part.height,
                    "quantity": part.quantity,
                    "allow_rotation": part.allow_rotation,
                }
                for part in self.parts
            ],
        }


def _require_object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be object")
    return value


def _require_non_empty_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be non-empty string")
    return value.strip()


def _require_positive_number(value: Any, where: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be number")
    val = float(value)
    if val <= 0:
        raise ProjectValidationError("E_SCHEMA_RANGE", f"{where} must be > 0")
    return val


def _require_positive_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be integer")
    if value <= 0:
        raise ProjectValidationError("E_SCHEMA_RANGE", f"{where} must be > 0")
    return value


def _require_non_negative_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be integer")
    if value < 0:
        raise ProjectValidationError("E_SCHEMA_RANGE", f"{where} must be >= 0")
    return value


def _validate_keys(obj: dict[str, Any], required: set[str], optional: set[str], where: str) -> None:
    allowed = required | optional
    missing = sorted(required - set(obj))
    extra = sorted(set(obj) - allowed)
    if missing:
        raise ProjectValidationError("E_SCHEMA_MISSING", f"{where} missing required keys: {', '.join(missing)}")
    if extra:
        raise ProjectValidationError("E_SCHEMA_UNKNOWN", f"{where} unknown keys: {', '.join(extra)}")


def _parse_stock(value: Any, index: int) -> Stock:
    obj = _require_object(value, f"stocks[{index}]")
    _validate_keys(obj, {"id", "width", "height", "quantity"}, set(), f"stocks[{index}]")
    return Stock(
        id=_require_non_empty_string(obj["id"], f"stocks[{index}].id"),
        width=_require_positive_number(obj["width"], f"stocks[{index}].width"),
        height=_require_positive_number(obj["height"], f"stocks[{index}].height"),
        quantity=_require_positive_int(obj["quantity"], f"stocks[{index}].quantity"),
    )


def _parse_part(value: Any, index: int) -> Part:
    obj = _require_object(value, f"parts[{index}]")
    _validate_keys(obj, {"id", "width", "height", "quantity"}, {"allow_rotation"}, f"parts[{index}]")

    allow_rotation = obj.get("allow_rotation", False)
    if not isinstance(allow_rotation, bool):
        raise ProjectValidationError("E_SCHEMA_TYPE", f"parts[{index}].allow_rotation must be boolean")

    return Part(
        id=_require_non_empty_string(obj["id"], f"parts[{index}].id"),
        width=_require_positive_number(obj["width"], f"parts[{index}].width"),
        height=_require_positive_number(obj["height"], f"parts[{index}].height"),
        quantity=_require_positive_int(obj["quantity"], f"parts[{index}].quantity"),
        allow_rotation=allow_rotation,
    )


def parse_project(payload: Any) -> ProjectModel:
    root = _require_object(payload, "project")
    _validate_keys(
        root,
        {"version", "name", "seed", "time_limit_s", "stocks", "parts"},
        set(),
        "project",
    )

    version = _require_non_empty_string(root["version"], "project.version")
    if version != "v1":
        raise ProjectValidationError("E_SCHEMA_VERSION", "project.version must be v1")

    name = _require_non_empty_string(root["name"], "project.name")
    seed = _require_non_negative_int(root["seed"], "project.seed")
    time_limit_s = _require_positive_int(root["time_limit_s"], "project.time_limit_s")

    stocks_raw = root["stocks"]
    if not isinstance(stocks_raw, list):
        raise ProjectValidationError("E_SCHEMA_TYPE", "project.stocks must be array")
    if not stocks_raw:
        raise ProjectValidationError("E_SCHEMA_RANGE", "project.stocks must not be empty")
    stocks = [_parse_stock(item, index) for index, item in enumerate(stocks_raw)]

    parts_raw = root["parts"]
    if not isinstance(parts_raw, list):
        raise ProjectValidationError("E_SCHEMA_TYPE", "project.parts must be array")
    if not parts_raw:
        raise ProjectValidationError("E_SCHEMA_RANGE", "project.parts must not be empty")
    parts = [_parse_part(item, index) for index, item in enumerate(parts_raw)]

    return ProjectModel(
        version=version,
        name=name,
        seed=seed,
        time_limit_s=time_limit_s,
        stocks=stocks,
        parts=parts,
    )


def load_project_json(path: str | Path) -> ProjectModel:
    project_path = Path(path)
    if not project_path.is_file():
        raise ProjectValidationError("E_PROJECT_PATH", f"project json not found: {project_path}")

    try:
        payload = json.loads(project_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectValidationError(
            "E_PROJECT_JSON",
            f"invalid json at line {exc.lineno} column {exc.colno}",
        ) from exc

    return parse_project(payload)
