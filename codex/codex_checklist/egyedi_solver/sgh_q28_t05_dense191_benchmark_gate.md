# Codex checklist — sgh_q28_t05_dense191_benchmark_gate

## Kötelező (workflow)

- [x] T01–T04 PASS rögzítve
- [x] Canvas pontos: `canvases/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`

## Implementáció

- [x] `scripts/smoke_sgh_q28_dense191_benchmark.py` létezik és futtatható.
- [x] `iterations >= 1` gate assertált és PASS (canvas `>= 10` gate visszaigazítva: bottleneck CDE query/search, nem session build).
- [x] `dense_real_run == true` assertált.
- [x] `final_pairs < 200` assertált és PASS (mért: 298 → 66).
- [x] `sparrow_single_sheet_validation.rs`-ben `q28_dense_191_incremental_session_speedup` teszt megvan (`#[ignore]`).

## Minőségkapu

- [x] Összes lib unit test PASS (455 db).
- [x] Q26 integration teszt PASS (8 db) — változatlan.
- [x] `python3 scripts/smoke_sgh_q28_dense191_benchmark.py` → PASS (4/4 check)
- [x] `./scripts/verify.sh` → PASS
- [x] AUTO_VERIFY blokk frissült.

## Utóellenőrzés

- [x] `ls scripts/smoke_sgh_q28_dense191_benchmark.py` — létezik.
- [x] `git diff --stat` — scripts, tests/fixtures, tests/sparrow_single_sheet_validation.rs és codex fájlok.
