PASS

## 1) Meta

* **Task slug:** `sgh_q28_t03_worker_single_session_lifecycle`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t03_worker_single_session_lifecycle.yaml`
* **Futás dátuma:** `2026-06-05`
* **Branch / commit:** `main`
* **Fókusz terület:** Rust | Solver | Performance

## 2) Scope

### 2.1 Cél

- `run_worker_pass` pass elején `build_all_items`-szel épít egyetlen `CdeCandidateSession`-t
- Minden single-sheet target esetén `native_search_placement`-nek `Some(&mut live_session)` megy
- Elfogadás/visszautasítás után reregister a tracker-ből vett aktuális shape-pel
- Degenerate (None session) esetén `None` fallback (per-item build, T02 backward compat)
- `debug_assert` a pass végén: `hazard_count == initial_session_size`

### 2.2 Nem-cél (explicit)

- GLS weight update logika módosítása
- Elfogadási kritérium változtatása
- `tracker.update_after_move` session-kezelés (T04)
- Exploration / compression módosítás

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

* **Rust:**
  * `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
  * `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs` (bugfix: deregister áthelyezve)

### 3.2 Miért változtak?

**worker.rs:** `run_worker_pass` a `colliding` lista meghatározása után egyszer épít session-t a primary sheet összes itemjéből. Az item-ciklusban `use_session` flag vezérli, hogy `Some(&mut live_session)` megy-e. A 3 kilépési pont mindegyikénél (search None, accept, reject) `reregister_item`-et hív `tracker.shapes[target].clone()`-nal, amely mindig a helyes (elfogadott új vagy visszaállított régi) shape-t tartalmazza.

**search.rs (bugfix):** A `deregister_item` hívást a `prepare_base_shape_native` `?`-early-return és a belső ciklus `deadline`-check elé kellett mozgatni. Különben ha a deadline épp a rank-0 iteráció elején telt le (a deregister előtt), a függvény `None`-nal tért vissza, de `worker.rs` feltételezte, hogy a deregisternálás megtörtént, és feleslegesen `reregister`-t hívott — `hazard_count` eggyel nőtt. Az invariáns: ha `live_session` Some, a target mindig deregistered állapotban marad visszatéréskor.

## 4) Verifikáció

### 4.1 Kötelező parancs

* `cargo test --manifest-path rust/vrs_solver/Cargo.toml` → `455 lib + 8 integration` (PASS)

### 4.2 Opcionális

* `cargo test ... native_optimizer_worker_competition_is_active -- --nocapture` → `ok` (korábban flaky, most stabil)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
*(verify.sh az összesített check.sh gate-et futtatja — Rust unit + integration tesztek PASS, verify futtatás T05-ben szükséges)*
<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + sor) | Magyarázat |
|----------|---------|------------------------|------------|
| `run_worker_pass` egyszer épít session-t per pass | PASS | `worker.rs:43–59` | `build_all_items` hívás a colliding lista után |
| `native_search_placement` `Some(&mut session)` kap | PASS | `worker.rs:79–83` | `if use_session { live_session.as_mut() } else { None }` |
| Accept reregister: new shape | PASS | `worker.rs:98–104` | `tracker.shapes[target]` = new shape after `update_after_move` |
| Reject reregister: old shape (acceptance criterion) | PASS | `worker.rs:107–113` | `tracker.shapes[target]` = old shape after `restore_keep_weights` |
| Reject reregister: old shape (search None) | PASS | `worker.rs:87–93` | `tracker.shapes[target]` = old shape (update_after_move nem futott) |
| `debug_assert` session konzisztencia | PASS | `worker.rs:117–122` | `hazard_count == initial_session_size` |
| Bugfix: deregister invariant | PASS | `search.rs:212–218` | deregister a `prepare_base_shape_native ?` és deadline check előtt |
| Összes meglévő teszt PASS (455 lib + 8 integration) | PASS | `455 passed; 0 failed` | Nincs regresszió |
