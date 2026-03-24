# H2-E5-T4 Elso machine-specific adapter — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## Elofeltetel / STOP szabaly
- [ ] `TARGET_MACHINE_FAMILY` rogzitve (jelenlegi: TODO)
- [ ] `TARGET_ADAPTER_KEY` rogzitve (jelenlegi: TODO)
- [ ] `TARGET_OUTPUT_FORMAT` rogzitve (jelenlegi: TODO)

**BLOCKED:** a fenti harom mezo nincs kitoltve, az implementacio nem inditthato.

## DoD
- [ ] A task csak a H2-E5-T4 optionalis adapter-agban mozog, nem minositi at H2 blockerre a T4 hianyat.
- [ ] A task a `manufacturing_plan_json` artifactra epul, nem live selectionre vagy raw solver outputra.
- [ ] A konkret target adapter csalad explicit rogzitesre kerul (`TARGET_*` mezok kitoltve).
- [ ] A `config_jsonb` szukitett boundary-ja tenylegesen enforce-olva van.
- [ ] A task nem tervez uj lead-in/out rendszert, csak mappinget/fallbacket alkalmaz.
- [ ] A task legfeljebb a `run_artifacts` reteget boviti machine-ready artifacttal.
- [ ] Keszul task-specifikus smoke script.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` PASS.
