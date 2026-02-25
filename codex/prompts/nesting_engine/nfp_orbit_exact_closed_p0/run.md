# VRS Nesting Codex Task — P0-2: ExactOrbit quality gap (>=3 prefer_exact → ExactClosed)
TASK_SLUG: nfp_orbit_exact_closed_p0
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. canvases/nesting_engine/nesting_engine_backlog.md (F2-2 DoD)
6. canvases/nesting_engine/nfp_computation_concave.md
7. canvases/nesting_engine/nfp_concave_orbit_next_event.md
8. canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md
9. canvases/nesting_engine/nfp_orbit_exact_closed_p0.md
10. rust/nesting_engine/src/nfp/concave.rs
11. rust/nesting_engine/tests/nfp_regression.rs
12. poc/nfp_regression/*.json
13. codex/goals/canvases/nesting_engine/fill_canvas_nfp_orbit_exact_closed_p0.yaml

Ha bármi hiányzik: STOP, és írd le pontosan mit kerestél.

## 2) Cél

A prefer_exact elvárás minőségi résének bezárása:

- legalább **3** concave fixture legyen `prefer_exact: true`
- ezeknél `enable_fallback=false` mellett outcome == `ExactClosed`
- a teszt bizonyítsa: exact canonical ring != stable canonical ring (kivéve explicit allow flag)
- silent fallback tiltás nem sérül: no-fallback módban orbit fail → Err (nem stable seed)

## 3) Nem cél

- stable baseline módosítása
- holes támogatás
- új dependency
- scripts/verify.sh módosítása

## 4) DoD

- `cd rust/nesting_engine && cargo test -q nfp_regression` PASS
- ≥3 prefer_exact fixture: ExactClosed (no-fallback) PASS
- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` PASS

## 5) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

Szabály: csak a YAML outputs listában szereplő fájlokat módosíthatod / hozhatod létre.

A végén add meg:
- módosított/létrehozott fájlok listája
- mely 3 fixture lett ExactClosed bizonyítottan
- report + verify log frissítve
