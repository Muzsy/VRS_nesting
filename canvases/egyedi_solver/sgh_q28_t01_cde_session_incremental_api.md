# SGH-Q28-T01 — `CdeCandidateSession` inkrementális API

## 🎯 Funkció / Cél

- Új `build_all_items` konstruktor a `CdeCandidateSession`-höz: minden darabot regisztrál
  (beleértve a keresési célpontot), így a session újrafelhasználható több egymás utáni mozgatáshoz.
- Új `deregister_item(layout_idx)` metódus: a megadott layout indexű darabot kiveszi a CDEngine-ből.
- Új `reregister_item(layout_idx, new_shape)` metódus: a darabot az új pozícióval visszarakja.
- Új `lookup_hole_slot(layout_idx) -> Option<usize>` helper: layout index → session-beli holes slot.
- Unit test: `cde_session_incremental_eq_full_rebuild` — 10 darabos fixture-n igazolja, hogy
  az inkrementális query ugyanazt adja, mint egy frissen épített full-rebuild session.

## Nem-cél (explicit)

- Nem módosítja a `build_with_policy` / `build` meglévő metódusokat (backward compat marad).
- Nem változtatja a `run_worker_pass` vagy `native_search_placement` logikáját (T02–T03 feladata).
- Nem érinti a `CdeTouchingPolicy` szemantikát.
- Nem exportál publikus API-t a crate boundary-n kívülre.

## 🧠 Fejlesztési részletek

### Scope

**Benne van:**
- `rust/vrs_solver/src/optimizer/cde_adapter.rs`:
  - `CdeCandidateSession::build_all_items(all: Vec<(usize, Rc<CdePreparedShape>)>, sheet: &CdePreparedShape, policy: CdeTouchingPolicy) -> Option<Self>`
    - Regisztrálja az összes darabot `Hole { idx: 0..N }` entitásként (a `build_with_policy`-val azonos logika, de a `target` nincs kizárva)
    - A `holes` vektor teljes (N db bejegyzés)
  - `CdeCandidateSession::deregister_item(&mut self, layout_idx: usize)`
    - Megkeresi a layout_idx-hez tartozó hole slot-ot `self.holes` alapján
    - Hívja `self.cde.deregister_hazard_by_entity(HazardEntity::Hole { idx: slot })`
    - Törli a bejegyzést a `self.holes` vektorból (swap_remove)
  - `CdeCandidateSession::reregister_item(&mut self, layout_idx: usize, new_shape: Rc<CdePreparedShape>)`
    - Megkeresi az újabb free slot index-et (append + `holes.len() - 1`)
    - Hívja `self.cde.register_hazard(Hazard::new(HazardEntity::Hole { idx: new_slot }, ...))`
    - Beilleszt a `self.holes` vektorba
  - `CdeCandidateSession::lookup_hole_slot(&self, layout_idx: usize) -> Option<usize>` (private helper)
- `rust/vrs_solver/src/optimizer/cde_adapter.rs` — unit test modul:
  - `cde_session_incremental_eq_full_rebuild`: 10 darabos szintetikus fixture, 3 kör deregister/reregister, query-eredmény azonos full-rebuild session query-jével

**Nincs benne:**
- `run_worker_pass`, `native_search_placement`, `tracker.rs` módosítása
- `jagua_rs` crate módosítása

### Érintett fájlok

- Módosul: `rust/vrs_solver/src/optimizer/cde_adapter.rs`

### DoD (Definition of Done)

- [ ] `CdeCandidateSession::build_all_items` létezik és dokumentált.
- [ ] `deregister_item` és `reregister_item` helyesen frissítik a `self.holes` vektort és a CDEngine quadtree-t.
- [ ] `lookup_hole_slot` private helper megvan.
- [ ] `cde_session_incremental_eq_full_rebuild` unit test PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md` PASS.

### Kockázatok + mitigáció + rollback

- **Kockázat:** `HazardEntity::Hole { idx }` slot-újrahasznosítás — ha a `deregister` + `reregister`
  ciklus után az idx eltér a korábbi slotnál, a quadtree query rossz hazard-ot érint.
  **Mitigáció:** A slot az aktuális `self.holes.len()`-ből számítódik, nem recycle-ál régi idx-et.
  A unit test explicit verifikálja a query-ekvivalenciát.
- **Rollback:** Csak új metódusok kerülnek hozzá; a meglévő `build_with_policy` érintetlen.
  Visszaállítás = az új metódusok törlése, minden más változatlan.

## 🧪 Tesztállapot

**Kötelező:**
```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib 2>&1 | grep "test result"
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md
```

**Opcionális:**
```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib cde_session_incremental_eq_full_rebuild -- --nocapture
```

## 📎 Kapcsolódások

- Task index: `canvases/egyedi_solver/sgh_q28_incremental_cde_session_task_index.md`
- Következő task: `canvases/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
- Érintett forrás: `rust/vrs_solver/src/optimizer/cde_adapter.rs:738–815`
- jagua-rs CDEngine API: `register_hazard` (L59), `deregister_hazard_by_entity` (L72)
