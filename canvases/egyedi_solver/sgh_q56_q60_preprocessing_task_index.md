# Q56–Q60 preprocessing task index

A VRS_nesting / Sparrow solver stratégiai preprocessing rétegének task-sorozata. A forrástervek:
`tmp/plans/q56_q60_preprocessing_tasks/`. A taskok **szándékosan** szét vannak bontva — ne olvaszd
őket egy nagy átírásba. A repo már több építőelemet tartalmaz; a cél ezek konszolidálása és
összekötése, nem eldobása.

## Architekturális alapelv

```text
worker cavity prepack v2
→ hole-free vrs_solver input contract
→ Rust/Sparrow PartAnalysis + OrientationCatalog + PairCompatibilityIndex + SheetFeasibilityHints
→ skeleton sheet-builder roles
→ exact CDE validation
→ incumbent/best-partial preservation
```

Kemény szabály: a preprocessing hinteket, candidate-eket, score-okat és diagnosztikát termel. A
CDE / exact prepared geometria marad a végső clearance és boundary igazság.

## Végrehajtási sorrend

```text
Q56A -> Q56B -> Q56B2 -> Q56C -> Q57A -> Q57B -> Q58A -> Q58B -> Q59 -> Q60
```

| # | Task | Slug | Csomag |
|---|------|------|--------|
| 1 | Q56A OrientationCatalog alap | `sgh_q56a_orientation_catalog_alap` | [canvas](sgh_q56a_orientation_catalog_alap.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q56a_orientation_catalog_alap/run.md) |
| 2 | Q56B PartAnalysis / ShapeProfileV2 | `sgh_q56b_part_analysis_shape_profile_v2` | [canvas](sgh_q56b_part_analysis_shape_profile_v2.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2/run.md) |
| 3 | Q56B2 CavityPrepackBridgeHints | `sgh_q56b2_cavity_prepack_bridge_hints` | [canvas](sgh_q56b2_cavity_prepack_bridge_hints.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints/run.md) |
| 4 | Q56C SheetEdgePlacementCatalog | `sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates` | [canvas](sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates/run.md) |
| 5 | Q57A PairCompatibilityIndex critical-only | `sgh_q57a_pair_compatibility_index_critical_only` | [canvas](sgh_q57a_pair_compatibility_index_critical_only.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only/run.md) |
| 6 | Q57B Pair candidates → Interlock role | `sgh_q57b_pair_candidates_to_interlock_role` | [canvas](sgh_q57b_pair_candidates_to_interlock_role.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role/run.md) |
| 7 | Q58A SheetFeasibilityHints | `sgh_q58a_sheet_feasibility_hints` | [canvas](sgh_q58a_sheet_feasibility_hints.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q58a_sheet_feasibility_hints/run.md) |
| 8 | Q58B SheetFeasibilityHints → BPP/sheet-builder | `sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder` | [canvas](sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder/run.md) |
| 9 | Q59 BandInsert true-extreme slot-edge | `sgh_q59_band_insert_true_extreme_slot_edge_placement` | [canvas](sgh_q59_band_insert_true_extreme_slot_edge_placement.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement/run.md) |
| 10 | Q60 Critical triple / simultaneous admission | `sgh_q60_critical_triple_simultaneous_admission` | [canvas](sgh_q60_critical_triple_simultaneous_admission.md) · [runner](../../codex/prompts/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission/run.md) |

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

## Globális non-negotiables (minden taskra)

```text
- moduláris implementáció; az exact geometria nem cserélhető bbox döntésre
- bbox / coarse grid / derived frame csak prefilter / ranking proxy / diagnosztika, soha nem collision truth
- spacing / margin / kerf / rotation freedom nem csökkenthető a pass kedvéért
- nincs part-id-specifikus hack (pl. Lv8_11612_6db)
- continuous rotation megőrzése continuous partoknál
- a Q55B one-part true-extreme sheet-edge proof nem regresszálhat
- minden új stratégiai döntés magyarázható artifact JSON-ban
- elutasított candidate-nél rögzítsd az elutasítás okát
- minden sikeres placement visszavezethető candidate source / role / rotation source / exact validation eredményre
- ha a feltevés rossznak bizonyul, jelentsd a bizonyítékot és igazítsd az implementációt — nincs hamis pass
```

## Várt végállapot Q60 után

```text
PartAnalysis / ShapeProfileV2
+ OrientationCatalog
+ CavityPrepackBridgeHints
+ SheetEdgePlacementCatalog
+ PairCompatibilityIndex
+ SheetFeasibilityHints
+ true-extreme Anchor / Interlock / BandInsert placement
+ critical pair/triple simultaneous admission support
+ best-partial preservation
```
