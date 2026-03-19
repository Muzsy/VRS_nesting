# Codex checklist - h1_e4_t3_queue_lease_mechanika_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `worker/queue_lease.py` helper modul
- [x] A helper a H0 canonical queue truth-ra epul (`app.run_queue`, `app.nesting_runs`)
- [x] A claim logika atomikus (`FOR UPDATE SKIP LOCKED`) es duplafutas ellen ved
- [x] Sikeres claim eseten `queue_state='leased'` + canonical lease mezok toltesre kerulnek
- [x] A `attempt_no` + `attempt_status='leased'` frissites claimnel megtortenik
- [x] A heartbeat tokenhez kotott (`run_id` + `leased_by` + `lease_token`) es TTL-t hosszabbit
- [x] Van minimalis expired-lease reclaim szemantika (`lease_expires_at <= now()`)
- [x] A `worker/main.py` claim/heartbeat a helperre lett realignalva
- [x] Lost-lease helyzet kontrollaltan kezelt (heartbeat miss -> process stop + explicit hiba)
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py`
- [x] `python3 -m py_compile worker/queue_lease.py worker/main.py scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e4_t3_queue_lease_mechanika_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t3_queue_lease_mechanika_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
