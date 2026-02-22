# Codex Checklist — nesting_engine_baseline_placer

**Task slug:** `nesting_engine_baseline_placer`  
**Canvas:** `canvases/nesting_engine/nesting_engine_baseline_placer.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer.yaml`

---

## Felderítés

- [x] `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md` áttekintve.
- [x] `run_inflate_pipeline()` API és `PipelineRequest/PipelineResponse` szerződés ellenőrizve.
- [x] `io_contract_v2`, `json_canonicalization`, `tolerance_policy` és `architecture` dokumentáció egyeztetve.

## Implementáció — Rust

- [x] `rust/nesting_engine/src/feasibility/mod.rs` létrehozva.
- [x] `rust/nesting_engine/src/feasibility/aabb.rs` létrehozva (AABB broad-phase).
- [x] `rust/nesting_engine/src/feasibility/narrow.rs` létrehozva (`can_place`, touching=infeasible).
- [x] `rust/nesting_engine/src/placement/mod.rs` + `rust/nesting_engine/src/placement/blf.rs` létrehozva (determinisztikus BLF).
- [x] `rust/nesting_engine/src/multi_bin/mod.rs` + `rust/nesting_engine/src/multi_bin/greedy.rs` létrehozva (multi-sheet greedy).
- [x] `rust/nesting_engine/src/export/mod.rs` + `rust/nesting_engine/src/export/output_v2.rs` létrehozva (`determinism_hash`, io_contract_v2 output).
- [x] `rust/nesting_engine/src/main.rs` frissítve (`nest` subcommand, stdin/stdout JSON).
- [x] `rust/nesting_engine/Cargo.toml` + `rust/nesting_engine/Cargo.lock` frissítve (sha2, hex, rstar).

## Implementáció — Python / scripts

- [x] `vrs_nesting/runner/nesting_engine_runner.py` létrehozva.
- [x] `vrs_nesting/cli.py` frissítve (`nest-v2` subcommand).
- [x] `scripts/check.sh` frissítve baseline `nesting_engine` smoke ellenőrzésekkel.

## Smoke / benchmark / gate

- [x] `poc/nesting_engine/baseline_benchmark.md` létrehozva valós mérési eredménnyel.
- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS.
- [x] `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` PASS.
- [x] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS.
- [x] Kézi smoke: valid JSON + valódi `determinism_hash` + determinisztikus két futás + margin alapú OOB ellenőrzés PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer.md` PASS.

## Report

- [x] `codex/reports/nesting_engine/nesting_engine_baseline_placer.md` elkészítve (DoD -> Evidence, benchmark, verify blokk).
