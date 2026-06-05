# SGH-Q28-T03 — Worker single-session lifecycle
TASK_SLUG: sgh_q28_t03_worker_single_session_lifecycle

## Szerep

Rust implementációs agent vagy. A feladatod a `run_worker_pass` bővítése
pass-szintű single-session lifecycle-lal. Ez az a lépés, ahol az O(N) per-item
session-build ténylegesen O(1) deregister/reregister-re cserélődik.
Előfeltétel: T01 + T02 PASS.

## Cél

Módosítsd:

1. `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
2. `codex/codex_checklist/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
3. `codex/reports/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`

## Kötelező olvasnivaló

1. `AGENTS.md`
2. `docs/codex/yaml_schema.md`
3. `docs/codex/report_standard.md`
4. `canvases/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
5. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t03_worker_single_session_lifecycle.yaml`
6. T01 + T02 report (PASS ellenőrzés)

## Előfeltétel ellenőrzés

```bash
grep -n "fn build_all_items\|fn deregister_item\|fn reregister_item" \
  rust/vrs_solver/src/optimizer/cde_adapter.rs
grep -n "live_session" rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
```

## Engedélyezett módosítások

- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- `codex/codex_checklist/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
- `codex/reports/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
- `codex/reports/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.verify.log`

## Szigorú tiltások

- Tilos módosítani a GLS weight update logikát.
- Tilos megváltoztatni az elfogadási kritériumot.
- Tilos módosítani tracker.update_after_move-t (T04).
- Tilos módosítani az exploration / compression fázist.

## Végrehajtandó lépések

### Step 1 — Felderítés: tracker.update_after_move sorrendje

```bash
grep -n "update_after_move\|shapes\[target\]\|shapes\[" \
  rust/vrs_solver/src/optimizer/sparrow/worker.rs
grep -n "fn update_after_move\|self\.shapes\[" \
  rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs | head -20
```

Kritikus kérdés: `tracker.update_after_move` UTÁN a `tracker.shapes[target]` már az ÚJ shape-t
tartalmazza-e? Ha igen, a reregister a `tracker.shapes[target]` alapján mehet.

### Step 2 — Session build a pass elején

A `run_worker_pass`-ban, közvetlenül a `colliding` lista meghatározása után:

```rust
// Single-sheet session az első colliding target sheet-jéhez
let primary_sheet_idx = colliding.first()
    .map(|&t| layout.placements[t].sheet_index)
    .unwrap_or(0);
let primary_sheet_shape = tracker.sheet_shapes
    .get(primary_sheet_idx)
    .and_then(|s| s.clone());
let all_on_primary_sheet: Vec<(usize, Rc<CdePreparedShape>)> = (0..layout.placements.len())
    .filter(|&j| layout.placements[j].sheet_index == primary_sheet_idx)
    .filter_map(|j| tracker.shapes[j].clone().map(|s| (j, s)))
    .collect();
let initial_session_size = all_on_primary_sheet.len();
let mut live_session: Option<CdeCandidateSession> = primary_sheet_shape
    .as_ref()
    .and_then(|ss| CdeCandidateSession::build_all_items(
        all_on_primary_sheet,
        ss,
        CdeTouchingPolicy::SparrowStrict,
    ));
```

### Step 3 — Item ciklus: session átadás + reregister

```rust
for target in colliding {
    // ... deadline check, loss check ...
    
    let old_shape = tracker.shapes[target].clone(); // reregister fallback-hez
    let use_session = live_session.is_some()
        && layout.placements[target].sheet_index == primary_sheet_idx;
    
    let Some(newp) = native_search_placement(
        target, &layout, instances, &tracker, sheets, cfg, &mut rng, started, deadline, diag,
        if use_session { live_session.as_mut() } else { None },
    ) else {
        // Visszautasítás: session-t visszaállítani (T02-ben a deregister már megtörtént)
        if use_session {
            if let (Some(session), Some(shape)) = (live_session.as_mut(), old_shape) {
                session.reregister_item(target, shape);
            }
        }
        rejected += 1;
        continue;
    };
    
    // ... layout.placements[target] = newp; tracker.update_after_move(...) ...
    
    // Elfogadás/visszautasítás (new_w vs old_w)
    if new_w <= old_w + 1e-9 {
        // Elfogadás: reregister az ÚJ shape-pel (update_after_move után)
        if use_session {
            if let (Some(session), Some(new_shape)) = (live_session.as_mut(), tracker.shapes[target].clone()) {
                session.reregister_item(target, new_shape);
            }
        }
        accepted += 1;
    } else {
        layout.placements[target] = old_p;
        tracker.restore_keep_weights(snap);
        // Visszautasítás: reregister az EREDETI shape-pel
        if use_session {
            if let (Some(session), Some(shape)) = (live_session.as_mut(), old_shape) {
                session.reregister_item(target, shape);
            }
        }
        rejected += 1;
    }
}
```

### Step 4 — debug_assert session konzisztencia

```rust
debug_assert!(
    live_session.as_ref()
        .map_or(true, |s| s.hazard_count() == initial_session_size),
    "session holes count mismatch after pass: {} vs {}",
    live_session.as_ref().map_or(0, |s| s.hazard_count()),
    initial_session_size,
);
```

### Step 5 — Repo gate

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib 2>&1 | grep "test result"
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md
```
