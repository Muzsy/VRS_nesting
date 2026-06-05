# SGH-Q28 — Inkrementális CDE session (dense 191 konvergencia) — Task index

## Miért létezik ez a task-sorozat?

A jelenlegi `sparrow_cde` solver minden egyes keresési híváshoz (`native_search_placement`)
felépít egy teljes `CdeCandidateSession`-t — azaz egy `CDEngine` quadtree-t az összes
azonos sheeten lévő darabból. 191 darabos LV8 esetén ez **~362 ms/hívás** (O(N) build),
miközben maga a CDE-query csak ~47 µs. Egy worker pass során ~100 ütköző darabot kell
elmozdítani, ami **18–36 másodperc/iteráció**; 900 s budgetből így csak ~25 iteráció fér be.

Az eredeti Sparrow upstream (`jagua_rs` `Layout.cde()`) ezt inkrementálisan oldja meg:
a `CDEngine` **támogatja a `register_hazard` / `deregister_hazard_by_entity` hívásokat**,
amelyek a quadtree-t is frissítik. Egy worker passra elegendő **1× build + N × deregister/reregister**,
ami becsülten ~23× gyorsabb iterációt ad → ~550 iteráció 900 s alatt.

## Task-lánc

| Slug | Cím | Függőség |
|------|-----|----------|
| `sgh_q28_t01` | `CdeCandidateSession` inkrementális API | — |
| `sgh_q28_t02` | `native_search_placement` session passthrough | T01 |
| `sgh_q28_t03` | Worker single-session lifecycle (`run_worker_pass`) | T02 |
| `sgh_q28_t04` | Tracker backward-pair session reuse (`update_after_move`) | T03 |
| `sgh_q28_t05` | Dense 191 benchmark gate + Q28 validation suite | T04 |

## Kritikus path

```text
T01 → T02 → T03 → T04 → T05
```

## Érintett fájlok (összesített)

- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
- `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs` (T05)
- `scripts/smoke_sgh_q28_dense191_benchmark.py` (T05)

## Nem-cél (explicit)

- Nem módosítja a GLS algoritmus logikáját (súlyozás, ordering, exploration)
- Nem érinti a multi-sheet keresési útvonalat (az T03-ban fallback marad)
- Nem változtatja a `CdeTouchingPolicy` szemantikát
- Nem érinti a kompressziós fázist
- Nem bővíti a `jagua_rs` crate-et (csak a meglévő `register_hazard` / `deregister_hazard_by_entity` API-t használja)

## Minőségkapu

Minden task végén:
```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md
```

T05 végén kötelező még:
```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
python3 scripts/smoke_sgh_q28_dense191_benchmark.py
```

## Baseline (T01 előtt kötelező rögzíteni)

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
# Elvárt: 454 passed (lib) + 8 passed (integration)
```
