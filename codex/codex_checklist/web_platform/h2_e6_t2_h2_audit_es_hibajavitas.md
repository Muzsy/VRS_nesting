# H2-E6-T2 H2 audit es hibajavitas — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letrejon a `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md` fajl.
- [x] A dokumentum tartalmaz H2 completion matrixot.
- [x] A dokumentum tartalmaz pilot-tanulsag fejezetet.
- [x] A dokumentum tartalmaz blokkolo vs advisory bontast.
- [x] A dokumentum egyertelmu H3 entry gate iteletet ad.
- [x] A `dxf_nesting_platform_h2_reszletes.md`, a `dxf_nesting_platform_implementacios_backlog_task_tree.md` es a `web_platform_known_issues.md` minimalisan szinkronba kerul a H2 lezarasi allapottal.
- [x] A pilotbol vagy auditbol kijovo kritikus H2 hibak celzottan javitva vannak.
- [x] A task nem hoz letre uj H3 feature-t.
- [x] A task nem teszi kotelezove az optionalis H2-E5-T4 ag megvalositasat.
- [x] A task nem hoz letre uj domain migraciot.
- [x] Keszul regresszios smoke/harness a H2 kritikus mainline lancra.
- [x] A report DoD -> Evidence Matrix konkret fajl- es parancs-hivatkozasokkal kitoltott.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e6_t2_h2_audit_es_hibajavitas.md` PASS.
