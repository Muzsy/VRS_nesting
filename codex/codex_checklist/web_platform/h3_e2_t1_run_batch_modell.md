# H3-E2-T1 Run batch modell — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letrejott a `run_batches` truth reteg.
- [x] Letrejott a `run_batch_items` truth reteg.
- [x] A batch CRUD owner/project-scope validacioval mukodik.
- [x] A batch item attach/list/remove contract mukodik.
- [x] A batch item opcionálisan strategy/scoring kontextust tud hordozni.
- [x] A task nem hoz letre uj queued run-okat.
- [x] A task nem csuszik at evaluation / ranking / comparison scope-ba.
- [x] Keszult dedikalt batch service es route.
- [x] A route be van kotve az `api/main.py`-ba.
- [x] Keszult task-specifikus smoke script.
- [x] Checklist es report evidence-alapon frissitve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t1_run_batch_modell.md` PASS.
