# Codex Checklist — full_pipeline_determinism_hardening

**Task slug:** `full_pipeline_determinism_hardening`  
**Canvas:** `canvases/nesting_engine/full_pipeline_determinism_hardening.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_full_pipeline_determinism_hardening.yaml`

---

## DoD

- [x] A `determinism_hash` canonicalization contract doksi-kód szinten egységes.
- [x] A `json_canonicalization.md` nem állít többet, mint amit a Rust/Python implementáció ténylegesen garantál.
- [x] Van 10-run determinism smoke ugyanarra az inputra, ugyanazzal a seed-del.
- [x] A 10-run smoke a teljes output JSON byte-identitását ellenőrzi.
- [x] A smoke ellenőrzi, hogy a Python oldali canonical hash egyezik a solver `meta.determinism_hash` mezőjével.
- [x] Explicit evidence tesztek vannak `touching_policy_` prefixszel.
- [x] `touching = infeasible` dokumentálva van.
- [x] A determinism smoke a `scripts/check.sh` része, tehát PR-ban automatikusan fut.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` PASS.
- [x] Checklist + report elkészült Report Standard v2 szerint.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml determinism_` PASS.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml touching_policy_` PASS.
- [x] `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` futtatva.
