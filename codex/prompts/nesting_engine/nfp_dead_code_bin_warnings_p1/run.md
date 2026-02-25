# VRS Nesting Codex Task — P1: NFP dead_code warnings fix (bin target)
TASK_SLUG: nfp_dead_code_bin_warnings_p1
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. canvases/nesting_engine/nfp_dead_code_bin_warnings_p1.md
6. rust/nesting_engine/src/nfp/mod.rs
7. rust/nesting_engine/src/nfp/concave.rs
8. rust/nesting_engine/src/nfp/convex.rs
9. rust/nesting_engine/src/nfp/boundary_clean.rs
10. rust/nesting_engine/src/nfp/cache.rs
11. scripts/check.sh
12. codex/goals/canvases/nesting_engine/fill_canvas_nfp_dead_code_bin_warnings_p1.yaml

Ha bármi hiányzik: STOP, és írd le pontosan mit kerestél.

## 2) Cél

A bin target build `dead_code` warningjai eltüntetése a NFP modulban:

- Futtasd és elemezd:
  cd rust/nesting_engine && cargo build --release --bin nesting_engine
- Javítsd cfg-gate-tel a test-only / debug-only itemeket.
- Legacy item: eltávolítás vagy célzott allow(dead_code) item-szinten, kommenttel.
- Funkció nem sérülhet, nincs új dependency.

## 3) DoD

- cargo build --release --bin nesting_engine: NFP-eredetű dead_code warning nincs
- cargo test PASS
- scripts/check.sh PASS
- verify PASS:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_dead_code_bin_warnings_p1.md

## 4) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

Szabály: csak a YAML outputs listában szereplő fájlokat módosíthatod / hozhatod létre.

A végén add meg:
- módosított fájlok listája
- a warningok Before/After rövid listája
- report + verify log frissítve
