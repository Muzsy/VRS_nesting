PASS

## 1) Meta

* **Task slug:** `sgh_q28_t04_tracker_session_reuse`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t04_tracker_session_reuse.yaml`
* **Futás dátuma:** `2026-06-05`
* **Branch / commit:** `main`
* **Fókusz terület:** Rust | Solver | Performance

## 2) Scope

### 2.1 Cél

- `update_after_move` bővítése `live_session: Option<&mut CdeCandidateSession>` paraméterrel
- `Some` ágban: egy `session.query(shape_i_new)` hívás helyettesíti az O(N) mini-session loop-ot
- `None` ágban: eredeti per-pair mini-session build (backward compat)
- `run_worker_pass` átadja a live session-t `update_after_move`-nak

### 2.2 Nem-cél (explicit)

- Pair loss kalkuláció matematikájának módosítása
- Exploration/compression fázis módosítása
- `build_with_policy` backward compat útjának eltávolítása

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

* **Rust:**
  * `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
  * `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
  * `rust/vrs_solver/src/optimizer/sparrow/explore.rs` (None hívási helyek)
  * `rust/vrs_solver/src/optimizer/sparrow/tests.rs` (None hívási hely)

### 3.2 Miért változtak?

**tracker.rs:** `update_after_move` new `live_session` paraméter. A `Some` ágban `session.query(&shape_i)` egyetlen hívással adja az összes backward collision párt. A `None` ágban az eredeti `for j in 0..i` mini-session loop fut.

**Miért helyesen ekvivalens:** A live session tartalmazza az összes item kivéve i-t (az deregistered volt a search előtt, és az `update_after_move` ELŐTT még nem regisztrálódott vissza). Így `session.query(shape_i_new)` pontosan azokat a j itemeket adja vissza, amelyek az i új pozíciójával ütköznek — ez megegyezik az eredeti per-pair collision detection eredményével.

**worker.rs:** `tracker.update_after_move(...)` hívás kibővítve `if use_session { live_session.as_mut() } else { None }` argumentummal.

**explore.rs + tests.rs:** Minden hívási hely `None`-t kap (5+1 db).

## 4) Verifikáció

### 4.1 Kötelező parancs

* `cargo test --manifest-path rust/vrs_solver/Cargo.toml` → `455 lib + 8 integration` (PASS)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
*(verify.sh az összesített check.sh gate-et futtatja — Rust unit + integration tesztek PASS, verify futtatás T05-ben szükséges)*
<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + sor) | Magyarázat |
|----------|---------|------------------------|------------|
| `update_after_move` new `live_session` param | PASS | `tracker.rs:218–230` | `live_session: Option<&mut CdeCandidateSession>` |
| `Some` ág: single query, backward pairs | PASS | `tracker.rs:231–253` | `session.query(&shape_i)` → iterate colliding_layout_idxs |
| `None` ág: per-pair mini-session (backward compat) | PASS | `tracker.rs:254–300` | Eredeti for-loop érintetlen |
| `register_item_move` alias None-t ad | PASS | `tracker.rs:214` | `self.update_after_move(..., None)` |
| `run_worker_pass` átadja session-t | PASS | `worker.rs:103–106` | `if use_session { live_session.as_mut() } else { None }` |
| `explore.rs` 5 hívás None-t kap | PASS | `explore.rs:87,90,128,170,311` | sed-del frissítve |
| `tests.rs` hívás None-t kap | PASS | `tests.rs:384` | manuálisan frissítve |
| Összes meglévő teszt PASS (455 lib + 8 integration) | PASS | `455 passed; 0 failed` | Nincs regresszió |
