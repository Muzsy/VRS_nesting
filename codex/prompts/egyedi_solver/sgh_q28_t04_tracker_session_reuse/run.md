# SGH-Q28-T04 — Tracker backward-pair session reuse
TASK_SLUG: sgh_q28_t04_tracker_session_reuse

## Szerep

Rust implementációs agent vagy. A feladatod az `update_after_move` opcionális live session
paraméterrel való bővítése a `tracker.rs`-ben, hogy a backward-pair recompute se építsen
mini-session-öket. Előfeltétel: T01 + T02 + T03 PASS.

## Cél

Módosítsd:

1. `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
2. `rust/vrs_solver/src/optimizer/sparrow/worker.rs` (hívási hely bővítése)
3. `codex/codex_checklist/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
4. `codex/reports/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`

## Kötelező olvasnivaló

1. `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
2. `canvases/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
3. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t04_tracker_session_reuse.yaml`
4. T01–T03 report (PASS ellenőrzés)

## Előfeltétel ellenőrzés

```bash
grep -n "fn build_all_items\|fn deregister_item\|fn reregister_item" \
  rust/vrs_solver/src/optimizer/cde_adapter.rs
grep -n "live_session" rust/vrs_solver/src/optimizer/sparrow/worker.rs
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
```

## Engedélyezett módosítások

- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- `codex/codex_checklist/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
- `codex/reports/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
- `codex/reports/egyedi_solver/sgh_q28_t04_tracker_session_reuse.verify.log`

## Szigorú tiltások

- Tilos módosítani a pair loss kalkuláció matematikáját.
- Tilos eltávolítani a None fallback utat.
- Tilos módosítani az exploration / compression fázist.

## Végrehajtandó lépések

### Step 1 — Felderítés

```bash
grep -n "fn update_after_move" rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
grep -n "CdeCandidateSession\|build_with_policy\|build_sheet_session" \
  rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
```

Azonosítsd a mini-session build helyeket.

### Step 2 — Szignatúra bővítése

```rust
pub fn update_after_move(
    &mut self,
    i: usize,
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheets: &[SheetShape],
    diag: &mut SparrowDiagnostics,
    live_session: Option<&mut CdeCandidateSession>,
)
```

Egyelőre None-ként kezel mindent. Frissítsd a hívási helyeket.

### Step 3 — Some(session) ág a backward-pair recompute-ban

A backward j items feldolgozásakor, ha live_session Some:
- Ne épít mini-session-t
- A session-ben a target már az ÚJ pozícióban van
- j-t deregisztrálni → a session a target + maradék itemekkel query-zik j nélkül
  (ez adja az ütközési állapotot target ÚJ vs j RÉGI pozíció között)
- A query eredménye alapján számítja a pair loss-t (ugyanolyan matemat. mint korábban)
- j-t visszaregisztrálni

### Step 4 — Repo gate

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib 2>&1 | grep "test result"
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md
```
