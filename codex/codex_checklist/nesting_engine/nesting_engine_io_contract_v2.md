# Codex Checklist - nesting_engine_io_contract_v2

**Task slug:** `nesting_engine_io_contract_v2`
**Canvas:** `canvases/nesting_engine/nesting_engine_io_contract_v2.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_io_contract_v2.yaml`

---

## Felderites

- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] `docs/solver_io_contract.md` (v1) megvizsgalva
- [x] `rust/nesting_engine/src/geometry/types.rs` megvizsgalva
- [x] `docs/nesting_engine/tolerance_policy.md` megvizsgalva
- [x] `docs/nesting_engine/json_canonicalization.md` megvizsgalva

## Implementacio

- [x] `docs/nesting_engine/io_contract_v2.md` letrehozva
- [x] `poc/nesting_engine/sample_input_v2.json` letrehozva
- [x] `poc/nesting_engine/sample_output_v2.json` letrehozva
- [x] Geometria egyezmenyek dokumentalva (CCW/CW, mm, nominalis vs. inflated, transzformacio)
- [x] `unplaced.reason` kodok dokumentalva
- [x] `determinism_hash` normativ hivatkozassal dokumentalva
- [x] v1 <-> v2 osszehasonlito tablazat kesz

## Ellenorzes

- [x] `python3 -m json.tool poc/nesting_engine/sample_input_v2.json` PASS
- [x] `python3 -m json.tool poc/nesting_engine/sample_output_v2.json` PASS
- [x] `git diff docs/solver_io_contract.md` ures

## Gate

- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md` PASS
