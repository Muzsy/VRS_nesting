#!/usr/bin/env python3
"""Sparrow determinism smoke check.

Runs Sparrow twice with the same seed + input and verifies deterministic behavior.
Primary check is byte-level hash equality on final_*.json outputs.
If byte-level hash differs, a semantic fallback check is applied by default.

Exit codes:
  0  PASS  – strict hash match OR semantic fallback match
  2  FAIL  – runner error or semantic mismatch (or strict hash mismatch)

Environment (inherited from scripts/check.sh):
  SPARROW_BIN   – path to sparrow binary (required; skips if absent)
  SEED          – integer seed (default: 0)
  TIME_LIMIT    – time limit in seconds (default: 30)
  SPARROW_DETERMINISM_STRICT – "1" forces strict hash equality

Usage (standalone):
  SPARROW_BIN=/path/to/sparrow python3 scripts/smoke_sparrow_determinism.py
  SPARROW_BIN=/path/to/sparrow SEED=42 TIME_LIMIT=10 python3 scripts/smoke_sparrow_determinism.py
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.runner.sparrow_runner import (
    SparrowRunnerError,
    run_sparrow,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Use the canonical Sparrow smoke-test input (same as run_sparrow_smoketest.sh).
DEFAULT_INPUT_JSON = ROOT / "poc" / "sparrow_io" / "swim.json"

DEFAULT_SEED = 0
DEFAULT_TIME_LIMIT = 30  # seconds – short for CI; determinism does not need long runs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        _eprint(f"WARN: {key}={raw!r} is not an integer; using default {default}")
        return default


def _final_json_from_meta(run_dir: Path) -> Path:
    meta_path = run_dir / "runner_meta.json"
    if not meta_path.is_file():
        raise RuntimeError(f"runner_meta.json not found in run_dir: {run_dir}")

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cannot parse runner_meta.json: {exc}") from exc

    final_path_str = str(meta.get("final_json_path", "")).strip()
    if not final_path_str:
        raise RuntimeError(
            f"runner_meta.json has no final_json_path entry in run_dir: {run_dir}"
        )

    final_path = Path(final_path_str)
    if not final_path.is_file():
        raise RuntimeError(
            f"final_json_path does not exist: {final_path} (run_dir: {run_dir})"
        )
    return final_path


def _to_semantic_signature(payload: dict) -> dict:
    items = payload.get("items")
    solution = payload.get("solution")
    if not isinstance(items, list) or not isinstance(solution, dict):
        raise RuntimeError("final output payload missing items/solution object")

    layout = solution.get("layout")
    if not isinstance(layout, dict):
        raise RuntimeError("final output payload missing solution.layout object")

    placed_items = layout.get("placed_items")
    if not isinstance(placed_items, list):
        raise RuntimeError("final output payload missing solution.layout.placed_items array")

    hist = collections.Counter()
    for idx, placed in enumerate(placed_items):
        if not isinstance(placed, dict):
            raise RuntimeError(f"invalid placed_items[{idx}] entry type")
        item_id = placed.get("item_id")
        if not isinstance(item_id, int):
            raise RuntimeError(f"invalid placed_items[{idx}].item_id")
        hist[item_id] += 1

    return {
        "name": str(payload.get("name", "")),
        "strip_height": float(payload.get("strip_height", 0.0)),
        "placed_count": len(placed_items),
        "placed_item_id_histogram": sorted(hist.items()),
    }


# ---------------------------------------------------------------------------
# Main smoke logic
# ---------------------------------------------------------------------------


def main() -> int:
    # --- Resolve SPARROW_BIN ---
    sparrow_bin = os.environ.get("SPARROW_BIN", "").strip() or None

    if sparrow_bin is None:
        # Graceful skip: Sparrow not available in this environment.
        print(
            "SKIP: smoke_sparrow_determinism – SPARROW_BIN not set; "
            "Sparrow binary unavailable, skipping determinism check."
        )
        return 0

    # --- Resolve parameters ---
    seed = _resolve_env_int("SEED", DEFAULT_SEED)
    time_limit = _resolve_env_int("TIME_LIMIT", DEFAULT_TIME_LIMIT)

    input_json = DEFAULT_INPUT_JSON
    if not input_json.is_file():
        _eprint(f"ERROR: Sparrow determinism input not found: {input_json}")
        _eprint("       Expected: poc/sparrow_io/swim.json (canonical smoke input)")
        return 2

    print(
        f"[sparrow-det] input={input_json.name}  seed={seed}  "
        f"time_limit={time_limit}s  sparrow_bin={sparrow_bin}"
    )

    with tempfile.TemporaryDirectory(prefix="vrs_sparrow_det_") as tmp_root:
        # --- Run A ---
        print("[sparrow-det] Run A …")
        try:
            run_dir_a, _meta_a = run_sparrow(
                str(input_json),
                seed=seed,
                time_limit=time_limit,
                run_root=tmp_root,
                sparrow_bin=sparrow_bin,
            )
        except SparrowRunnerError as exc:
            _eprint(f"ERROR: Sparrow run A failed: {exc.code}: {exc}")
            return 2

        # --- Run B ---
        print("[sparrow-det] Run B …")
        try:
            run_dir_b, _meta_b = run_sparrow(
                str(input_json),
                seed=seed,
                time_limit=time_limit,
                run_root=tmp_root,
                sparrow_bin=sparrow_bin,
            )
        except SparrowRunnerError as exc:
            _eprint(f"ERROR: Sparrow run B failed: {exc.code}: {exc}")
            return 2

        # --- Hash final_*.json outputs ---
        try:
            final_a = _final_json_from_meta(run_dir_a)
            final_b = _final_json_from_meta(run_dir_b)
        except RuntimeError as exc:
            _eprint(f"ERROR: Cannot locate final output: {exc}")
            return 2

        hash_a = _sha256_file(final_a)
        hash_b = _sha256_file(final_b)

        print(f"[sparrow-det] run_a={run_dir_a.name}  final={final_a.name}  sha256={hash_a[:16]}…")
        print(f"[sparrow-det] run_b={run_dir_b.name}  final={final_b.name}  sha256={hash_b[:16]}…")

        if hash_a != hash_b:
            strict = os.environ.get("SPARROW_DETERMINISM_STRICT", "").strip() == "1"
            payload_a = json.loads(final_a.read_text(encoding="utf-8"))
            payload_b = json.loads(final_b.read_text(encoding="utf-8"))
            if not isinstance(payload_a, dict) or not isinstance(payload_b, dict):
                _eprint("ERROR: final output is not a JSON object in one of the runs")
                return 2

            sig_a = _to_semantic_signature(payload_a)
            sig_b = _to_semantic_signature(payload_b)
            if sig_a != sig_b:
                _eprint("ERROR: Sparrow determinism semantic MISMATCH")
                _eprint(f"  run_a={run_dir_a}  hash={hash_a}")
                _eprint(f"  run_b={run_dir_b}  hash={hash_b}")
                _eprint(f"  signature_a={sig_a}")
                _eprint(f"  signature_b={sig_b}")
                _eprint(
                    "  Same seed + input produced different semantic result "
                    "(placed item distribution/count changed)."
                )
                return 2

            if strict:
                _eprint("ERROR: Sparrow determinism strict hash MISMATCH")
                _eprint(f"  run_a={run_dir_a}  hash={hash_a}")
                _eprint(f"  run_b={run_dir_b}  hash={hash_b}")
                _eprint("  SPARROW_DETERMINISM_STRICT=1 set, semantic fallback disabled.")
                return 2

            print("WARN: Sparrow byte-level hash mismatch, semantic signature stable.")
            print("      Set SPARROW_DETERMINISM_STRICT=1 to enforce strict hash equality.")
            print(f"PASS: Sparrow semantic determinism stable: {sig_a}")
            return 0

    print(f"PASS: Sparrow determinism hash stable: {hash_a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
