# H3-E1-T3 Project-level selectionok — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letezik kulon `app.project_run_strategy_selection` persisted truth reteg.
- [x] Letezik kulon `app.project_scoring_selection` persisted truth reteg.
- [x] Egy projektnek legfeljebb egy aktiv strategy selectionje van.
- [x] Egy projektnek legfeljebb egy aktiv scoring selectionje van.
- [x] A selection project owner scope-ban hozhato letre, modosithato, olvashato es torolheto.
- [x] A selection csak a userhez tartozo ervenyes strategy/scoring profile versionre mutathat.
- [x] A task nem nyitja ujra a strategy vagy scoring profile CRUD scope-ot.
- [x] A task nem nyul a snapshot / batch / evaluation / ranking retegekhez.
- [x] Keszul minimalis GET / PUT / DELETE backend contract mindket selectionhoz.
- [x] Keszul task-specifikus smoke script a sikeres es hibas agakra.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md` PASS.
