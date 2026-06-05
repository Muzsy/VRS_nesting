# SGH-Q28-T02 — native_search_placement session passthrough
TASK_SLUG: sgh_q28_t02_search_session_passthrough

## Szerep

Rust implementációs agent vagy. A feladatod a `native_search_placement` függvény opcionális
`live_session` paraméterrel való bővítése a `search.rs`-ben. Előfeltétel: T01 PASS.

## Cél

Módosítsd / hozd létre:

1. `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
2. `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs` (kisebb)
3. `rust/vrs_solver/src/optimizer/sparrow/worker.rs` (hívási hely frissítés)
4. `codex/codex_checklist/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
5. `codex/reports/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`

## Kötelező olvasnivaló

1. `AGENTS.md`
2. `docs/codex/yaml_schema.md`
3. `docs/codex/report_standard.md`
4. `canvases/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
5. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t02_search_session_passthrough.yaml`
6. `codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md` (T01 PASS ellenőrzés)

## Előfeltétel ellenőrzés

```bash
grep -n "fn build_all_items\|fn deregister_item\|fn reregister_item" \
  rust/vrs_solver/src/optimizer/cde_adapter.rs
# Mind a három metódusnak meg kell lennie (T01 PASS)
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
```

## Engedélyezett módosítások

- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
- `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs`
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- `codex/codex_checklist/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
- `codex/reports/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
- `codex/reports/egyedi_solver/sgh_q28_t02_search_session_passthrough.verify.log`

## Szigorú tiltások

- Tilos módosítani a keresési algorithmus logikáját (sampling, coord-descent, acceptance).
- Tilos eltávolítani a build_sheet_session fallback utat.
- Tilos módosítani run_worker_pass-t érdemben (csak a hívási hely None-ra frissítése engedélyezett).
- Tilos módosítani tracker.rs-t.

## Végrehajtandó lépések

### Step 1 — Felderítés

```bash
sed -n '194,291p' rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
sed -n '60,82p' rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
grep -n "native_search_placement" rust/vrs_solver/src/optimizer/sparrow/worker.rs
```

### Step 2 — Szignatúra bővítése (None fallback)

`native_search_placement` utolsó paramétere legyen:
```rust
live_session: Option<&mut CdeCandidateSession>,
```
Egyelőre a `live_session`-t nem használja a törzs; minden hívási hely `None`-t kap.
Ellenőrizd: `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` ← zöld kell.

### Step 3 — Some(session) ág implementálása

Az aktuális sheet (rank==0) blokkban, `build_sheet_session` hívás előtt:

```rust
if let Some(ref mut session) = live_session {
    // Deregisztrálás: a target ki van véve a session-ből
    session.deregister_item(target);
    // session-t adjuk az evaluator-nak build_sheet_session helyett
    // ... [evaluator session = session]
    // search fut
    // elfogadás esetén: reregister az új shape-pel
    // visszautasítás esetén: reregister az eredeti shape-pel
} else {
    // meglévő build_sheet_session fallback
}
```

Rejection kezelés: ha a `run_worker_pass` elfogadási döntése a search után jön (worker.rs-ben),
akkor a `native_search_placement` csak a keresési eredményt adja vissza — az elfogadást a
worker végzi. Ezért T02-ban a reregister az elfogadott placement-tel a `run_worker_pass`-ban
kell megtörténjen (a search.rs csak deregisztrál és keres). Ezt a T03 zárja le.

Azaz T02-ban: search.rs deregisztrált → keresés → visszaadja `Some(newp)` vagy `None` →
a session a deregisztrált állapotban marad → T03 fogja a reregiszter-t elvégezni.

### Step 4 — Repo gate

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib 2>&1 | grep "test result"
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t02_search_session_passthrough.md
```
