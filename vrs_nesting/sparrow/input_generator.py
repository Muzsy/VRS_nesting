#!/usr/bin/env python3
"""Build Sparrow instance and solver-compatible artifacts from dxf_v1 projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vrs_nesting.dxf.importer import INNER_LAYER_DEFAULT, OUTER_LAYER_DEFAULT, import_part_raw
from vrs_nesting.geometry.offset import offset_part_geometry, offset_stock_geometry, polygon_bbox
from vrs_nesting.geometry.polygonize import polygonize_part_raw, polygonize_stock_raw
from vrs_nesting.project.model import DxfAssetSpec, DxfProjectModel


class SparrowInputGeneratorError(RuntimeError):
    """Raised when dxf_v1 -> Sparrow conversion fails."""


def _close_polygon(points: list[list[float]]) -> list[list[float]]:
    if not points:
        return []
    if points[0] == points[-1]:
        return [list(p) for p in points]
    return [list(p) for p in points] + [list(points[0])]


def _resolve_source(path_value: str, *, project_dir: Path) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = (project_dir / candidate).resolve()
    if not candidate.is_file():
        raise SparrowInputGeneratorError(f"source geometry not found: {path_value}")
    return candidate


def _load_asset_geometry(
    asset: DxfAssetSpec,
    *,
    project_dir: Path,
    spacing_mm: float,
    margin_mm: float,
    as_stock: bool,
) -> dict[str, Any]:
    source = _resolve_source(asset.path, project_dir=project_dir)
    raw = import_part_raw(source)

    if as_stock:
        poly = polygonize_stock_raw(raw.to_dict())
        prepared = offset_stock_geometry(poly, margin_mm=margin_mm, spacing_mm=spacing_mm)
    else:
        poly = polygonize_part_raw(raw.to_dict())
        prepared = offset_part_geometry(poly, spacing_mm=spacing_mm)

    min_x, min_y, max_x, max_y = polygon_bbox(prepared)
    source_base_x = min(float(point[0]) for point in raw.outer_points_mm)
    source_base_y = min(float(point[1]) for point in raw.outer_points_mm)
    return {
        "id": asset.id,
        "quantity": asset.quantity,
        "source_path": str(source),
        "source_dxf_path": str(source),
        "source_layers": {"outer": OUTER_LAYER_DEFAULT, "inner": INNER_LAYER_DEFAULT},
        "source_base_offset_mm": {"x": source_base_x, "y": source_base_y},
        "allowed_rotations_deg": list(asset.allowed_rotations_deg),
        "raw_outer_points": raw.outer_points_mm,
        "raw_holes_points": raw.holes_points_mm,
        "prepared_outer_points": prepared["outer_points_mm"],
        "prepared_holes_points": prepared.get("holes_points_mm", []),
        "source_entities": raw.source_entities,
        "width": float(max_x - min_x),
        "height": float(max_y - min_y),
    }


def build_sparrow_inputs(project: DxfProjectModel, *, project_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    stocks = [
        _load_asset_geometry(
            stock,
            project_dir=project_dir,
            spacing_mm=project.spacing_mm,
            margin_mm=project.margin_mm,
            as_stock=True,
        )
        for stock in project.stocks_dxf
    ]
    parts = [
        _load_asset_geometry(
            part,
            project_dir=project_dir,
            spacing_mm=project.spacing_mm,
            margin_mm=project.margin_mm,
            as_stock=False,
        )
        for part in project.parts_dxf
    ]

    if not stocks:
        raise SparrowInputGeneratorError("dxf_v1 project has no stocks")
    first_stock = stocks[0]
    strip_height = max(float(first_stock["height"]), float(first_stock["width"])) + 1.0

    items: list[dict[str, Any]] = []
    item_id = 0
    for part in parts:
        for seq in range(part["quantity"]):
            items.append(
                {
                    "id": item_id,
                    "demand": 1,
                    "dxf": part["source_path"],
                    "instance_id": f"{part['id']}__{seq + 1:04d}",
                    "part_id": part["id"],
                    "allowed_orientations": [float(rot) for rot in part["allowed_rotations_deg"]],
                    "shape": {
                        "type": "simple_polygon",
                        "data": _close_polygon(part["prepared_outer_points"]),
                    },
                }
            )
            item_id += 1

    sparrow_instance = {
        "name": project.name,
        "strip_height": strip_height,
        "items": items,
    }

    solver_input = {
        "contract_version": "v1",
        "project_name": project.name,
        "seed": project.seed,
        "time_limit_s": project.time_limit_s,
        "stocks": [
            {
                "id": stock["id"],
                "width": stock["width"],
                "height": stock["height"],
                "quantity": stock["quantity"],
                "outer_points": stock["raw_outer_points"],
                "holes_points": stock["raw_holes_points"],
            }
            for stock in stocks
        ],
        "parts": [
            {
                "id": part["id"],
                "width": part["width"],
                "height": part["height"],
                "quantity": part["quantity"],
                "allowed_rotations_deg": part["allowed_rotations_deg"],
                "outer_points": part["raw_outer_points"],
                "holes_points": part["raw_holes_points"],
                "source_outer_points": part["raw_outer_points"],
                "source_holes_points": part["raw_holes_points"],
                "source_entities": part["source_entities"],
                "source_path": part["source_path"],
                "source_dxf_path": part["source_dxf_path"],
                "source_layers": part["source_layers"],
                "source_base_offset_mm": part["source_base_offset_mm"],
            }
            for part in parts
        ],
    }

    meta = {
        "schema_version": project.version,
        "units": project.units,
        "spacing_mm": project.spacing_mm,
        "margin_mm": project.margin_mm,
        "stock_count": len(stocks),
        "part_count": len(parts),
        "item_instance_count": len(items),
        "stocks": [{"id": stock["id"], "path": stock["source_path"]} for stock in stocks],
        "parts": [{"id": part["id"], "path": part["source_path"]} for part in parts],
    }

    return sparrow_instance, solver_input, meta


def write_sparrow_input_artifacts(
    run_dir: str | Path,
    *,
    sparrow_instance: dict[str, Any],
    solver_input: dict[str, Any],
    meta: dict[str, Any],
) -> tuple[Path, Path, Path]:
    root = Path(run_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    instance_path = root / "sparrow_instance.json"
    solver_input_path = root / "solver_input.json"
    meta_path = root / "sparrow_input_meta.json"

    instance_path.write_text(json.dumps(sparrow_instance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    solver_input_path.write_text(json.dumps(solver_input, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return instance_path, solver_input_path, meta_path
