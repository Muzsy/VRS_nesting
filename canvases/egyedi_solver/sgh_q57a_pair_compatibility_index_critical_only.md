# Q57A — PairCompatibilityIndex critical-only

## Goal / Funkció

Építsd meg az első production pair-kompatibilitási indexet **csak kritikus** partokra. Ez a task még
nem változtat Interlock placementet: nagy értékű pair candidate-eket számol és riportol, amelyeket a
Q57B köt majd a `SkeletonRole::Interlock` szerephez.

## Context / Háttér

A repo ma lokális szomszéd-feature illesztést tud, de nincs globális, előre számolt pair index. A
`rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs` jelenleg lényegében stub — ez a
természetes hely a pair munkának (replace/extend/supersede). Cél: segíteni az olyan eseteket, ahol a
pair/triple interlock a valódi bottleneck (pl. nagy kritikus LV8 partok).

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q57A_PairCompatibilityIndex_critical_only.md`

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs` — jelenlegi stub (12 sor),
  `PairMatrix`.
- `rust/vrs_solver/src/optimizer/sparrow/quantify/mod.rs` — `pair_matrix`, `overlap_proxy`, `tracker`.
- `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs` — `ContourFeatureSet`.
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — `criticality_tier()`,
  `is_large_anchor`, `is_high_interlock_potential`.
- `rust/vrs_solver/src/optimizer/sparrow/model.rs` — `SPInstance`, `spacing_collision_base_shape`.
- `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` (Q56A),
  `rust/vrs_solver/src/optimizer/sparrow/part_analysis.rs` (Q56B) — ha léteznek, reuse.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs
rust/vrs_solver/src/optimizer/sparrow/quantify/mod.rs
rust/vrs_solver/src/optimizer/sparrow/contour_features.rs
rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/io.rs
```

## Scope

- `PairCompatibilityIndex` + `PairCompatibilityCandidate` (vagy ekvivalens) a pair_matrix.rs helyén
  vagy új modulban; a stub explicit lecserélve/kiterjesztve.
- Két-stage filterezés (olcsó prefilter + bounded geometriai validáció top-K párra).
- JSON diagnosztikai artifact.
- Fókuszált unit tesztek.

## Out of scope

- Interlock placement megváltoztatása (Q57B).
- All-pairs exact geometria minden partra.
- Pair candidate-ek kötelező superpartként kezelése.

## Required implementation

Kritikus-only fókusz: `critical-critical`, same part type repeated family,
`large_anchor + high_interlock_potential`, `large_anchor + medium_structural` csak ha olcsó filterek
átengedik. `PairCompatibilityCandidate` mezők: `part_a_id`, `part_b_id`, instance class-ok,
`rotation_a_deg`, `rotation_b_deg`, `relative_dx`, `relative_dy`, `candidate_source`,
`compactness_gain`, `bbox_area_reduction`, `interlock_depth_score`, `spacing_clear`, `cde_clear`,
`score`, diagnostics. Candidate source-ok: `same_part_flip`, `same_family_flip`,
`dominant_edge_parallel`, `protrusion_to_concavity`, `extreme_to_edge`, `orientation_catalog_pair`.

Reuse: PartAnalysis/ShapeProfileV2, OrientationCatalog, ContourFeatureSet,
`spacing_collision_base_shape`, feature candidate logika — kontúrfeature extrakció **nem** duplikálva.

Két-stage:
- Stage 1 (olcsó): criticality_tier, is_large_anchor, is_high_interlock_potential, family key,
  quantity, area/aspect kompatibilitás, dominant edge angle kompatibilitás, convexity/fill.
- Stage 2 (bounded, top-K): OrientationCatalog rotációk, feature-eredetű relatív placementek,
  spacing-expanded CDE clearance, compactness / composite bbox scoring.

Bounded/konfigurálható top-K. Javasolt env: `VRS_PAIR_INDEX=1`,
`VRS_PAIR_INDEX_MAX_PART_TYPES=64`, `VRS_PAIR_INDEX_TOPK_PER_PART=12`,
`VRS_PAIR_INDEX_MAX_CANDIDATES=512`.

Same-part kritikus pár: ismételt kritikus típusoknál explicit same-part flip candidate (pl.
`A@~90 + A@~270`). **Ne** hardcode-old a part nevet; same part type + criticality + OrientationCatalog.

Validáció: minden candidate spacing-expanded alakok ellen (`cde_clear`, separation/clear). Invalid
candidate csak egyértelmű jelöléssel; a production top-lista a valid/clear candidate-eket priorizálja.

## Required diagnostics

```text
artifacts/benchmarks/sgh_q57a/pair_compatibility_index.json
```

Tartalom: `unique_part_count`, `critical_part_type_count`, `candidate_count_total`,
`candidate_count_valid`, `candidate_count_by_source`, `top_pairs[]` (part id-k, rotations, relative
transform, source, cde_clear, spacing_clear, compactness_gain, interlock_depth_score, score,
rejection_reason ha invalid). Ha van: `lv8_critical_same_part_pair_candidates[]`.

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_pair_compatibility_index.rs`. Ellenőrzések:

1. A pair index determinisztikusan épül.
2. Critical-only filter kizárja a tiny-filler-only párokat default szerint.
3. Ismételt kritikus típus same-part pair candidate-et ad.
4. A pair candidate-eknek van rotation source metaadata.
5. A valid candidate-ek CDE/spacing-checked.
6. A PairMatrix stub lecserélve/kiterjesztve/egyértelműen superseded.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml pair_compatibility_index
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
```

## Acceptance criteria

```text
- PairCompatibilityIndex létezik.
- Bounded és default szerint critical-only.
- PartAnalysis/OrientationCatalog/ContourFeatureSet alapú (nem független hack).
- Valid pair candidate-eket ad relatív transzformmal és score-ral.
- Diagnosztikai artifactot ad.
- Még nem kényszerít solver placement döntést.
```

## Hard restrictions

```text
- nincs vak all-pairs számítás bounds nélkül
- nincs part-ID / LV8-specifikus hack
- nincs CDE/spacing nélküli pair suggestion tárolás
- pair candidate nem kötelező superpart
- Interlock viselkedés nem változik Q57B előtt
- pair_matrix.rs nem maradhat értelmetlen stub magyarázat nélkül
- nincs NFP, nincs bbox collision shortcut, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- Az egész index env-gated (`VRS_PAIR_INDEX=0` default), így no-regression: kikapcsolva a meglévő
  viselkedés byte-azonos.
- Ha a stage-2 validáció túl drága, csökkentsd a top-K-t; ha instabil, jelöld invalid/unknown a
  candidate-et és priorizáld a tisztán validakat.

## Deliverables

```text
canvases/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57a_pair_compatibility_index_critical_only.yaml
codex/prompts/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only/run.md
codex/codex_checklist/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.verify.log
```
