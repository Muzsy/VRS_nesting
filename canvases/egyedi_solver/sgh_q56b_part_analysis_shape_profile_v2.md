# Q56B — PartAnalysis / ShapeProfileV2

## Goal / Funkció

Hozz létre egy koherens, part-szintű analízis réteget a meglévő `PartShapeProfile` és
`ContourFeatureSet` fölé. Ez a réteg (`PartAnalysis` / `ShapeProfileV2`) táplálja a prioritizálást,
az orientáció-választást, a pair-kompatibilitást, a sheet-feasibility-t és a role-hozzárendelést. A
meglévő profilozást **nem dobja el**, hanem teljesebbé fejleszti.

## Context / Háttér

A `PartShapeProfile` ma már sok hasznos jellemzőt tartalmaz (`true_area`, `bbox_area`,
`convex_hull_area`, `aspect_ratio`, `fill_ratio`, `convexity_ratio`, `slenderness`,
`sheet_area_ratio`, `is_large_anchor`, `is_high_interlock_potential`, `is_tiny_filler`,
`priority_score`, `search_budget_multiplier`, `filler_defer_score`, …), de a következő solver
stádiumokhoz még túl durva. A Q56B döntéstámogató jeleket, soft shape tag-eket, fit-difficulty
pontszámot és olcsó family/near-duplicate kulcsot ad — mindezt CDE megkerülése nélkül.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q56B_PartAnalysis_ShapeProfileV2.md`
- A shape tag-ek és pontszámok **soft** döntéstámogatás; nem exact fit/collision proof.

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — `PartShapeProfile`, tier/score mezők.
- `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs` — `ContourFeatureSet`,
  `ContourFeatureSummary`.
- `rust/vrs_solver/src/optimizer/sparrow/model.rs` — `SPInstance`, `from_solver_input(...)`,
  `shape_profile`.
- `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` — Q56A `OrientationCatalog`
  (ha már létezik; egyébként tiszta slot marad).

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
rust/vrs_solver/src/optimizer/sparrow/contour_features.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/io.rs
```

Megjegyzés: `rust/vrs_solver/src/optimizer/sparrow/part_analysis.rs` még **nem létezik** — ez a task
deliverable-je (új fájl). `orientation_catalog.rs` az Q56A-ból jön; ha Q56B előbb fut, hagyj tiszta
slotot a bekötéshez.

## Scope

- Új `part_analysis.rs` modul: `PartAnalysis` (vagy `PartShapeProfileV2`), `ShapeTag`,
  `FitDifficultySignals`, `PartAnalysisDiagnostics`.
- `PartAnalysis` újrahasználja `Rc<PartShapeProfile>`-t és `ContourFeatureSummary`-t (nem duplikál).
- Bekötés: `SPInstance` kap `Rc<PartAnalysis>`-t (vagy explicit, tesztelhető part-analysis map).
- JSON artifact a valós LV8 munkacsomagra vagy reprezentatív részhalmazra.
- Fókuszált unit tesztek.

## Out of scope

- Final placement viselkedés agresszív megváltoztatása (Q56B analízis-réteg task).
- Cavity prepack implementáció Rustban (Q56B2; itt csak hole-free flag rögzítés).
- PairCompatibilityIndex (Q57A) és SheetFeasibilityHints (Q58A) számítása.

## Required implementation

- Soft jelek (minimum): `fit_difficulty_score`, `orientation_sensitivity_score`,
  `symmetry_score`/`symmetry_class`, `same_shape_family_key`/`near_duplicate_key`,
  `hole_free_solver_input`, `outer_contour_complexity`, `dominant_edge_count`, `concavity_count`,
  `protrusion_count`, `interlock_potential_score`, `critical_anchor_score`, `filler_score`,
  `sheet_span_risk_score`. Ezek nem kerülhetik meg a CDE-t.
- Determinisztikus, nem-kizáró shape tag-ek (pl. `exact_rectangle`, `slender_long`, `large_anchor`,
  `critical_large`, `tiny_filler`, `repeated_family`, `high_interlock_potential`,
  `hole_free_after_prepack`, `orientation_sensitive`, `complex_outer_contour`, `edge_alignable`).
  Geometriából és mennyiségből származzanak, **ne** part-ID-ból.
- `fit_difficulty_score`: sheet span ratio, area ratio, low fill/concavity, high aspect, kevés hasznos
  orientáció, magas kontúr-komplexitás, ismételt kritikus mennyiség-nyomás (+), tiny filler (−). A
  `priority_score`-tól **külön** riportolva, nem csendben beolvasztva.
- Olcsó, determinisztikus family / near-duplicate kulcs (area/perimeter/vertex/convexity bucket-ek);
  drága shape matching nincs.
- Cavity interakció: csak rögzítsd és diagnosztizáld, hogy a Rustba érkező part hole-free-e
  (`hole_free_solver_input`, `hole_count_in_solver_input`, `cavity_prepack_bridge_status`). Részletes
  bridge munka az Q56B2-é.

## Required diagnostics

JSON artifact:

```text
artifacts/benchmarks/sgh_q56b/part_analysis_summary.json
```

Egyedi part-típusonként: `part_id`, `quantity`, `shape_tags`, `priority_score`,
`fit_difficulty_score`, `criticality_tier`, `orientation_sensitivity_score`,
`interlock_potential_score`, `family_key`, `hole_free_solver_input`, `outer_contour_complexity`,
`contour_feature_summary`. Plusz rendezett listák: `top_critical_parts_by_priority`,
`top_critical_parts_by_fit_difficulty`, `top_interlock_candidates_by_shape_signal`,
`tiny_filler_families`, `repeated_families`.

## Required tests / runners

Új teszt: `rust/vrs_solver/tests/sparrow_part_analysis.rs`. Ellenőrzések:

1. Minden `SPInstance` / egyedi part kap analízis-metaadatot.
2. A meglévő `PartShapeProfile` értékek továbbra is elérhetők.
3. A valós LV8 kritikus part large/critical/edge-alignable-ként van címkézve (ahol releváns).
4. Tiny filler shape-ek nem anchorként.
5. Fit difficulty determinisztikus.
6. Egyetlen shape tag sem enged bbox collision shortcutot.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml part_analysis
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
```

## Acceptance criteria

```text
- PartAnalysis / ShapeProfileV2 létezik és solver adathoz kötött.
- Újrahasználja a ShapeProfile + ContourFeatureSet réteget (nem vakon duplikál).
- Az új tag-ek/jelek determinisztikusak és diagnosztikával alátámasztottak.
- Nem változtat final placement viselkedést (csak explicit gated diagnosztika/rendezés, ha kérik).
- Használható artifactot ad valós partokra.
- Q55B továbbra is zöld.
```

## Hard restrictions

```text
- nincs párhuzamos, konfliktusos profilrendszer a régi mellett
- nincs part-ID alapú osztályozás
- shape tag nem exact collision/fit proof
- nincs cavity/hole logika a Rust fősolverben (worker prepack tisztelete)
- minden score-hoz tartozik magyarázó diagnosztika
- continuous rotation nem cserélhető diszkrét foklistára
- CDE/final exact validation marad az igazság
```

## Rollback

- Ha az analízis réteg regressziót okoz, tartsd read-only diagnosztikának (ne fonódjon placement
  döntésbe), és kapcsold le a rendezés-befolyásolást.
- Ha IO regresszió: additív/opcionális mezők.

## Deliverables

```text
canvases/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b_part_analysis_shape_profile_v2.yaml
codex/prompts/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2/run.md
codex/codex_checklist/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.verify.log
```
