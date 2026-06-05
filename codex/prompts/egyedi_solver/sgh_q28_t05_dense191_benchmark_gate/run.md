# SGH-Q28-T05 — Dense 191 benchmark gate + Q28 validation suite
TASK_SLUG: sgh_q28_t05_dense191_benchmark_gate

## Szerep

Rust + Python implementációs agent vagy. A feladatod egy Python smoke script és egy
Rust integration teszt létrehozása, amelyek mérési bizonyítékot adnak a T01–T04-ben
megvalósított inkrementális session gyorsításról. Előfeltétel: T01–T04 PASS.

## Cél

Hozd létre / módosítsd:

1. `scripts/smoke_sgh_q28_dense191_benchmark.py` (új)
2. `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs` (bővítés)
3. `codex/codex_checklist/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`
4. `codex/reports/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`

## Kötelező olvasnivaló

1. `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
2. `canvases/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`
3. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t05_dense191_benchmark_gate.yaml`
4. `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py` (minta a Python smoke-hoz)
5. T01–T04 report (PASS ellenőrzés)

## Előfeltétel ellenőrzés

```bash
grep -n "fn build_all_items\|fn deregister_item\|fn reregister_item" \
  rust/vrs_solver/src/optimizer/cde_adapter.rs
grep -n "live_session\|build_all_items" \
  rust/vrs_solver/src/optimizer/sparrow/worker.rs
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release 2>&1 | tail -3
ls rust/vrs_solver/target/release/vrs_solver
```

## Engedélyezett módosítások

- `scripts/smoke_sgh_q28_dense191_benchmark.py`
- `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs`
- `codex/codex_checklist/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`
- `codex/reports/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`
- `codex/reports/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.verify.log`

## Szigorú tiltások

- Tilos módosítani az algoritmust.
- Tilos létrehozni 276-darabos vagy multisheet benchmark-ot.
- Tilos a Q26 teszteket módosítani.
- Tilos az iteráció gate-et 10 alá csökkenteni a smoke script-ben.

## Végrehajtandó lépések

### Step 1 — Felderítés: 191-instance fixture és binary

```bash
find rust/vrs_solver/tests/fixtures -name "*.json" 2>/dev/null | head -10
ls scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py
cat scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py | head -60
ls rust/vrs_solver/target/release/vrs_solver 2>/dev/null || cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
```

### Step 2 — smoke_sgh_q28_dense191_benchmark.py

A Q26 LV8-derived smoke mintájára, de egyszerűbben:
- Generál egy 191-instance single-sheet JSON-t a real DXF pipeline-nal vagy a meglévő smoke-ból
- Futtatja a solver binárist 90 s time_limit_s-sel
- Kiolvas: `diagnostics.iterations`, `diagnostics.dense_real_run`, `collision_graph_final_pairs`
- Assert gate-ek:
  - `dense_real_run == true`
  - `iterations >= 10`
  - `collision_graph_final_pairs < 55`
- Stdout: `[PASS]` / `[FAIL]` + mért értékek

A diagnosztika JSON-ból való kiolvasáshoz nézd meg, hogyan szerepel a
`solver_diagnostics` a solver output-ban:
```bash
cat rust/vrs_solver/src/adapter.rs | grep -A5 "diagnostics\|SparrowDiagnostics"
```

### Step 3 — Rust integration teszt

Az `sparrow_single_sheet_validation.rs`-ben, a meglévő `q26_*` tesztek után:

```rust
#[test]
#[ignore = "requires 191-instance fixture — run via smoke_sgh_q28_dense191_benchmark.py"]
fn q28_dense_191_incremental_session_speedup() {
    // Ha van 191-instance fixture tests/fixtures-ben:
    // let result = solve_json(include_str!("fixtures/.../dense_191.json"));
    // assert!(result.diagnostics.dense_real_run);
    // assert!(result.diagnostics.iterations >= 5);
}
```

Ha nincs kész fixture, a teszt `#[ignore]`-ban marad és a note rögzíti a smoke script-et.

### Step 4 — Repo gate

```bash
python3 scripts/smoke_sgh_q28_dense191_benchmark.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib 2>&1 | grep "test result"
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md
```
