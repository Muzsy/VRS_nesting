# Codex checklist - h1_e4_t2_run_create_api_service_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `api/services/run_creation.py` service
- [x] A service project owner guard utan hivja a H1-E4-T1 `build_run_snapshot_payload(...)` buildert
- [x] Sikeres create eseten `app.nesting_runs` rekord jon letre `status='queued'` allapottal
- [x] Sikeres create eseten `app.nesting_run_snapshots` rekord jon letre `status='ready'` allapottal
- [x] Sikeres create eseten `app.run_queue` rekord jon letre `queue_state='pending'` allapottal
- [x] A create flow explicit idempotencia + snapshot hash dedup kezelest ad
- [x] Snapshot hash unique versenyhelyzetre nem nyers DB hiba, hanem dedup valasz jon
- [x] A service hibas reszleges write eseten best-effort cleanupot vegez
- [x] A `api/routes/runs.py` create aga a service-re lett atkotve, list/log/artifact agak erintetlenek maradtak
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py`
- [x] `python3 -m py_compile api/services/run_creation.py api/routes/runs.py scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
