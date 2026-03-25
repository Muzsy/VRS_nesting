# H2-E5-T4 Elso machine-specific adapter — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## Target freeze
- [x] `TARGET_MACHINE_FAMILY` rogzitve: `hypertherm_edge_connect`
- [x] `TARGET_ADAPTER_KEY` rogzitve: `hypertherm_edge_connect`
- [x] `TARGET_OUTPUT_FORMAT` rogzitve: `basic_plasma_eia_rs274d`
- [x] `TARGET_LEGACY_ARTIFACT_TYPE` rogzitve: `hypertherm_edge_connect_basic_plasma_eia`

## DoD
- [x] A task explicit targetet rogzit: `hypertherm_edge_connect` / `basic_plasma_eia_rs274d`. — `api/services/machine_specific_adapter.py:53-55`
- [x] A task megorzi, hogy a H2-E5-T4 optionalis ag, nem H2 blocker. — canvas + report "Miert igy?" szekciok
- [x] A service primer bemenete a persisted `manufacturing_plan_json` artifact. — `api/services/machine_specific_adapter.py:122-131` (`_load_export_artifact` + `_download_export_payload`)
- [x] A service legfeljebb geometry feloldasra olvas `run_manufacturing_contours` + `geometry_derivatives` truthot, es nem kerul vissza live selection vilagba. — `api/services/machine_specific_adapter.py:479-540` (`_build_geometry_cache`)
- [x] A `config_jsonb` szukitett boundary-ja tenylegesen enforce-olva van. — `api/services/machine_specific_adapter.py:61-82` (`_ALLOWED_CONFIG_BLOCKS`, `_REQUIRED_CONFIG_BLOCKS`) + `api/services/machine_specific_adapter.py:766-773` (`_validate_config_boundary`)
- [x] A task nem tervez uj lead-in/out rendszert. — adapter csak mapping/fallback: `api/services/machine_specific_adapter.py:323-331`
- [x] A task nem vezet be uj artifact kindot; a meglevo `machine_program` kindot hasznalja custom `legacy_artifact_type` metadata-val. — `api/services/machine_specific_adapter.py:56` (`_ARTIFACT_KIND = "machine_program"`) + smoke Test 2
- [x] A task nem seedel globalis postprocessor profilt migrationben. — nincs SQL migration fajl; smoke in-memory fixture-oket hasznal
- [x] Keszul dedikalt `api/services/machine_specific_adapter.py`. — 842 sor, `generate_machine_programs_for_run` entry point
- [x] Keszul task-specifikus smoke script. — `scripts/smoke_h2_e5_t4_elso_machine_specific_adapter.py`, 62/62 PASS
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t4_elso_machine_specific_adapter.md` PASS.
