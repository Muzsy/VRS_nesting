Olvasd el:
- AGENTS.md
- canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
- codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

Kemény szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- Ez nem LV8 benchmark task. Ne optimalizálj benchmarkra, és ne adj hozzá LV8 minőségi acceptance gate-et.
- Ez nem compression task. Compression marad deferred.
- A Q25-R3 report PASS állításai nem bizonyítékok, ha a source mást mutat. A Q25-R4 reportban a source-truth alapján korrigálj.
- `SampleEvaluator::evaluate_sample(x,y,rot)` helyi konvenciója rect-min koordináta legyen; `SparrowPlacement` továbbra is anchor output.
- LBF collision candidate nem lehet `Some(ScoredPlacement { is_clear: false, ... })`. LBF collision = Invalid/rejected.
- Ne vezesd vissza a `WorkingLayout`, `VrsCollisionTracker`, bbox/AABB ranking, legacy VRS-core vagy dense-specific shortcut logikát.

Kötelező végső gate:
- cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
- cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
- python3 scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py
- ./scripts/check.sh
- ./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md

Eredményként frissítsd:
- codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
- codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
- codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.verify.log

A végén add meg a módosított fájlok listáját és a gate-ek eredményét.
