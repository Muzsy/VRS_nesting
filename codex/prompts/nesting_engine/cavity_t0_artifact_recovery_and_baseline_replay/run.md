# DXF Nesting Platform Codex Task - Cavity T0 artifact recovery es baseline replay
TASK_SLUG: cavity_t0_artifact_recovery_and_baseline_replay

## Szerep
Senior coding agent vagy a valos VRS_nesting repoban. A feladat artifact URL
recovery es baseline evidence, nem cavity feature implementacio.

## Cel
Javitsd vagy bizonyitsd a `solver_input` es `engine_meta` artifact download URL
utvonalat, majd hozz letre legacy baseline replay evidence-et, ha a production
artifact elerheto.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `tmp/plans/cavity_first_composite_nesting_fejlesztesi_terv.md`
- `codex/reports/nesting_engine/otszog_bodypad_runtime_root_cause_20260428.md`
- `canvases/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t0_artifact_recovery_and_baseline_replay.yaml`

## Repo inspection kovetelmeny
Nezz ra konkretan:
- `api/routes/runs.py`
- `api/supabase_client.py`
- `worker/main.py`
- `scripts/verify.sh`
- `scripts/check.sh`
- `tmp/runs/**/downloaded_artifact_urls.json`, ha letezik
- `tmp/runs/**/run_artifacts.json`, ha letezik
- `tmp/repro_f683e6f7/solver_input_snapshot.json`, ha letezik

## Engedelyezett modositas
Csak a YAML `outputs` listajaban szereplo fajlok. Ha mas fajl kell, elobb
frissitsd a YAML-t. Ne modosits Rust engine fallbacket es ne implementalj
cavity prepack logikat.

## Szigoru tiltasok
- Nincs OTSZOG_BODYPAD/NEGYZET/MACSKANYELV vagy filename hardcode.
- Nincs timeout/work_budget-only fix.
- Nincs warning suppression.
- Nincs globalis hole deletion.
- Titok/token nem kerulhet repoba.

## Elvart parancsok
- `python3 -m pytest -q tests/test_run_artifact_url_recovery.py` ha a teszt elkeszult.
- `python3 scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py`
- Ha production snapshot letoltheto, legacy Rust replay `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`

## Stop conditions
Allj meg es FAIL/PASS_WITH_NOTES reportot irj, ha:
- artifact URL hiba credential/storage policy miatt nem javithato ebben a repoban;
- production snapshot nem letoltheto a javitas utan sem;
- a javitashoz DB migration vagy schema dontes kell, ami nincs a scope-ban.

## Report nyelve es formatuma
A vegso task report magyarul keszuljon `docs/codex/report_standard.md` szerint.
Legyen DoD -> Evidence matrix, parancsok exit code-dal, AUTO_VERIFY blokk, es
kulon baseline replay vagy blokkolt replay szekcio.
