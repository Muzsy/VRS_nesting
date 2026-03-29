# H2-E5-T5 Masodik machine-specific adapter (QtPlasmaC) — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## Target freeze
- [x] `TARGET_MACHINE_FAMILY` rogzitve: `linuxcnc_qtplasmac` — `api/services/machine_specific_adapter.py:63`
- [x] `TARGET_ADAPTER_KEY` rogzitve: `linuxcnc_qtplasmac` — `api/services/machine_specific_adapter.py:63`
- [x] `TARGET_OUTPUT_FORMAT` rogzitve: `basic_manual_material_rs274ngc` — `api/services/machine_specific_adapter.py:64`
- [x] `TARGET_LEGACY_ARTIFACT_TYPE` rogzitve: `linuxcnc_qtplasmac_basic_manual_material` — `api/services/machine_specific_adapter.py:65`

## DoD
- [x] A task explicit targetet rogzit: `linuxcnc_qtplasmac` / `basic_manual_material_rs274ngc`. — `api/services/machine_specific_adapter.py:63-65`, smoke Test 16
- [x] A roadmapban megjelenik, hogy ez a H2 optionalis postprocess ag masodik adapter-taskja. — `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md` H2-E5-T5 blokk
- [x] A `machine_specific_adapter.py` a Hypertherm target regresszio nelkul tamogatja a QtPlasmaC targetet is. — smoke Test 4 (Hypertherm regression 12/12 PASS), T4 smoke 62/62 PASS
- [x] A primer bemenet tovabbra is a persisted `manufacturing_plan_json` artifact. — smoke Test 1, Test 7
- [x] A canonical geometry feloldas tovabbra is csak a persisted manufacturing truth tabla-lancbol tortenik. — `api/services/machine_specific_adapter.py:_build_geometry_cache` + `_resolve_contour_points`
- [x] A QtPlasmaC emitter per-sheet `machine_program` artifactokat general. — smoke Test 1 (1 sheet, 1 upload, 1 register)
- [x] A QtPlasmaC artifact metadata kitolti a target-specifikus legacy type-ot. — smoke Test 2
- [x] A storage path es filename deterministic. — smoke Test 3 (byte-level identical)
- [x] A task nem vezet be uj artifact kindot. — smoke Test 11, `_ARTIFACT_KIND = "machine_program"`
- [x] A task nem vezet be globalis SQL seed migrationt. — nincs migration fajl
- [x] A task nem ir manufacturing truth vagy postprocessor truth tablaba. — smoke Test 10
- [x] A task nem vezet be `M190`/`M66` material auto-change workflowt. — smoke Test 12
- [x] A task nem tervez uj lead-in/out rendszert. — adapter csak mapping/fallback
- [x] A smoke script ellenorzi a QtPlasmaC pozitiv utat, a Hypertherm regressziot, es a dispatch boundary-ket. — smoke 78/78 PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t5_masodik_machine_specific_adapter_qtplasmac.md` PASS.
