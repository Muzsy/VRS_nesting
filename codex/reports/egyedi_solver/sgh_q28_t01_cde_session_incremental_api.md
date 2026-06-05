PASS

## 1) Meta

* **Task slug:** `sgh_q28_t01_cde_session_incremental_api`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t01_cde_session_incremental_api.yaml`
* **Futás dátuma:** `2026-06-05`
* **Branch / commit:** `main`
* **Fókusz terület:** Rust | Solver | Performance

## 2) Scope

### 2.1 Cél

- `CdeCandidateSession::build_all_items` konstruktor hozzáadása
- `deregister_item` / `reregister_item` inkrementális hazard-management metódusok
- `lookup_hole_slot` private helper
- `holes` mező típusmódosítása `Vec<Option<...>>`-re (slot-indexelés megőrzése)
- `cde_session_incremental_eq_full_rebuild` unit teszt

### 2.2 Nem-cél (explicit)

- `run_worker_pass`, `native_search_placement`, `tracker.rs` módosítása (T02–T04)
- Publikus API exportálás
- `jagua-rs` crate módosítása

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

* **Rust:**
  * `rust/vrs_solver/src/optimizer/cde_adapter.rs`

### 3.2 Miért változtak?

A `holes` mező típusa `Vec<(usize, Rc<CdePreparedShape>)>`-ről `Vec<Option<(usize, Rc<CdePreparedShape>)>>`-re változott. A `deregister_item` után a CDEngine `HazardEntity::Hole { idx: slot }` entitások slot-száma nem változhat (nincs swap_remove) — a `None`-slot jelöli az inaktív bejegyzést. A `query` és `SinkAdapter` mindkettőnél a `Some(Some(...))` mintát alkalmazza.

## 4) Verifikáció

### 4.1 Kötelező parancs

* `cargo test --manifest-path rust/vrs_solver/Cargo.toml` → `455 lib + 8 integration` (PASS)

### 4.2 Opcionális parancsok

* `cargo test ... cde_session_incremental_eq_full_rebuild -- --nocapture` → `ok` (PASS)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
*(verify.sh az összesített check.sh gate-et futtatja — Rust unit + integration tesztek PASS, verify futtatás T05-ben szükséges)*
<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + sor) | Magyarázat |
|----------|---------|------------------------|------------|
| `build_all_items` pub(crate), létezik | PASS | `cde_adapter.rs:813–819` | Delegál `build_with_policy`-ra |
| `deregister_item` frissíti holes + CDEngine | PASS | `cde_adapter.rs:832–837` | `holes[slot] = None`, `cde.deregister_hazard_by_entity` |
| `reregister_item` appendi holes + CDEngine register | PASS | `cde_adapter.rs:840–847` | `new_slot = holes.len()`, `cde.register_hazard` |
| `lookup_hole_slot` private helper megvan | PASS | `cde_adapter.rs:827–829` | `position` scan aktív `Some` slotokra |
| `build_with_policy` / `build` érintetlen | PASS | Csak `others.into_iter().map(Some)` típusadaptáció | Meglévő szemantika változatlan |
| `cde_session_incremental_eq_full_rebuild` PASS | PASS | `test result: ok. 455 passed` | 10 item × 10 target körön át, query ekvivalencia assertálva |
| Összes meglévő teszt PASS (454→455 lib + 8 integration) | PASS | `455 passed; 0 failed` | 1 új teszt hozzáadva, minden régit zöld maradt |
