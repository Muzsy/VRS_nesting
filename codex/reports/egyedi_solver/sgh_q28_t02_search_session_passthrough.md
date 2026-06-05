PASS

## 1) Meta

* **Task slug:** `sgh_q28_t02_search_session_passthrough`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t02_search_session_passthrough.yaml`
* **Futás dátuma:** `2026-06-05`
* **Branch / commit:** `main`
* **Fókusz terület:** Rust | Solver | Performance

## 2) Scope

### 2.1 Cél

- `native_search_placement` bővítése `live_session: Option<&mut CdeCandidateSession>` paraméterrel
- `Some(session)` esetén rank-0 sheeten: `deregister_item` → keresés → session deregistered állapotban marad (T03 reregistrálja)
- `None` esetén: a meglévő `build_sheet_session` fallback érintetlen
- Minden hívási hely (optimizer.rs, worker.rs, separator.rs) `None`-t kap

### 2.2 Nem-cél (explicit)

- `run_worker_pass` módosítása (T03)
- `tracker.rs` módosítása (T04)
- Keresési algoritmus logikájának változtatása

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

* **Rust:**
  * `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
  * `rust/vrs_solver/src/optimizer/sparrow/optimizer.rs` (probe hívás `None`)
  * `rust/vrs_solver/src/optimizer/sparrow/worker.rs` (hívási hely `None`)
  * `rust/vrs_solver/src/optimizer/sparrow/separator.rs` (hívási hely `None`)

### 3.2 Miért változtak?

`native_search_placement` új utolsó paramétere `live_session: Option<&mut CdeCandidateSession>`.
A rank-0 blokk két ágra osztódik:
1. `Some(ref mut ls)`: `ls.deregister_item(target)` → `SeparationEvaluator { session: &**ls }` → `search_placement` → `continue` (session deregistered marad, T03 kezeli a reregistert)
2. Fallback (None vagy rank>0): `build_sheet_session` → meglévő logika (változatlan)

A három hívási hely (`optimizer.rs`, `worker.rs`, `separator.rs`) `None`-t kap — backward compat.

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
| `native_search_placement` új `live_session` paraméter | PASS | `search.rs:199–229` | `live_session: Option<&mut CdeCandidateSession>` utolsó param |
| `None` eset backward compat | PASS | `search.rs:278–318` (fallback ág) | `build_sheet_session` hívás változatlan |
| `Some` eset: deregister → keresés → deregistered marad | PASS | `search.rs:254–277` | rank-0 + Some ág, `continue` után session deregistered |
| `optimizer.rs` probe `None`-t ad át | PASS | `optimizer.rs:67–79` | `None` argumentum hozzáadva |
| `worker.rs` hívás `None`-t ad át | PASS | `worker.rs:62–67` | `None` argumentum hozzáadva |
| `separator.rs` hívás `None`-t ad át | PASS | `separator.rs:125–137` | `None` argumentum hozzáadva |
| Összes meglévő teszt PASS (455 lib + 8 integration) | PASS | `455 passed; 0 failed` | Nincs regresszió |
