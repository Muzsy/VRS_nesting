# VRS Nesting Codex Task — F2-2 Hardening: ExactOrbit next-event sliding
TASK_SLUG: nfp_concave_orbit_next_event
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. docs/nesting_engine/tolerance_policy.md
6. canvases/nesting_engine/nesting_engine_backlog.md (F2-2)
7. canvases/nesting_engine/nfp_computation_concave.md
8. canvases/nesting_engine/nfp_concave_integer_union.md
9. canvases/nesting_engine/nfp_concave_orbit_next_event.md
10. rust/nesting_engine/src/nfp/concave.rs
11. rust/nesting_engine/src/nfp/boundary_clean.rs
12. rust/nesting_engine/tests/nfp_regression.rs
13. poc/nfp_regression/concave_*.json
14. codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_next_event.yaml

Ha bármelyik hiányzik: STOP, és írd le pontosan mit kerestél.

---

## 2) Cél

Az ExactOrbit mód legyen valódi orbitális csúsztatás:

- Next-event léptetés (nem egységlépések): p += v * t, ahol t a következő eseményig tartó legkisebb pozitív eltolás
- Touching group kötelező multi-contact esetekre
- Determinisztikus tie-break minden döntésnél
- i128 minden cross/orient/dot döntéshez
- f64 és f64 PIP tiltás
- boundary_clean kötelező a kimenetben
- Fallback csak dead-end / loop esetén

---

## 3) Nem cél

- Stable baseline (Minkowski+dekompozíció+union) változtatása
- Holes teljes támogatás
- scripts wrapper módosítása
- rust/vrs_solver módosítása

---

## 4) DoD

- Legalább 3 concave fixture-ben az ExactOrbit mód nem fallbackel (evidence a reportban)
- Determinisztika: exact módban 2 futás bitazonos canonical ring
- verify.sh PASS:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md

---

## 5) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

Szabály: csak a YAML outputs listában szereplő fájlokat módosíthatod / hozhatod létre.

A végén add meg:
- a módosított fájlok listáját
- rövid evidenciát arról, mely 3 fixture-ben lett “no fallback” exact módban
- report + verify log frissítve