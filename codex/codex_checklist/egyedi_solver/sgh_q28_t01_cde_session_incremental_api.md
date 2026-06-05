# Codex checklist — sgh_q28_t01_cde_session_incremental_api

## Kötelező (workflow)

- [x] Elolvastam: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- [x] A canvas pontos, csak valós fájlokra hivatkozik: `canvases/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md`
- [x] A goal YAML a szabvány sémát használja: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q28_t01_cde_session_incremental_api.yaml`
- [x] A baseline teszt-szám rögzített a reportban (454 lib + 8 integration).

## Implementáció

- [x] `CdeCandidateSession::build_all_items` létezik és `pub(crate)`.
- [x] `CdeCandidateSession::deregister_item` frissíti a `holes` vektort és a CDEngine quadtree-t.
- [x] `CdeCandidateSession::reregister_item` appendi a `holes`-t és regisztrál a CDEngine-be.
- [x] `lookup_hole_slot` private helper megvan.
- [x] `build_with_policy` és `build` érintetlen (nem módosultak).
- [x] `run_worker_pass`, `native_search_placement`, `tracker.rs` érintetlen.

## Minőségkapu és bizonyítékok

- [x] `cde_session_incremental_eq_full_rebuild` unit test PASS.
- [x] Összes lib unit test PASS (≥454).
- [x] Q26 integration teszt PASS (8 db).
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t01_cde_session_incremental_api.md` → PASS
- [x] A report AUTO_VERIFY blokkja frissült és a log létrejött.
- [x] A reportban a DoD → Evidence Matrix minden pontja kitöltve.

## Utóellenőrzés (gyors)

- [x] `grep -n "fn build_all_items\|fn deregister_item\|fn reregister_item" rust/vrs_solver/src/optimizer/cde_adapter.rs` — mind a három megvan.
- [x] `git diff --stat` csak `cde_adapter.rs` és codex fájlokat mutat.
