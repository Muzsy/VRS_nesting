# VRS Nesting Codex Task — F2-2 Hardening: ExactOrbit no silent fallback + explicit proof
TASK_SLUG: nfp_concave_orbit_no_silent_fallback
AREA: nesting_engine

## 1) Kötelező olvasnivaló

1. AGENTS.md
2. docs/codex/overview.md
3. docs/codex/yaml_schema.md
4. docs/codex/report_standard.md
5. docs/nesting_engine/tolerance_policy.md
6. canvases/nesting_engine/nfp_computation_concave.md
7. canvases/nesting_engine/nfp_concave_orbit_next_event.md
8. canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md
9. rust/nesting_engine/src/nfp/concave.rs
10. rust/nesting_engine/src/nfp/mod.rs
11. rust/nesting_engine/tests/nfp_regression.rs
12. poc/nfp_regression/concave_*.json
13. codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_no_silent_fallback.yaml

Ha bármi hiányzik: STOP, és írd le pontosan mit kerestél.

---

## 2) Cél

Megszüntetni, hogy ExactOrbit “no fallback” módban csendben stable seedet adjon vissza.

Kötelező:
- enable_fallback=false mellett dead-end/loop/max_steps → Err(...)
- enable_fallback=true mellett orbit sikertelenség → explicit stable baseline fallback (outcome jelzéssel)
- teszt bizonyítsa, hogy prefer_exact esetén:
  - outcome = ExactClosed, és
  - exact canonical ring != stable canonical ring
  - vagy fixture explicit expect_exact_error=true

Nem megengedett:
- Ok(stable_seed) visszaadása enable_fallback=false mellett
- f64 PIP behúzása

---

## 3) DoD

- prefer_exact fixture-ekből legalább 3-on:
  - ExactClosed + exact != stable (vagy explicit expect_exact_error)
- verify wrapper PASS:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md

---

## 4) Végrehajtás

Hajtsd végre a YAML steps lépéseit sorrendben.

Szabály: csak a YAML outputs listában szereplő fájlokat módosíthatod / hozhatod létre.

A végén add meg:
- módosított/létrehozott fájlok listáját
- rövid evidencia: mely 3 fixture és mi lett az outcome (ExactClosed vagy expect_exact_error)
- report + verify log frissítve