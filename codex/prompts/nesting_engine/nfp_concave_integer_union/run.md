# VRS Nesting Codex Task — F2-2 Hardening: Concave baseline integer-only union
TASK_SLUG: nfp_concave_integer_union
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. docs/nesting_engine/tolerance_policy.md
6. docs/known_issues/nesting_engine_known_issues.md (KI-007)
7. canvases/nesting_engine/nfp_computation_concave.md
8. canvases/nesting_engine/nfp_concave_integer_union.md
9. rust/nesting_engine/src/nfp/concave.rs
10. rust/nesting_engine/src/nfp/boundary_clean.rs
11. rust/nesting_engine/tests/nfp_regression.rs
12. codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_integer_union.yaml

Ha bármelyik fájl nem létezik: STOP, és írd le pontosan mit kerestél.

---

## 2) Cél

A concave “stable baseline” union útvonalból ki kell venni a float uniont:

- TILOS: i_overlay::float::overlay::FloatOverlay, i_overlay::float::* union a concave baseline-ban
- KÖTELEZŐ: integer-only boolean union (Point64/i64 koordinátákon), i128 predikátumokkal
- A regressziós concave fixture-ek továbbra is PASS
- boundary_clean a kimenet végén kötelező

---

## 3) Nem cél

- orbitális exact algoritmus fejlesztése
- holes támogatás
- scripts/ wrapper módosítása
- rust/vrs_solver módosítása

---

## 4) Kritikus szabályok (hard)

- A FloatOverlay visszacsúszását guard teszt védi (nfp_no_float_overlay.rs).
- Csak olyan fájlt módosíthatsz/létrehozhatsz, ami a YAML step outputs listájában van.
- A quality gate kizárólag wrapperrel:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md

---

## 5) DoD

- concave.rs-ben nincs FloatOverlay / i_overlay::float import union célra
- concave fixture regressziók PASS
- verify.sh PASS + report + log friss

---

## 6) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

A végén add meg:
- módosított/létrehozott fájlok listáját
- verify parancs kimenet összegzését
- reportot a standard szerint (DoD → Evidence → Advisory)