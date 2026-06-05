# SGH-Q28-T02 — `native_search_placement` session passthrough

## 🎯 Funkció / Cél

- `build_sheet_session` helyett egy új `build_sheet_session_full` függvény, amely a céldarab
  session-beli deregisztrálását a hívóra bízza (T01 API-t használja).
- `native_search_placement` kap egy opcionális `session: Option<&mut CdeCandidateSession>`
  paramétert; ha `Some`, deregisztrál a session-ből, futtatja a keresést, majd visszaregisztrálja
  az elfogadott pozícióba — ha `None`, a jelenlegi `build_sheet_session`-t hívja (backward compat).
- A `SeparationEvaluator` kompatibilis marad — nem változik a szignatúrája.

## Nem-cél (explicit)

- Nem módosítja `run_worker_pass`-t — az T03 feladata.
- Nem változtatja a keresési algoritmus logikáját (sampling, coord-descent, acceptance).
- Nem érinti a multi-sheet cross-sheet logikát (T02-ban a session csak az aktuális sheetre érvényes).
- Nem módosítja a `CdeCandidateSession::query` metódust.

## 🧠 Fejlesztési részletek

### Scope

**Benne van:**
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`:
  - `native_search_placement` új szignatúra:
    ```rust
    pub(crate) fn native_search_placement(
        target: usize,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        tracker: &SparrowCollisionTracker,
        sheets: &[SheetShape],
        cfg: &SparrowConfig,
        rng: &mut DeterministicRng,
        started: &Instant,
        deadline: f64,
        diag: &mut SparrowDiagnostics,
        live_session: Option<&mut CdeCandidateSession>,
    ) -> Option<SparrowPlacement>
    ```
  - Ha `live_session` = `Some(session)` és a keresés az aktuális sheeten folyik:
    `session.deregister_item(target)` → keresés → `session.reregister_item(target, új_shape)`
  - Ha `None` vagy cross-sheet: jelenlegi `build_sheet_session` hívás (fallback)
  - Meglévő hívók (`optimizer.rs` probe hívás) kapnak `None` argumentumot

**Nincs benne:**
- `run_worker_pass` módosítása (T03)
- `tracker.rs` módosítása (T04)

### Érintett fájlok

- Módosul: `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
- Módosul (kisebb): `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs` (probe hívás `None`-ra)

### DoD (Definition of Done)

- [ ] `native_search_placement` új opcionális `live_session` paraméterrel rendelkezik.
- [ ] `None` esetén a viselkedés azonos a T02 előtti állapottal (backward compat).
- [ ] `Some(session)` esetén deregister → keresés → reregister helyes sorrendben fut.
- [ ] Az `optimizer.rs` probe hívás fordítható és `None`-t ad át.
- [ ] Összes meglévő teszt PASS (454 lib + 8 integration).
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t02_search_session_passthrough.md` PASS.

### Kockázatok + mitigáció + rollback

- **Kockázat:** A `reregister_item` az elfogadott új pozíció shape-jével hívódik; ha az
  elfogadás nem jön létre (rejection), a session helyes-e?
  **Mitigáció:** Rejection esetén `reregister_item`-et az eredeti shape-pel kell hívni.
  T02 ezt explicit kezeli.
- **Rollback:** Az `Option<&mut CdeCandidateSession>` paraméter eltávolítható; a meglévő
  `build_sheet_session` logika érintetlen marad a `None` ágban.

## 🧪 Tesztállapot

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t02_search_session_passthrough.md
```

## 📎 Kapcsolódások

- Előző task: `canvases/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
- Következő task: `canvases/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
- Érintett forrás: `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs:194–291`
