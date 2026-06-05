# Codex checklist — sgh_q28_t04_tracker_session_reuse

## Kötelező (workflow)

- [x] T01 + T02 + T03 PASS rögzítve
- [x] Canvas pontos: `canvases/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`

## Implementáció

- [x] `update_after_move` opcionális `live_session: Option<&mut CdeCandidateSession>` paraméterrel rendelkezik.
- [x] `Some` esetén backward-pair recompute a live session-t használja: egyetlen `session.query(shape_i)` az összes backward collision párt adja vissza.
- [x] `None` esetén viselkedés azonos a T04 előtti állapottal (per-pair mini-session build, backward compat).
- [x] `run_worker_pass` átadja `live_session.as_mut()`-ot `update_after_move`-nak (ha use_session, egyébként None).
- [x] `register_item_move` alias `None`-t ad át (backward compat).
- [x] `explore.rs` összes hívási helye `None`-t kap (5 db).
- [x] `tests.rs` hívása `None`-t kap.

## Minőségkapu

- [x] Összes lib unit test PASS (455 db).
- [x] Q26 integration teszt PASS (8 db).
- [ ] `./scripts/verify.sh` → PASS
- [ ] AUTO_VERIFY blokk frissült.

## Utóellenőrzés

- [x] `grep -n "live_session" rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs` — megtalálható.
- [x] `git diff --stat` — tracker.rs, worker.rs, explore.rs, tests.rs és codex fájlok érintettek.
