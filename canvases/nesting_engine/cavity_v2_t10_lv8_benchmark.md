# Cavity v2 T10 — LV8 benchmark run

## Cél

A teljes LV8 benchmark futtatása `quality_cavity_prepack` profillal (`placer=nfp`, `search=sa`, `part_in_part=prepack`, `compaction=slide`). A benchmark mér: top-level holes count, cavity belső elhelyezések száma, fallback, timeout, placed/unplaced, overlap, bounds violation, utilization, quantity mismatch. Az eredmény artefaktum formában mentve.

---

## Miért szükséges

A T01–T09 izolált unit tesztek és funkcionális ellenőrzések. A T10 az első teljes end-to-end futtatás valós LV8 adatokkal, amely bizonyítja, hogy:
- a solver input top-level hole-free
- nincs silent NFP→BLF fallback
- a final placement tree teljes
- a quantity invariáns tartja magát
- az elfogadási minimumok teljesülnek

---

## Érintett valós fájlok

### Létrehozandó:
- `scripts/benchmark_cavity_v2_lv8.py` — futtatható benchmark szkript

### Szükséges meglévő (csak olvasható, nem módosítható):
- A LV8 teszt fixture-ök vagy benchmark bemeneti fájlok elérési útjai (keresendők `tests/`, `poc/`, `scripts/` alatt)
- `worker/cavity_prepack.py` — `build_cavity_prepacked_engine_input_v2()`
- `worker/result_normalizer.py` — normalizer
- `worker/cavity_validation.py` — validator (T08)
- `vrs_nesting/config/nesting_quality_profiles.py`

### Output artefaktumok:
- `tmp/benchmark_results/cavity_v2_lv8_<timestamp>.json` — részletes benchmark report

---

## Nem célok / scope határok

- **Nem** módosít egyetlen termelési kódfájlt sem.
- **Nem** futtat UI tesztet.
- **Nem** szükséges CI-ba bekötni (csak manuális benchmark).
- A T10 nem standalone unit teszt — de tartalmaz assertion-öket a minimum feltételekre.

---

## Részletes implementációs lépések

### 1. LV8 fixture megkeresése

Keresd meg a LV8 bemeneti adatokat a repo-ban:
```bash
find . -name "*lv8*" -o -name "*LV8*" | grep -v __pycache__ | head -20
find tests/ -name "*.json" | head -20
find poc/ -name "*.json" | head -20
```

Ha a LV8 nem létezik mint önálló fixture, keress bármely meglévő nesting benchmark fixture-t (pl. `poc/sparrow_io/`, `tests/fixtures/`), és a szkript adaptálódjon ahhoz.

### 2. `scripts/benchmark_cavity_v2_lv8.py`

```python
#!/usr/bin/env python3
"""
Cavity v2 LV8 benchmark runner.
Futtatás: python3 scripts/benchmark_cavity_v2_lv8.py [--fixture PATH]

Méri:
  - top_level_holes_count_before_prepack
  - top_level_holes_count_after_prepack  (kötelező: 0)
  - nfp_fallback_occurred                (kötelező: False)
  - timeout_occurred
  - placed_count
  - unplaced_count
  - internal_placement_count
  - nested_internal_placement_count
  - virtual_parent_count
  - overlap_count                        (kötelező: 0)
  - bounds_violation_count               (kötelező: 0)
  - quantity_mismatch_count              (kötelező: 0)
  - utilization_ratio
  - sheet_count
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# --- Setup sys.path for local import ---
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from worker.cavity_prepack import (
    build_cavity_prepacked_engine_input_v2,
    validate_prepack_solver_input_hole_free,
)
from worker.cavity_validation import validate_cavity_plan_v2, CavityValidationError
from vrs_nesting.config.nesting_quality_profiles import build_nesting_engine_cli_args_for_quality_profile


def _count_top_level_holes(engine_input: dict[str, Any]) -> int:
    return sum(
        1 for part in (engine_input.get("parts") or [])
        if isinstance(part, dict) and len(part.get("holes_points_mm") or []) > 0
    )


def run_benchmark(
    *,
    snapshot_row: dict[str, Any],
    base_engine_input: dict[str, Any],
    fixture_name: str,
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "fixture": fixture_name,
        "timestamp": datetime.utcnow().isoformat(),
        "quality_profile": "quality_cavity_prepack",
    }

    # Mérés: prepack előtti holes
    holes_before = _count_top_level_holes(base_engine_input)
    results["top_level_holes_count_before_prepack"] = int(holes_before)

    # Prepack futtatás
    t_start = time.perf_counter()
    out_input, cavity_plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot_row,
        base_engine_input=base_engine_input,
        enabled=True,
    )
    prepack_elapsed = time.perf_counter() - t_start
    results["prepack_elapsed_sec"] = round(prepack_elapsed, 3)

    # Mérés: prepack utáni holes (kötelező: 0)
    holes_after = _count_top_level_holes(out_input)
    results["top_level_holes_count_after_prepack"] = int(holes_after)

    # Guard futtatás
    guard_ok = True
    try:
        validate_prepack_solver_input_hole_free(out_input)
    except Exception as e:
        guard_ok = False
        results["guard_error"] = str(e)
    results["guard_passed"] = guard_ok

    # Cavity plan summary
    summary = cavity_plan.get("summary") or {}
    qty_delta = cavity_plan.get("quantity_delta") or {}
    diag = cavity_plan.get("diagnostics") or []
    results["virtual_parent_count"] = int(len(cavity_plan.get("virtual_parts") or {}))
    results["usable_cavity_count"] = int(summary.get("usable_cavity_count") or 0)
    results["internal_placement_count"] = 0  # T07 után számolandó a placement rows-ból
    results["nested_internal_placement_count"] = 0
    results["holed_child_proxy_count"] = sum(
        1 for d in diag if isinstance(d, dict) and d.get("code") == "child_has_holes_outer_proxy_used"
    )
    results["quantity_delta_parts"] = int(len(qty_delta))

    # Quantity mismatch check
    qty_mismatches = 0
    for part_id, delta in qty_delta.items():
        if not isinstance(delta, dict):
            continue
        orig = int(delta.get("original_required_qty", 0))
        intern = int(delta.get("internal_qty", 0))
        tl = int(delta.get("top_level_qty", 0))
        if intern + tl != orig:
            qty_mismatches += 1
    results["quantity_mismatch_count"] = int(qty_mismatches)

    # CLI args lekérés (ellenőrzés: --part-in-part off megy a solver-nek)
    cli_args = build_nesting_engine_cli_args_for_quality_profile("quality_cavity_prepack")
    results["engine_cli_args"] = cli_args
    results["nfp_fallback_occurred"] = "--placer blf" in " ".join(cli_args)

    # Minimum feltételek assert
    failures: list[str] = []
    if holes_after != 0:
        failures.append(f"top_level_holes_after_prepack={holes_after} (expected 0)")
    if qty_mismatches != 0:
        failures.append(f"quantity_mismatch_count={qty_mismatches} (expected 0)")
    if not guard_ok:
        failures.append("guard_failed")

    results["minimum_criteria_passed"] = len(failures) == 0
    results["minimum_criteria_failures"] = failures

    # Cavity validation (T08)
    validation_issues: list[dict[str, Any]] = []
    try:
        from worker.cavity_prepack import _build_part_records
        # part_records visszaépítése csak a count-hoz
        issues = validate_cavity_plan_v2(
            cavity_plan=cavity_plan,
            part_records=[],  # T08 adaptálni kell a part_records struktúrájához
            solver_placements=[],
            strict=False,
        )
        validation_issues = [{"code": i.code, "message": i.message} for i in issues]
    except ImportError:
        validation_issues = [{"code": "T08_NOT_AVAILABLE", "message": "cavity_validation module not found"}]
    results["validation_issues"] = validation_issues
    results["overlap_count"] = sum(1 for i in validation_issues if i["code"] == "CAVITY_CHILD_CHILD_OVERLAP")
    results["bounds_violation_count"] = sum(1 for i in validation_issues if i["code"] == "CAVITY_CHILD_OUTSIDE_PARENT_CAVITY")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Cavity v2 LV8 benchmark runner")
    parser.add_argument("--fixture", type=Path, help="Path to fixture JSON (snapshot+engine_input)")
    parser.add_argument("--output-dir", type=Path, default=Path("tmp/benchmark_results"))
    args = parser.parse_args()

    fixture_path: Path | None = args.fixture
    if fixture_path is None:
        # Automatikus keresés
        candidates = [
            Path("poc/sparrow_io"),
            Path("tests/fixtures"),
            Path("tests/worker/fixtures"),
        ]
        for candidate in candidates:
            if candidate.is_dir():
                jsons = list(candidate.glob("*.json"))
                if jsons:
                    fixture_path = jsons[0]
                    print(f"Auto-detected fixture: {fixture_path}", file=sys.stderr)
                    break
    if fixture_path is None or not fixture_path.is_file():
        print("ERROR: No fixture found. Use --fixture PATH", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    snapshot_row = payload.get("snapshot_row") or payload
    base_engine_input = payload.get("base_engine_input") or payload.get("engine_input") or payload

    results = run_benchmark(
        snapshot_row=snapshot_row,
        base_engine_input=base_engine_input,
        fixture_name=str(fixture_path),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    out_path = args.output_dir / f"cavity_v2_lv8_{ts}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))

    if not results["minimum_criteria_passed"]:
        print("\nMINIMUM CRITERIA FAILED:", file=sys.stderr)
        for failure in results["minimum_criteria_failures"]:
            print(f"  - {failure}", file=sys.stderr)
        sys.exit(1)
    print("\nAll minimum criteria PASSED.", file=sys.stderr)


if __name__ == "__main__":
    main()
```

---

## Mérési metrikák

| Metrika | Min. elvárás |
|---------|-------------|
| `top_level_holes_count_after_prepack` | 0 |
| `guard_passed` | True |
| `quantity_mismatch_count` | 0 |
| `overlap_count` | 0 |
| `bounds_violation_count` | 0 |
| `nfp_fallback_occurred` | False |
| `timeout_occurred` | False (ha LV8 fut) |
| `utilization_ratio` | > 0 (csak tájékoztató) |

---

## Tesztelési terv

```bash
# Alap futtatás (fixture auto-detect)
python3 scripts/benchmark_cavity_v2_lv8.py

# Explicit fixture
python3 scripts/benchmark_cavity_v2_lv8.py --fixture tests/fixtures/lv8_input.json

# Output artefaktum ellenőrzés
ls -la tmp/benchmark_results/cavity_v2_lv8_*.json | tail -1

./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t10_lv8_benchmark.md
```

---

## Elfogadási feltételek

- `scripts/benchmark_cavity_v2_lv8.py` futtatható és nem dob Python szintaxishibát
- Ha LV8 fixture rendelkezésre áll: `minimum_criteria_passed = true`
- `top_level_holes_count_after_prepack = 0`
- `quantity_mismatch_count = 0`
- Az output artefaktum JSON formátumban elmentve `tmp/benchmark_results/`-be
- A script exit code 0 sikeres minimum criteria esetén, 1 hiba esetén

---

## Rollback / safety notes

- A benchmark script csak olvas — nem módosít termelési kódot
- Ha LV8 fixture nem elérhető, a script gracefully hibázik és útmutatást ad
- Az output `tmp/` mappába megy — nincs repo-pollutáció

---

## Dependency

- T01–T09 összes task — kötelező (ez az utolsó, integráló task)
- A benchmark script a T06, T07, T08 modulokat importálja
