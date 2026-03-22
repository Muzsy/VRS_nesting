# H2-E5-T2 Postprocessor profile/version domain aktiválása — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letezik `app.postprocessor_profiles` owner-scoped truth-reteg.
- [x] Letezik `app.postprocessor_profile_versions` owner-scoped, verziozott truth-reteg.
- [x] Keszul owner-scoped CRUD service + route a postprocessor domainhez.
- [x] A `manufacturing_profile_versions` tud nullable `active_postprocessor_profile_version_id` hivatkozast tarolni.
- [x] A manufacturing -> postprocessor referencia owner-konzisztens.
- [x] A `project_manufacturing_selection` read-path vissza tudja adni a kapcsolt postprocessor refet.
- [x] A `run_snapshot_builder` valos postprocess selectiont snapshotol, ha van aktiv ref.
- [x] `includes_postprocess` csak aktiv ref eseten lesz true.
- [x] A task nem hoz letre export / adapter / machine-ready scope-ot.
- [x] A task nem vezet be nem letezo catalog-FK vilagot.
- [x] Keszul task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md` PASS.
