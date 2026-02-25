#!/usr/bin/env python3
"""Generate targeted concave NFP regression fixtures in quarantine namespace.

This script is stdlib-only by design.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "poc" / "nfp_regression"


def die(message: str) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_fixture(name: str) -> dict[str, Any]:
    path = FIXTURE_DIR / name
    if not path.is_file():
        die(f"missing base fixture: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def affine(points: list[list[int]], a: int, b: int, c: int, d: int) -> list[list[int]]:
    out: list[list[int]] = []
    for x, y in points:
        out.append([a * x + b * y, c * x + d * y])
    return out


def shift(points: list[list[int]], dx: int, dy: int) -> list[list[int]]:
    return [[x + dx, y + dy] for x, y in points]


def densify_collinear(points: list[list[int]]) -> list[list[int]]:
    if len(points) < 2:
        return points
    out: list[list[int]] = []
    for idx, (x0, y0) in enumerate(points):
        x1, y1 = points[(idx + 1) % len(points)]
        out.append([x0, y0])
        dx = x1 - x0
        dy = y1 - y0
        g = math.gcd(abs(dx), abs(dy))
        if g > 1:
            # Insert a lattice interior point while preserving exact collinearity.
            out.append([x0 + dx // g, y0 + dy // g])
    return out


def build_case(case_name: str, base: dict[str, Any], seed: int) -> dict[str, Any]:
    poly_a = [list(p) for p in base["polygon_a"]]
    poly_b = [list(p) for p in base["polygon_b"]]
    expected = [list(p) for p in base["expected_nfp"]]

    if case_name == "near_parallel":
        # Axis-anisotropic scaling keeps existing contact topology while stressing long-parallel edges.
        mat = (100, 0, 0, 99)
        poly_a = affine(poly_a, *mat)
        poly_b = affine(poly_b, *mat)
        expected = affine(expected, *mat)
        desc = "Generated boss-fight: near-parallel long-edge anisotropic scale"
    elif case_name == "near_tangent":
        # NFP(A, B + t) = NFP(A, B) - t ; 1-step offset gives near-tangent sensitivity.
        tangent_shift = 1 + (seed % 2)
        poly_b = shift(poly_b, tangent_shift, 0)
        expected = shift(expected, -tangent_shift, 0)
        desc = "Generated boss-fight: almost-tangent contact via deterministic B shift"
    elif case_name == "sliver_gap":
        # Keep exact lattice, amplify y to produce a high-aspect sliver channel behavior.
        mat = (1, 0, 0, 31)
        poly_a = affine(poly_a, *mat)
        poly_b = affine(poly_b, *mat)
        expected = affine(expected, *mat)
        desc = "Generated boss-fight: sliver-style concave gap (high aspect transform)"
    elif case_name == "collinear_dense":
        poly_a = densify_collinear(poly_a)
        poly_b = densify_collinear(poly_b)
        desc = "Generated boss-fight: dense collinear vertices on both polygons"
    else:  # pragma: no cover - defensive
        die(f"unknown case: {case_name}")

    return {
        "description": desc,
        "fixture_type": "concave",
        "polygon_a": poly_a,
        "polygon_b": poly_b,
        "rotation_deg_b": 0,
        "expected_nfp": expected,
        "expected_vertex_count": len(expected),
        "prefer_exact": False,
        "generated_quarantine": True,
        "generated_case": case_name,
        "generated_seed": seed,
    }


def write_fixture(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_regression_suite() -> int:
    workdir = ROOT / "rust" / "nesting_engine"

    cmd_filter = ["cargo", "test", "-q", "nfp_regression"]
    result_filter = subprocess.run(cmd_filter, cwd=workdir)
    if result_filter.returncode != 0:
        return result_filter.returncode

    cmd_fixture_suite = ["cargo", "test", "-q", "--test", "nfp_regression"]
    result_fixture_suite = subprocess.run(cmd_fixture_suite, cwd=workdir)
    return result_fixture_suite.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260225, help="Deterministic RNG seed")
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="How many quarantine fixtures to materialize (minimum 3 recommended)",
    )
    parser.add_argument(
        "--date",
        default=dt.date.today().strftime("%Y%m%d"),
        help="Date component for quarantine filenames (YYYYMMDD)",
    )
    args = parser.parse_args()

    if args.count < 1:
        die("--count must be >= 1")

    rng = random.Random(args.seed)
    available_cases = [
        ("near_parallel", "concave_touching_group.json"),
        ("near_tangent", "concave_hole_pocket.json"),
        ("sliver_gap", "concave_slit.json"),
        ("collinear_dense", "concave_slit.json"),
    ]
    rng.shuffle(available_cases)
    selected = available_cases[: min(args.count, len(available_cases))]

    written: list[Path] = []
    for case_name, base_name in selected:
        base = read_fixture(base_name)
        payload = build_case(case_name, base, args.seed)
        out_name = (
            f"quarantine_generated_{args.date}_{args.seed}_{case_name}.json"
        )
        out_path = FIXTURE_DIR / out_name
        write_fixture(out_path, payload)
        written.append(out_path)
        print(f"[WRITE] {out_path.relative_to(ROOT)}")

    print("[TEST] cargo test -q nfp_regression")
    exit_code = run_regression_suite()
    if exit_code != 0:
        print("FAIL: nfp_regression failed after generating quarantine fixtures.", file=sys.stderr)
        print(
            "Generated files were kept under poc/nfp_regression/quarantine_generated_*.json",
            file=sys.stderr,
        )
        return exit_code

    print("PASS: nfp_regression passed with generated quarantine fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
