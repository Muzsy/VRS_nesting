# Q56A — OrientationCatalog alap

## Goal / Funkció

Vezess be egy production `OrientationCatalog` réteget minden egyedi part-típushoz a Sparrow
solverben. A katalógus part-típusonként **egyszer** kerül kiszámításra és a part/instance analízis
réteghez csatolva. Nem írja át azonnal a placement stratégiát: első célja, hogy megbízható,
újrahasználható, diagnosztikával alátámasztott orientációs jelölteket adjon a későbbi Anchor /
Interlock / BandInsert / PairCompatibility munkának.

## Context / Háttér

A repo ma több, párhuzamos, részleges orientációs mechanizmust tartalmaz:

```text
ContourFeatureSet.sheet_edge_alignment_angles
min_width_rotations(...)              (feature_candidate_generator.rs)
sheet-edge anchor szögek              (feature_candidate_generator.rs)
density rotation jelöltek             (density.rs)
0/90/180/270 fallback + fit check     (több helyen)
```

Ez a szétszórtság kockázatos: ugyanazt a fogalmat különböző placement utak különbözőképpen
számolják, a continuous rotation egyes utakon csendben degradálódik, és a diagnosztika nem tudja
megmagyarázni, miért létezett vagy miért lett kiválasztva egy rotációs jelölt. A Q56A ezt úgy oldja
meg, hogy az orientációs jelölteket első osztályú, előre kiszámított objektummá teszi.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q56A_OrientationCatalog_alap.md`
- A CDE marad a collision/boundary igazság; a katalógus csak döntéstámogató metaadat.

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs` — `ContourFeatureSet`,
  `sheet_edge_alignment_angles`, dominant edge / extreme point logika.
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — `PartShapeProfile`,
  `criticality_tier()`, `is_critical()`.
- `rust/vrs_solver/src/optimizer/sparrow/model.rs` — `SPInstance`,
  `spacing_collision_base_shape`, `shape_profile: Rc<PartShapeProfile>`,
  `continuous_rotation`, `from_solver_input(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs` —
  `min_width_rotations(...)`, `nearest_axis_angle_deg(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/mod.rs` — modul-regisztráció.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/contour_features.rs
rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/io.rs
```

Megjegyzés: `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` még **nem létezik** —
ez a task egyik deliverable-je (új fájl, létrehozandó). A konkrét Rust nevek eltérhetnek a
forrástervben javasoltaktól, de az átadott modellnek ekvivalens információt kell adnia.

## Scope

- Új `orientation_catalog.rs` modul: `OrientationCatalog`, `OrientationCandidate`,
  `OrientationCandidateKind`, `OrientationExtremaSample` (vagy ekvivalens).
- A katalógus part-típusonként egyszer számolódik a `from_solver_input(...)` (vagy ekvivalens
  építési) úton, és minden mennyiségre újrahasználódik.
- Minimális integráció: `SPInstance` kap `orientation_catalog: Rc<OrientationCatalog>` mezőt.
- JSON diagnosztika export legalább egy valós LV8 kritikus partra.
- Fókuszált unit tesztek.

## Out of scope

- Placement viselkedés átírása (Anchor/Interlock/BandInsert választás).
- NFP visszahozása vagy pairwise NFP mátrix.
- Cavity/hole logika a Rust fősolverben.
- A `PartAnalysis` réteg (az Q56B feladata; itt csak tiszta integrációs slot készül).

## Required implementation

- Az extrema mintákhoz a **spacing-expanded** collision kontúrt használd:
  `SPInstance.spacing_collision_base_shape` (vagy ekvivalens spacing-clearance geometria).
  Minden mintavételezett szögnél a valós lokális kontúrpontokat forgasd el, és abból számolj
  `min_x/max_x/min_y/max_y`-t. **Tilos** a `part.width`/`part.height`, nem forgatott bbox vagy
  spacing nélküli alak final extrémaként.
- Continuous partoknál generálj: dominant edge → vertical sheet-axis, dominant edge → horizontal
  sheet-axis, min-width / min-height jelölteket, magas értékű jelöltek 180° flipjeit, indokolt
  finom variánsokat. Diszkrét partoknál: allowed rotations + kind/source metaadat ott, ahol egy
  allowed rotation feature-illesztésnek felel meg.
- **Ne snappeld** a continuous jelölteket 0/90/180/270-re, kivéve ha a számolt continuous eredmény
  ténylegesen az a szög.
- Dedup normalizált szög-toleranciával (javaslat: 0.01° identitás, 0.25° riport-csoport),
  determinisztikus sorrenddel.

## Required diagnostics

JSON artifact legalább egy valós LV8 kritikus partra:

```text
artifacts/benchmarks/sgh_q56a/orientation_catalog_lv8_critical.json
```

Kötelező mezők: `part_id`, `continuous_rotation`, `allowed_rotations_count`, `candidate_count`,
`vertical_alignment_count`, `horizontal_alignment_count`, `min_width_candidate_count`,
`min_height_candidate_count`, `fractional_candidate_count`, `spacing_extrema_sample_count`,
`candidates[]` (`angle_deg`, `kind`, `source_edge_index`, `source_edge_angle_deg`,
`target_axis_angle_deg`, `score`, `is_fractional`, `is_policy_allowed`),
`extrema_samples[]` (`angle_deg`, `width`, `height`, `min_x`, `max_x`, `min_y`, `max_y`).

## Required tests / runners

Új teszt: `rust/vrs_solver/tests/sparrow_orientation_catalog.rs`. Ellenőrzések:

1. Valós kritikus LV8 part nem üres katalógust ad.
2. Continuous partok continuous feature-eredetű jelölteket kapnak.
3. Legalább egy jelölt valós kontúr-élhez visszavezethető (ahol van dominant edge).
4. Extrema minták a spacing-expanded kontúrból.
5. Diszkrét partok nem kapnak illegális continuous jelöltet.
6. A dedup determinisztikus.
7. A Q55B one-part sheet-edge teszt továbbra is zöld.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml orientation_catalog
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
```

## Acceptance criteria

```text
- OrientationCatalog létezik újrahasználható modul/modellként.
- A katalógus part-típusonként egyszer számolódik, nem placement-kísérletenként.
- Continuous és discrete rotation policy is tiszteletben tartva.
- Az extrema valós spacing-expanded kontúrpontokon alapul.
- Valós LV8 kritikus part diagnosztika generálódik.
- Egy placement út sem változik csendben (csak explicit dokumentálva).
- A meglévő tesztek zöldek, különösen a Q55B sheet-edge proof.
```

## Hard restrictions

```text
- nincs NFP-visszahozás
- nincs bbox collision shortcut (part.width/height nem final extrema)
- nincs part-id hack
- nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- Ha a katalógus integrációja regressziót okoz, tartsd `Rc<OrientationCatalog>`-ot additív,
  nem-kötelező mezőként, és ne kösd be placement útba (read-only diagnosztika marad).
- Ha az extrema számítás IO regressziót okoz, csak additív/opcionális mezőként exportáld.

## Deliverables

```text
canvases/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56a_orientation_catalog_alap.yaml
codex/prompts/egyedi_solver/sgh_q56a_orientation_catalog_alap/run.md
codex/codex_checklist/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.verify.log
```
