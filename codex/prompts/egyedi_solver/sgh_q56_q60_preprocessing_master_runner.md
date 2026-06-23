# Master runner — Q56–Q60 preprocessing task sorozat

Ez a master runner a Q56–Q60 stratégiai preprocessing csomagok egységes belépési pontja. Egyesével,
sorrendben futtasd a taskokat; mindegyiknek saját canvas + goal YAML + runner + checklist + report
csomagja van.

## Kötelező olvasnivaló (minden task előtt)

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/prompts/task_runner_prompt_template.md
canvases/egyedi_solver/sgh_q56_q60_preprocessing_task_index.md
tmp/plans/q56_q60_preprocessing_tasks/00_README_TASK_SEQUENCE.md
```

## Végrehajtási sorrend és runnerek

```text
Q56A  -> codex/prompts/egyedi_solver/sgh_q56a_orientation_catalog_alap/run.md
Q56B  -> codex/prompts/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2/run.md
Q56B2 -> codex/prompts/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints/run.md
Q56C  -> codex/prompts/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates/run.md
Q57A  -> codex/prompts/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only/run.md
Q57B  -> codex/prompts/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role/run.md
Q58A  -> codex/prompts/egyedi_solver/sgh_q58a_sheet_feasibility_hints/run.md
Q58B  -> codex/prompts/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder/run.md
Q59   -> codex/prompts/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement/run.md
Q60   -> codex/prompts/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission/run.md
```

## Dependency graph

```text
Q56A OrientationCatalog
  -> Q56B PartAnalysis / ShapeProfileV2
  -> Q56C SheetEdgePlacementCatalog

Q56B2 CavityPrepackBridgeHints
  -> Q58A SheetFeasibilityHints

Q56A + Q56B
  -> Q57A PairCompatibilityIndex critical-only

Q57A + sheet_skeleton
  -> Q57B Pair candidates to Interlock role

Q56A + Q56B + Q56B2
  -> Q58A SheetFeasibilityHints

Q58A
  -> Q58B BPP/sheet-builder integration

Q56C + Q58B + existing BandInsert
  -> Q59 true-extreme BandInsert

Q57B + Q58B + Q59
  -> Q60 critical triple / simultaneous admission
```

## Egységes kemény szabályok (minden task)

```text
- Csak az adott task YAML step `outputs` listájában szereplő fájlt módosítsd.
- nincs NFP-visszahozás
- nincs bbox collision shortcut
- nincs part-id hack
- nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
- a Q55B one-part true-extreme sheet-edge proof nem regresszálhat
```

## Minden task lezárása

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/<TASK_SLUG>.md
```

A `verify.sh` után frissítsd a task checklistjét és reportját (Report Standard v2, DoD→Evidence
path+line). PASS csak zöld verify + teljesült DoD esetén. Ha egy task azt találja, hogy a feltevés
rossz, jelentse a bizonyítékot és igazítsa az implementációt — nincs hamis pass.
