# Codex Checklist — simulated_annealing_search_cli_smoke_gate_p1

**Task slug:** `simulated_annealing_search_cli_smoke_gate_p1`  
**Canvas:** `canvases/nesting_engine/simulated_annealing_search_cli_smoke_gate_p1.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_simulated_annealing_search_cli_smoke_gate_p1.yaml`

---

## DoD

- [x] SA CLI smoke script letrehozva: `scripts/smoke_nesting_engine_sa_cli.py`.
- [x] A script ellenorzi a JSON contract minimumot (`version`, `meta.determinism_hash`).
- [x] A script legalabb 2 futas hash-et hasonlit es mismatch eseten non-zero exitet ad.
- [x] A script quality thresholdot ellenoriz (`sheets_used <= 1`).
- [x] `scripts/check.sh` meghivja a smoke scriptet a `cargo test ... sa_` utan.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_cli_smoke_gate_p1.md` futtatva.
