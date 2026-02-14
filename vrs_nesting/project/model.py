#!/usr/bin/env python3
"""Project schema model and strict validation for table-solver and DXF flows."""

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
    allowed_rotations_deg: list[int]


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
                    "allowed_rotations_deg": part.allowed_rotations_deg,
                }
                for part in self.parts
            ],
        }


@dataclass(frozen=True)
class DxfAssetSpec:
    id: str
    path: str
    quantity: int
    allowed_rotations_deg: list[int]


@dataclass(frozen=True)
class DxfProjectModel:
    version: str
    name: str
    seed: int
    time_limit_s: int
    units: str
    spacing_mm: float
    margin_mm: float
    stocks_dxf: list[DxfAssetSpec]
    parts_dxf: list[DxfAssetSpec]

    def to_dict(self) -> dict[str, Any]:
        def _asset_to_dict(asset: DxfAssetSpec) -> dict[str, Any]:
            return {
                "id": asset.id,
                "path": asset.path,
                "quantity": asset.quantity,
                "allowed_rotations_deg": list(asset.allowed_rotations_deg),
            }

        return {
            "version": self.version,
            "name": self.name,
            "seed": self.seed,
            "time_limit_s": self.time_limit_s,
            "units": self.units,
            "spacing_mm": self.spacing_mm,
            "margin_mm": self.margin_mm,
            "stocks_dxf": [_asset_to_dict(asset) for asset in self.stocks_dxf],
            "parts_dxf": [_asset_to_dict(asset) for asset in self.parts_dxf],
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


def _require_non_negative_number(value: Any, where: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be number")
    val = float(value)
    if val < 0:
        raise ProjectValidationError("E_SCHEMA_RANGE", f"{where} must be >= 0")
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


def _parse_allowed_rotations(raw: Any, where: str) -> list[int]:
    if not isinstance(raw, list) or not raw:
        raise ProjectValidationError("E_SCHEMA_TYPE", f"{where} must be non-empty array")

    allowed_set: set[int] = set()
    allowed_rotations: list[int] = []
    for ridx, value in enumerate(raw):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ProjectValidationError("E_SCHEMA_TYPE", f"{where}[{ridx}] must be integer")
        rot = value % 360
        if rot not in {0, 90, 180, 270}:
            raise ProjectValidationError("E_SCHEMA_RANGE", f"{where}[{ridx}] must be one of 0,90,180,270")
        if rot not in allowed_set:
            allowed_set.add(rot)
            allowed_rotations.append(rot)
    return allowed_rotations


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
    _validate_keys(obj, {"id", "width", "height", "quantity"}, {"allowed_rotations_deg"}, f"parts[{index}]")

    raw_rotations = obj.get("allowed_rotations_deg", [0])
    allowed_rotations_deg = _parse_allowed_rotations(raw_rotations, f"parts[{index}].allowed_rotations_deg")

    return Part(
        id=_require_non_empty_string(obj["id"], f"parts[{index}].id"),
        width=_require_positive_number(obj["width"], f"parts[{index}].width"),
        height=_require_positive_number(obj["height"], f"parts[{index}].height"),
        quantity=_require_positive_int(obj["quantity"], f"parts[{index}].quantity"),
        allowed_rotations_deg=allowed_rotations_deg,
    )


def _parse_dxf_asset(value: Any, index: int, where: str) -> DxfAssetSpec:
    obj = _require_object(value, f"{where}[{index}]")
    _validate_keys(obj, {"id", "path", "quantity"}, {"allowed_rotations_deg"}, f"{where}[{index}]")

    raw_rotations = obj.get("allowed_rotations_deg", [0])
    allowed_rotations = _parse_allowed_rotations(raw_rotations, f"{where}[{index}].allowed_rotations_deg")

    return DxfAssetSpec(
        id=_require_non_empty_string(obj["id"], f"{where}[{index}].id"),
        path=_require_non_empty_string(obj["path"], f"{where}[{index}].path"),
        quantity=_require_positive_int(obj["quantity"], f"{where}[{index}].quantity"),
        allowed_rotations_deg=allowed_rotations,
    )


def parse_project(payload: Any) -> ProjectModel:
    root = _require_object(payload, "project")
    _validate_keys(root, {"version", "name", "seed", "time_limit_s", "stocks", "parts"}, set(), "project")

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


def parse_dxf_project(payload: Any) -> DxfProjectModel:
    root = _require_object(payload, "project")
    _validate_keys(
        root,
        {"version", "name", "seed", "time_limit_s", "units", "spacing_mm", "margin_mm", "stocks_dxf", "parts_dxf"},
        set(),
        "project",
    )

    version = _require_non_empty_string(root["version"], "project.version")
    if version != "dxf_v1":
        raise ProjectValidationError("E_SCHEMA_VERSION", "project.version must be dxf_v1")

    name = _require_non_empty_string(root["name"], "project.name")
    seed = _require_non_negative_int(root["seed"], "project.seed")
    time_limit_s = _require_positive_int(root["time_limit_s"], "project.time_limit_s")
    units = _require_non_empty_string(root["units"], "project.units")
    spacing_mm = _require_non_negative_number(root["spacing_mm"], "project.spacing_mm")
    margin_mm = _require_non_negative_number(root["margin_mm"], "project.margin_mm")

    stocks_raw = root["stocks_dxf"]
    if not isinstance(stocks_raw, list):
        raise ProjectValidationError("E_SCHEMA_TYPE", "project.stocks_dxf must be array")
    if not stocks_raw:
        raise ProjectValidationError("E_SCHEMA_RANGE", "project.stocks_dxf must not be empty")
    stocks_dxf = [_parse_dxf_asset(item, index, "stocks_dxf") for index, item in enumerate(stocks_raw)]

    parts_raw = root["parts_dxf"]
    if not isinstance(parts_raw, list):
        raise ProjectValidationError("E_SCHEMA_TYPE", "project.parts_dxf must be array")
    if not parts_raw:
        raise ProjectValidationError("E_SCHEMA_RANGE", "project.parts_dxf must not be empty")
    parts_dxf = [_parse_dxf_asset(item, index, "parts_dxf") for index, item in enumerate(parts_raw)]

    return DxfProjectModel(
        version=version,
        name=name,
        seed=seed,
        time_limit_s=time_limit_s,
        units=units,
        spacing_mm=spacing_mm,
        margin_mm=margin_mm,
        stocks_dxf=stocks_dxf,
        parts_dxf=parts_dxf,
    )


def _load_json(path: str | Path) -> Any:
    project_path = Path(path)
    if not project_path.is_file():
        raise ProjectValidationError("E_PROJECT_PATH", f"project json not found: {project_path}")

    try:
        return json.loads(project_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectValidationError("E_PROJECT_JSON", f"invalid json at line {exc.lineno} column {exc.colno}") from exc


def load_project_json(path: str | Path) -> ProjectModel:
    payload = _load_json(path)
    return parse_project(payload)


def load_dxf_project_json(path: str | Path) -> DxfProjectModel:
    payload = _load_json(path)
    return parse_dxf_project(payload)
