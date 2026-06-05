# SGH-Q28-T04 — Tracker backward-pair session reuse

## 🎯 Funkció / Cél

- A `tracker.update_after_move` jelenleg minden backward-pair recompute-hoz külön
  `CdeCandidateSession`-t épít (mini session az érintett párhoz). Ezek is O(N) buildek.
- T04 átírja az `update_after_move`-t úgy, hogy ha a hívó átad egy live session-t,
  a backward-pair recompute a live session-t használja deregister/query/reregister ciklussal.
- Új opcionális `live_session: Option<&mut CdeCandidateSession>` paraméter az `update_after_move`-ban.
- Ha `None`: jelenlegi per-pair mini-session build (backward compat).
- `run_worker_pass` (T03-ban módosított) átadja a live session-t `update_after_move`-nak.

## Nem-cél (explicit)

- Nem módosítja a GLS weight update logikát.
- Nem módosítja a pair loss kalkuláció matematikáját (overlap_proxy, overlap_proxy_boundary).
- Nem változtatja az exploration / compression fázist.
- Nem módosítja a `build_with_policy` backward compat útját.

## 🧠 Fejlesztési részletek

### Scope

**Benne van:**
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`:
  - `update_after_move` új szignatúra: `live_session: Option<&mut CdeCandidateSession>` paraméter
  - Ha `Some(session)`: backward-pair recompute a session-nel (deregister j → query i vs j → reregister j)
  - Ha `None`: jelenlegi mini-session build (fallback, backward compat)
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`:
  - `tracker.update_after_move(target, ...)` hívás kibővítve `live_session.as_mut()` átadással

**Nincs benne:**
- `native_search_placement` módosítása
- Más tracker metódus módosítása

### Érintett fájlok

- Módosul: `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
- Módosul (kisebb): `rust/vrs_solver/src/optimizer/sparrow/worker.rs`

### DoD (Definition of Done)

- [ ] `update_after_move` opcionális `live_session` paraméterrel rendelkezik.
- [ ] `Some` esetén backward-pair recompute a live session-t használja.
- [ ] `None` esetén a viselkedés azonos a T04 előtti állapottal.
- [ ] `run_worker_pass` átadja a session-t `update_after_move`-nak.
- [ ] Összes meglévő teszt PASS (454 lib + 8 integration).
- [ ] `./scripts/verify.sh` PASS.

### Kockázatok + mitigáció + rollback

- **Kockázat:** A backward-pair recompute komplex — a session-ben a target már az ÚJ
  pozícióban van (reregisztrálva T03-ban), a `j` itemek még az eredeti pozícióban. A
  query tehát az ÚJ target vs RÉGI j párokat vizsgálja — ez pontosan helyes.
  **Mitigáció:** A unit test ellenőrzi, hogy az inkrementális és a full-rebuild session
  ugyanolyan collision eredményt ad.
- **Rollback:** `None` visszaállítása minden hívási helyen → per-pair mini-session build.

## 🧪 Tesztállapot

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml 2>&1 | grep "test result"
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md
```

## 📎 Kapcsolódások

- Előző task: `canvases/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
- Következő task: `canvases/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md`
- Érintett forrás: `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
