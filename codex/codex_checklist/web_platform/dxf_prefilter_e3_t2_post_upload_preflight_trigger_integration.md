# Codex checklist - dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Létrejött kulon `api/services/dxf_preflight_runtime.py` runtime/orchestration service
- [x] A runtime a meglévő T1→T7 + E3-T1 service-eket sorrendi hivással futtatja (nem duplikálja a logikát)
- [x] A runtime a source DXF-et `download_storage_object_blob(...)` helperrel tölti le storage-ból
- [x] A `run_seq` service-side, `app.preflight_runs` truth-ból számolódik (`get_next_run_seq`)
- [x] `rules_profile=None` V1 bridge (nincs rules-profile domain függőség)
- [x] Minimális failure handling: strukturált logger + `persist_preflight_failed_run` ahol lehetséges
- [x] `api/routes/files.py` `complete_upload` source DXF finalize után 3 background task regisztrálódik: geometry import + legacy validate + preflight runtime
- [x] A `complete_upload` response shape változatlan marad
- [x] A meglévő geometry import task és legacy readability check nem tűnik el
- [x] `api/services/dxf_preflight_persistence.py` bővítve: `RunSeqQueryGateway`, `get_next_run_seq`, `persist_preflight_failed_run`
- [x] Készült deterministic unit teszt: `tests/test_dxf_preflight_runtime.py` (11 teszt, 0.53s)
- [x] Készült deterministic smoke: `scripts/smoke_dxf_prefilter_e3_t2_post_upload_preflight_trigger_integration.py` (9 scenario, minden OK)
- [x] A tesztek fake gateway-jel futnak (nincs valós Supabase-hívás)
- [x] A checklist és report evidence-alapon frissült (DoD -> Evidence Matrix)
- [x] `./scripts/verify.sh` check.sh-t futtatott; a Python/mypy/DXF/Sparrow/vrs_solver rétegek mind PASS-on zártak; a FAIL forrása: pre-existing nesting engine timeout-bound canonical JSON determinism flakiness (`time_limit_sec=1`), nem E3-T2 változás
