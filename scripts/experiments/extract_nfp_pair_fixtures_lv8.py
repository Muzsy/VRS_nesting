#!/usr/bin/env python3
"""Extract LV8 NFP pair fixtures from real nesting_engine input."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("tests/fixtures/nesting_engine/ne2_input_lv8jav.json")
DEFAULT_OUTPUT_DIR = Path("tests/fixtures/nesting_engine/nfp_pairs")
TARGET_IDS = ("Lv8_11612", "Lv8_07921", "Lv8_07920")


@dataclass(frozen=True)
class PartRecord:
    part_id: str
    points_mm: list[list[float]]
    holes_points_mm: list[list[list[float]]]

    @property
    def vertex_count(self) -> int:
        return len(self.points_mm)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - explicit fail path for runner
        raise SystemExit(f"FAIL: unable to parse input fixture: {path}: {exc}") from exc


def _to_points(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list):
        return []
    out: list[list[float]] = []
    for point in raw:
        if not isinstance(point, list) or len(point) != 2:
            continue
        try:
            x = float(point[0])
            y = float(point[1])
        except (TypeError, ValueError):
            continue
        out.append([x, y])
    return out


def _to_holes(raw: Any) -> list[list[list[float]]]:
    if not isinstance(raw, list):
        return []
    holes: list[list[list[float]]] = []
    for ring in raw:
        points = _to_points(ring)
        if points:
            holes.append(points)
    return holes


def _load_parts(payload: dict[str, Any]) -> list[PartRecord]:
    raw_parts = payload.get("parts")
    if not isinstance(raw_parts, list) or not raw_parts:
        raise SystemExit("FAIL: input fixture does not contain a non-empty parts list")

    parts: list[PartRecord] = []
    for item in raw_parts:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("part_id") or item.get("id") or "").strip()
        points = _to_points(item.get("points_mm") or item.get("outer_points_mm"))
        holes = _to_holes(item.get("holes_points_mm"))
        if not pid:
            continue
        parts.append(PartRecord(part_id=pid, points_mm=points, holes_points_mm=holes))

    if not parts:
        raise SystemExit("FAIL: no usable part records found in input fixture")
    return parts


def _find_named_parts(parts: list[PartRecord]) -> tuple[dict[str, PartRecord], list[str]]:
    by_id = {p.part_id: p for p in parts}
    matched: dict[str, PartRecord] = {}
    warnings: list[str] = []

    for target in TARGET_IDS:
        found = by_id.get(target)
        if found is None:
            found = next((p for p in parts if p.part_id.lower().startswith(target.lower() + "_")), None)
        if found is None:
            found = next((p for p in parts if target.lower() in p.part_id.lower()), None)
        if found is None:
            warnings.append(f"WARN: part_id not found in fixture: {target}")
            continue
        matched[target] = found
    return matched, warnings


def _top_complexity_pairs(parts: list[PartRecord]) -> list[tuple[PartRecord, PartRecord]]:
    top = sorted(parts, key=lambda p: p.vertex_count, reverse=True)[:6]
    pairs = sorted(
        combinations(top, 2),
        key=lambda pair: pair[0].vertex_count * pair[1].vertex_count,
        reverse=True,
    )
    return list(pairs[:3])


def _named_pairs(matched: dict[str, PartRecord]) -> list[tuple[PartRecord, PartRecord]]:
    if len(matched) < 3:
        return []
    return [
        (matched["Lv8_11612"], matched["Lv8_07921"]),
        (matched["Lv8_11612"], matched["Lv8_07920"]),
        (matched["Lv8_07921"], matched["Lv8_07920"]),
    ]


def _build_fixture(pair_id: str, part_a: PartRecord, part_b: PartRecord, source: str) -> dict[str, Any]:
    return {
        "fixture_version": "nfp_pair_fixture_v1",
        "pair_id": pair_id,
        "description": "LV8 problematic pair for reduced convolution NFP pipeline",
        "source": source,
        "part_a": {
            "part_id": part_a.part_id,
            "geometry_level": "solver",
            "outer_ring_vertex_count": part_a.vertex_count,
            "points_mm": part_a.points_mm,
            "holes_mm": [],
        },
        "part_b": {
            "part_id": part_b.part_id,
            "geometry_level": "solver",
            "outer_ring_vertex_count": part_b.vertex_count,
            "points_mm": part_b.points_mm,
            "holes_mm": [],
        },
        "baseline_metrics": {
            "fragment_count_a": None,
            "fragment_count_b": None,
            "expected_pair_count": None,
            "current_nfp_timeout_reproduced": False,
            "notes": "baseline metrics to be filled in T04",
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="LV8 engine input fixture")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for lv8_pair fixtures",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"FAIL: input fixture missing: {args.input}")

    payload = _read_json(args.input)
    parts = _load_parts(payload)
    matched, warnings = _find_named_parts(parts)

    for warn in warnings:
        print(warn)

    selected_pairs = _named_pairs(matched)
    pair_source = "named_ids"
    if not selected_pairs:
        print("WARN: named part IDs not found, using top-complexity fallback")
        selected_pairs = _top_complexity_pairs(parts)
        pair_source = "top_complexity_fallback"

    if len(selected_pairs) < 3:
        raise SystemExit("FAIL: unable to select at least 3 part pairs from fixture")

    fixture_paths: list[Path] = []
    index_items: list[dict[str, str]] = []
    for idx, (part_a, part_b) in enumerate(selected_pairs[:3], start=1):
        pair_id = f"lv8_pair_{idx:02d}"
        if not part_a.points_mm or not part_b.points_mm:
            raise SystemExit(f"FAIL: empty points_mm in selected pair {pair_id}")
        fixture = _build_fixture(pair_id, part_a, part_b, args.input.name)
        fixture_path = args.output_dir / f"{pair_id}.json"
        _write_json(fixture_path, fixture)
        fixture_paths.append(fixture_path)
        index_items.append(
            {
                "pair_id": pair_id,
                "file": fixture_path.name,
                "part_a": part_a.part_id,
                "part_b": part_b.part_id,
            }
        )
        print(
            f"{pair_id}: {part_a.part_id} (vc={part_a.vertex_count}) x "
            f"{part_b.part_id} (vc={part_b.vertex_count}) "
            f"product={part_a.vertex_count * part_b.vertex_count}"
        )

    index_payload = {
        "index_version": "v1",
        "selection_mode": pair_source,
        "fixtures": index_items,
        "created_from": args.input.name,
        "geometry_level": "solver",
        "hole_status": "hole_free_after_cavity_prepack_v2",
    }
    _write_json(args.output_dir / "lv8_pair_index.json", index_payload)

    print(f"OK: wrote {len(fixture_paths)} fixtures + index to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
