# H2-E5-T3 Machine-neutral exporter — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letezik `manufacturing_plan_json` artifact kind a bridge-frissitessel egyutt.
- [x] Keszul dedikalt `api/services/machine_neutral_exporter.py` service.
- [x] A service owner-scoped runra a persisted H2 truth + snapshot alapjan gepfuggetlen export payloadot tud eloallitani.
- [x] Az export payload deterministic es canonical.
- [x] Az artifact `app.run_artifacts` ala regisztralodik `manufacturing_plan_json` tipussal.
- [x] Aktiv postprocessor selection eseten a metadata bekerul, de nincs machine-specific emit.
- [x] A task nem hoz letre `machine_ready_bundle` vagy mas machine-specific scope-ot.
- [x] A task nem olvas live project selectiont, es nem ir vissza korabbi truth tablaba.
- [x] Keszul task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t3_machine_neutral_exporter.md` PASS.
