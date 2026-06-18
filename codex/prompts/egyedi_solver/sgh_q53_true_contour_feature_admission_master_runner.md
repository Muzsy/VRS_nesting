# SGH-Q53 master runner — True contour-feature critical admission

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- Q47–Q52 canvasok és reportok, különösen:
  - `canvases/egyedi_solver/sgh_q47_shape_profile_priority_layer.md`
  - `canvases/egyedi_solver/sgh_q51_critical_aware_sheet_builder.md`
  - `canvases/egyedi_solver/sgh_q52_density_biased_admission.md`

Majd a Q53 taskokat sorrendben hajtsd végre:

1. `codex/prompts/egyedi_solver/sgh_q53a_contour_feature_extraction/run.md`
2. `codex/prompts/egyedi_solver/sgh_q53b_feature_candidate_generator/run.md`
3. `codex/prompts/egyedi_solver/sgh_q53c_continuous_feature_refine/run.md`
4. `codex/prompts/egyedi_solver/sgh_q53d_critical_admission_integration/run.md`
5. `codex/prompts/egyedi_solver/sgh_q53e_lv8_feature_admission_proof/run.md`

## Stop conditions

Állj meg és írj BLOCKED reportot, ha:

- az előző Q53 task kimenete hiányzik;
- a szükséges valós repo fájl/funkció nem létezik és nincs egyértelmű alternatíva;
- a megoldás csak bbox-corner seedet tudna primaryként használni;
- continuous rotationt diszkrét listára kellene snappelni;
- a final CDE validation gyengülne.

## Globális hard rules

- Csak a task YAML outputs listájában szereplő fájlokat módosíthatod.
- Nem hozhatsz vissza NFP-t.
- Nem adhatsz bbox collision shortcutot.
- Cavity/hole nincs a fő solverben.
- Nincs hardcoded LV8 part-id viselkedés.
- Minden task végén `./scripts/verify.sh --report ...` kötelező.
