# Codex checklist — sgh_q28_t03_worker_single_session_lifecycle

## Kötelező (workflow)

- [x] T01 + T02 PASS rögzítve
- [x] Canvas pontos: `canvases/egyedi_solver/sgh_q28_t03_worker_single_session_lifecycle.md`
- [x] YAML séma szerint: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t03_worker_single_session_lifecycle.yaml`

## Implementáció

- [x] `run_worker_pass` pass elején egyszer épít session-t (`build_all_items`).
- [x] `native_search_placement`-nek `Some(&mut session)` megy single-sheet esetén.
- [x] Elfogadás után: reregister az ÚJ shape-pel (update_after_move után).
- [x] Visszautasítás esetén (acceptance criterion): reregister az EREDETI shape-pel (restore_keep_weights után).
- [x] Visszautasítás esetén (search returns None): reregister az EREDETI shape-pel.
- [x] Degenerate bbox (None session) esetén fallback per-item build fut.
- [x] `debug_assert` session hazard_count konzisztencia a ciklus végén megvan.
- [x] Kritikus bugfix: deregister ELŐRE mozgatva `prepare_base_shape_native` és deadline check elé (invariant: ha live_session Some, a target mindig deregistered állapotban marad visszatéréskor).

## Minőségkapu

- [x] Összes lib unit test PASS (455 db).
- [x] Q26 integration teszt PASS (8 db).
- [ ] `./scripts/verify.sh` → PASS
- [ ] AUTO_VERIFY blokk frissült.

## Utóellenőrzés

- [x] `grep -n "build_all_items\|live_session" rust/vrs_solver/src/optimizer/sparrow/worker.rs` — mindkettő megvan.
- [x] `git diff --stat` — worker.rs, search.rs és codex fájlok érintettek.
