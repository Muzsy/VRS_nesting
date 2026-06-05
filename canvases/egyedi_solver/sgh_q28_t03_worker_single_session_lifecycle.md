# SGH-Q28-T03 — Worker single-session lifecycle

## 🎯 Funkció / Cél

- A `run_worker_pass` pass elején egyszer épít `CdeCandidateSession`-t az összes azonos sheeten
  lévő darabból (`build_all_items`).
- Minden colliding target mozgatásakor `native_search_placement`-nek átadja a live session-t
  (`Some(&mut session)`).
- A search.rs T02-ban elkészített deregister/reregister logikája fut: deregisztrál → keres →
  elfogadás esetén reregisztrál az új shape-pel, visszautasítás esetén az eredeti shape-pel.
- Ha `build_all_items` `None`-t ad vissza (degenerate bbox), fallback: `None` session (per-item build).
- Multi-sheet esetén a session-passthrough nem aktív (cross-sheet fallback változatlan marad).

## Nem-cél (explicit)

- Nem módosítja a GLS weight update logikát.
- Nem változtatja az elfogadási kritériumot (`new_w <= old_w + 1e-9`).
- Nem érinti a `tracker.update_after_move` session-kezelést — az T04 feladata.
- Nem módosítja az exploration vagy compression fázist.

## 🧠 Fejlesztési részletek

### Scope

**Benne van:**
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`:
  - `run_worker_pass` elején (a `colliding` lista után):
    ```rust
    let sheet_idx = /* az első colliding elem sheete, vagy 0 ha üres */ ;
    let sheet_shape = tracker.sheet_shapes.get(sheet_idx).and_then(|s| s.clone());
    let all_on_sheet: Vec<(usize, Rc<CdePreparedShape>)> = (0..layout.placements.len())
        .filter(|&j| layout.placements[j].sheet_index == sheet_idx)
        .filter_map(|j| tracker.shapes[j].clone().map(|s| (j, s)))
        .collect();
    let mut live_session: Option<CdeCandidateSession> = sheet_shape
        .and_then(|ss| CdeCandidateSession::build_all_items(all_on_sheet, &ss, CdeTouchingPolicy::SparrowStrict));
    ```
  - Az item-ciklusban `native_search_placement`-nek `live_session.as_mut()` átadása.
  - Az elfogadás/visszautasítás után a reregister elvégzése:
    - elfogadás: `session.reregister_item(target, tracker.shapes[target].clone()?)`
    - visszautasítás: `session.reregister_item(target, eredeti_shape)`
  - Single-sheet only: ha `cur.sheet_index != sheet_idx`, session-passthrough nem aktív.

**Nincs benne:**
- `tracker.update_after_move` session-passthrough (T04)
- Exploration / compression módosítás

### Érintett fájlok

- Módosul: `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- Módosul (kisebb): `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
  (reregister logika a deregister-hez kapcsoltan)

### DoD (Definition of Done)

- [ ] `run_worker_pass` egyszer épít session-t per pass (single-sheet esetén).
- [ ] `native_search_placement` `Some(&mut session)`-t kap minden single-sheet target esetén.
- [ ] Elfogadás/visszautasítás után a session reregisztrált állapotba kerül.
- [ ] Degenerate bbox esetén (None session) a fallback per-item build fut.
- [ ] Összes meglévő teszt PASS (454 lib + 8 integration).
- [ ] `./scripts/verify.sh` PASS.

### Kockázatok + mitigáció + rollback

- **Kockázat:** Elfogadás utáni `tracker.shapes[target]` még a mozgatás előtti shape-t tartalmazza
  (`update_after_move` már lefutott? Vagy nem?).
  **Mitigáció:** A reregister `tracker.update_after_move` után fut, amikor a tracker.shapes[target]
  már az új pozíciót tükrözi. A sorrend pontosan rögzítendő a canvas-ban és unit test-tel ellenőrizendő.
- **Rollback:** `live_session.as_mut()` helyett `None` visszaállítása → per-item build (T02 óta stabil).

## 🧪 Tesztállapot

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md
```

## 📎 Kapcsolódások

- Előző task: `canvases/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
- Következő task: `canvases/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
- Érintett forrás: `rust/vrs_solver/src/optimizer/sparrow/worker.rs:27–98`
