# H3-E1-T2 Scoring profile modellek — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letezik kulon `app.scoring_profiles` persisted truth reteg.
- [x] Letezik kulon `app.scoring_profile_versions` persisted truth reteg.
- [x] A scoring profile domain owner-scoped es verziozott.
- [x] A version rekordok legalabb `weights_jsonb`, `tie_breaker_jsonb`, `threshold_jsonb`, `is_active` mezoket hordoznak.
- [x] Keszul dedikalt scoring profile service reteg.
- [x] Keszul dedikalt scoring profile API route.
- [x] A route be van kotve az `api/main.py`-ba.
- [x] A task nem vezet be `project_scoring_selection` persisted selectiont.
- [x] A task nem vezet be `run_evaluations`, ranking vagy comparison scope-ot.
- [x] A task nem ir vissza H2 manufacturing truth tablaba.
- [x] Keszul task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t2_scoring_profile_modellek.md` PASS.
