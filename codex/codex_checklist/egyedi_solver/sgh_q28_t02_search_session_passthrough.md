# Codex checklist — sgh_q28_t02_search_session_passthrough

## Kötelező (workflow)

- [x] Elolvastam: `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- [x] T01 PASS rögzítve (build_all_items, deregister_item, reregister_item létezik)
- [x] Canvas pontos: `canvases/egyedi_solver/sgh_q28_t02_search_session_passthrough.md`

## Implementáció

- [x] `native_search_placement` új `live_session: Option<&mut CdeCandidateSession>` paramétere megvan.
- [x] `None` esetén a viselkedés byte-for-byte azonos a T02 előtti állapottal.
- [x] `optimizer.rs` probe hívás `None`-t ad át, fordítható.
- [x] `worker.rs` hívási hely `None`-t ad át egyelőre (T03-ban fog Some-ra változni).
- [x] `separator.rs` hívási hely `None`-t ad át.
- [x] `build_sheet_session` fallback érintetlen.

## Minőségkapu

- [x] Összes lib unit test PASS (455 db).
- [x] Q26 integration teszt PASS (8 db).
- [ ] `./scripts/verify.sh` → PASS
- [ ] AUTO_VERIFY blokk frissült, log létrejött.

## Utóellenőrzés

- [x] `grep -n "live_session" rust/vrs_solver/src/optimizer/sparrow/sample/search.rs` — megtalálható.
- [x] `git diff --stat` csak search.rs, optimizer.rs, worker.rs, separator.rs és codex fájlokat mutat.
