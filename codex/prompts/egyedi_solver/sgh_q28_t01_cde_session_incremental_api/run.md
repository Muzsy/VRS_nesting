# SGH-Q28-T01 — CdeCandidateSession inkrementális API
TASK_SLUG: sgh_q28_t01_cde_session_incremental_api

## Szerep

Rust implementációs agent vagy. A feladatod a `CdeCandidateSession` struktúra bővítése
inkrementális hazard-management metódusokkal a `rust/vrs_solver/src/optimizer/cde_adapter.rs`
fájlban, a jagua-rs `CDEngine` meglévő `register_hazard` / `deregister_hazard_by_entity` API
felhasználásával. Implementáción kívül semmit nem csinálsz.

## Cél

Hozd létre / módosítsd:

1. `rust/vrs_solver/src/optimizer/cde_adapter.rs` (új metódusok + unit test)
2. `codex/codex_checklist/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
3. `codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`

Ne módosítsd a `run_worker_pass`-t, `native_search_placement`-t, vagy `tracker.rs`-t.

## Kötelező olvasnivaló prioritási sorrendben

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `canvases/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
7. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t01_cde_session_incremental_api.yaml`
8. Minta (hasonló Rust impl task):
   - `canvases/egyedi_solver/sgh_q24r9_exact_upstream_style_tracker_evaluator_search_semantics.md`

Ha bármelyik kötelező szabályfájl hiányzik, állj meg és FAIL-ként rögzítsd a reportban.

## Előfeltétel ellenőrzés

```bash
ls AGENTS.md || echo "STOP: AGENTS.md missing"
ls docs/codex/yaml_schema.md || echo "STOP: yaml schema missing"
ls docs/codex/report_standard.md || echo "STOP: report standard missing"
ls rust/vrs_solver/src/optimizer/cde_adapter.rs || echo "STOP: cde_adapter.rs missing"
ls canvases/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md || echo "STOP: canvas missing"
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
```

## Valós repo anchorok ellenőrzése

```bash
grep -n "struct CdeCandidateSession" rust/vrs_solver/src/optimizer/cde_adapter.rs
grep -n "fn build_with_policy" rust/vrs_solver/src/optimizer/cde_adapter.rs
grep -n "fn register_hazard\|fn deregister_hazard_by_entity" \
  ~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/jagua-rs-0.6.4/src/collision_detection/cd_engine.rs
grep -n "HazardEntity" \
  ~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/jagua-rs-0.6.4/src/collision_detection/hazards/mod.rs \
  2>/dev/null | head -20
```

## Engedélyezett módosítások

Csak ezek a fájlok hozhatók létre vagy módosíthatók:

- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
- `codex/codex_checklist/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
- `codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
- `codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.verify.log`

## Szigorú tiltások

- Tilos módosítani `build_with_policy`, `build`, vagy `query` meglévő metódusokat.
- Tilos módosítani `worker.rs`, `search.rs`, `tracker.rs`-t.
- Tilos módosítani a `jagua-rs` crate-et.
- Tilos publikus API-t exportálni (csak `pub(crate)` / `pub(super)` / private).
- Tilos a `docs/codex/yaml_schema.md` sémájától eltérő YAML-t írni.

## Végrehajtandó lépések

### Step 1 — Felderítés és baseline rögzítése

```bash
sed -n '738,870p' rust/vrs_solver/src/optimizer/cde_adapter.rs
sed -n '50,100p' ~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/jagua-rs-0.6.4/src/collision_detection/cd_engine.rs
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
```

Rögzítsd a `CdeCandidateSession` struct mezőit, a `build_with_policy` logikáját,
és a jagua-rs CDEngine `register_hazard` / `deregister_hazard_by_entity` szignatúráját a reportban.

### Step 2 — build_all_items implementálása

A `cde_adapter.rs` `CdeCandidateSession` impl blokkjába, közvetlenül a `build_with_policy` után:

```rust
pub(crate) fn build_all_items(
    all: Vec<(usize, Rc<CdePreparedShape>)>,
    sheet: &CdePreparedShape,
    touching_policy: CdeTouchingPolicy,
) -> Option<Self> {
    Self::build_with_policy(all, sheet, touching_policy)
}
```

(A `build_with_policy` már az összes átadott elemet regisztrálja; `build_all_items` csak
egy névvel ellátott belépési pont, ahol a hívó tudatosan átadja a target-et is.)

### Step 3 — lookup_hole_slot, deregister_item, reregister_item implementálása

```rust
fn lookup_hole_slot(&self, layout_idx: usize) -> Option<usize> {
    self.holes.iter().position(|(idx, _)| *idx == layout_idx)
}

pub(crate) fn deregister_item(&mut self, layout_idx: usize) {
    let Some(slot) = self.lookup_hole_slot(layout_idx) else { return };
    self.cde.deregister_hazard_by_entity(HazardEntity::Hole { idx: slot });
    self.holes.swap_remove(slot);
    // swap_remove-val a slot-ra kerülő új elem CDEngine bejegyzése érintetlen
    // (a CDEngine HazKey alapon nyilvántart, az idx csak az entitás azonosítója)
}

pub(crate) fn reregister_item(&mut self, layout_idx: usize, new_shape: Rc<CdePreparedShape>) {
    let new_slot = self.holes.len();
    self.cde.register_hazard(Hazard::new(
        HazardEntity::Hole { idx: new_slot },
        new_shape.spoly.clone(),
        false,
    ));
    self.holes.push((layout_idx, new_shape));
}
```

Ellenőrizd, hogy a `Hazard`, `HazardEntity` import-ok megvannak-e a fájl tetején.
Ha hiányzik, add hozzá a meglévő import blokkhoz.

### Step 4 — Unit test implementálása

A fájl alján lévő `#[cfg(test)] mod tests` blokkban (vagy create it if missing):

```rust
#[test]
fn cde_session_incremental_eq_full_rebuild() {
    // 10 egyszerű téglalap layout-ban, 1 sheet
    // build_all_items → deregister target → query → build_with_policy(maradék 9) → query
    // assert_eq!(result_incremental, result_full_rebuild)
    // reregister → következő target...
}
```

Részletek a canvas DoD szekciójában. A tesztnek meg kell találnia a szükséges
builder-eket (pl. `CdePreparedShape` tesztben való felépítése — nézd meg a meglévő
cde-teszteket a fájlban vagy a `tests/` könyvtárban mintaként).

### Step 5 — Repo gate

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib 2>&1 | grep "test result"
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib cde_session_incremental_eq_full_rebuild -- --nocapture
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md
```

Frissítsd az AUTO_VERIFY blokkot a reportban.
