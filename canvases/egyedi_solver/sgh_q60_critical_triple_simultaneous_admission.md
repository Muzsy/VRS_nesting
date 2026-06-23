# Q60 — Critical triple / simultaneous admission támogatás

## Goal / Funkció

Implementálj valódi kritikus multi-part simultaneous admission támogatást a nehéz esetekre, ahol a
szekvenciális egy-part admission elbukik. A cél nem brute-force teljes nesting solver, hanem bounded,
role-aware simultaneous admission mechanizmus kritikus pár/triple-re — különösen
`Anchor + Interlock + BandInsert`. Ez a Q56–Q59 utáni hiányzó lépés.

## Context / Háttér

A szekvenciális admission akkor is elbukhat, ha egy multi-part elrendezés feasibilis vagy közel az:
az első kritikus part elhelyezése után a szabad tér rossz lesz, és a második/harmadik nem férhet be. A
helyes stratégia: a kritikus csoportot együtt kezelni → Anchor/Interlock/BandInsert candidate-eket
közösen generálni → kis csoportként finomítani → a legjobb valid partial megőrzése. A
`simultaneous_critical_repack(...)` hook már létezik, de a mechanizmust teljessé és diagnosztikussá
kell tenni.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q60_Critical_triple_simultaneous_admission.md`
- Függés: Q56C (SheetEdgePlacementCatalog), Q57A/B (PairCompatibilityIndex/Interlock), Q58A/B
  (SheetFeasibilityHints), Q59 (BandInsert true-extreme).

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `simultaneous_critical_repack(...)`,
  `try_seeded_critical_separation(...)`, `try_admit_critical(...)`, `build_critical_aware_seed(...)`,
  best partial / fallback paths.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — `SkeletonRole`.
- Q56–Q59 outputok: OrientationCatalog, SheetEdgePlacementCatalog, PairCompatibilityIndex,
  SheetFeasibilityHints, BandInsert true-extreme slot-edge placement.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/io.rs
```

## Scope

- Bounded csoportok: 2-part kritikus pár, 3-part kritikus triple (nagyobb csoport nincs, hacsak nem
  olcsó és explicit bounded).
- Group candidate konstrukció a preprocessing rétegekből.
- Bounded simultaneous refinement (a csoport mozoghat, a placed non-group fix).
- Kötelező best-partial preservation.
- Gate: `VRS_SIMULTANEOUS_CRITICAL=1`.
- JSON + SVG artifact + fókuszált benchmark.

## Out of scope

- Unbounded all-part global optimizer.
- Spacing/margin csökkentés.
- Part-id-specifikus hack vagy hardcoded koordináták.

## Required implementation

Group candidate konstrukció: Anchor a SheetEdgePlacementCatalog-ból, Interlock a
PairCompatibilityIndex-ből, BandInsert a true-extreme slot-edge placementből, SheetFeasibilityHints
target kvóta, OrientationCatalog rotációk. Group candidate-ek: `Anchor only`, `Anchor + Interlock`,
`Anchor + Interlock + BandInsert`, `Anchor + Pair candidate + Slot candidate`. Minden group candidate:
`group_source`, `roles[]`, `part_ids[]`, `rotations[]`, `positions[]`, `source_candidates[]`,
`expected_critical_count`, `initial_score`.

Simultaneous refinement (bounded): kis coordinate descent / SA / bounded perturbation a csoporton; az
összes group part mozoghat, a placed non-group part fix; spacing-expanded collision; exact boundary;
continuous rotációk continuous-ak maradnak. **Nem** teljes, ha csak egyesével rak be partokat a
korábbi kritikus partok mozgatása nélkül.

Best-partial preservation (kötelező): incumbensek (`best_group_full`,
`best_group_partial_by_critical_count`, `best_group_partial_by_area`,
`best_group_partial_by_free_space_score`). Ha a 3-part full bukik, de a 2-part valid, a 2-part csoport
megmarad; soha nem regresszál rosszabb 1-partra valid 2-part után.

Scoring: `+critical_count`, `+target kvóta satisfaction` (magas súly ha Q58 hint van),
`+CDE/boundary clear` hard gate, `+placed area`, `+largest useful edge-connected free space`,
`+pair/triple compactness`, `+next sheet stratégia megőrzés`, `-fragmentation`, `-dead strip`,
`-excessive overlap after refinement` hard fail.

## Required diagnostics

Mezők: `bpp_simultaneous_critical_enabled`, `bpp_simultaneous_group_attempts`,
`bpp_simultaneous_group_size_counts`, `bpp_simultaneous_candidates_generated/refined`,
`bpp_simultaneous_full_successes`, `bpp_simultaneous_partial_successes`,
`bpp_simultaneous_best_partial_count`, `bpp_simultaneous_best_partial_source`,
`bpp_simultaneous_rejection_summary`, `bpp_simultaneous_time_ms`. Elfogadott csoportra:
`accepted_group_source`, `accepted_roles`, `accepted_part_ids`, `accepted_rotations`,
`accepted_positions`, `accepted_collision_pairs`, `accepted_boundary_violations`, `accepted_score`.

Artifact: `artifacts/benchmarks/sgh_q60/critical_group_admission.json` + `.svg` (az elfogadott
csoport vagy best partial, role-ok, candidate source).

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_critical_simultaneous_admission.rs`. Ellenőrzések:

1. Egy 2-kritikus csoport admittálható és validálható.
2. Egy 3-kritikus csoport simultaneous refinementet kísérel meg.
3. A korábbi group partok mozoghatnak a refinement alatt.
4. Ha a full 3 bukik, de a 2 sikerül, a best partial 2 megmarad.
5. A diagnosztika azonosítja a group source-ot és a partial/full kimenetet.
6. A szekvenciális fallback elérhető és logolt.

Fókuszált benchmark: 3 kritikus nagy part, 1 sheet 1500×3000, valós margin/spacing, continuous
rotation, skeleton + feature candidates + pair index + band insert true-extreme + simultaneous
critical bekapcsolva. Jelentsd a spacing=0 proofot **és** a valós konfigurált spacing futást
őszintén (a spacing=0 siker önmagában nem siker).

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_simultaneous
VRS_SIMULTANEOUS_CRITICAL=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_simultaneous
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
```

## Acceptance criteria

```text
- bounded 2/3 kritikus group candidate-ek léteznek;
- legalább pair-szintű simultaneous mozgás/refinement implementált;
- best partial preservation bizonyított;
- a diagnosztika és az artifact őszintén mutatja a full/partial eredményt;
- nincs regresszió a meglévő one-part/anchor/pair/band utakon;
- ha a valós 3-part spacing futás még bukik, az artifact megmagyarázza és megőrzi a best partialt.
```

## Hard restrictions

```text
- nincs ál-simultaneous (szekvenciális berakás a korábbiak mozgatása nélkül)
- valid best partial nem dobható el
- nincs spacing/margin csökkentés
- nincs LV8 part-name / koordináta hardcode
- nincs bbox-only collision check
- nem válhat unbounded all-part global optimizerré
- timeout/failure nem rejthető el sikerként
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- `VRS_SIMULTANEOUS_CRITICAL` gate default off → a meglévő szekvenciális admission marad
  (no-regression).
- Ha a refinement timeout-közeli, a best-partial incumbens kerül vissza, és a diagnosztika
  timeout-bound flaget tesz (a determinizmus gate timeout-bound kategóriaként kezeli).

## Deliverables

```text
canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q60_critical_triple_simultaneous_admission.yaml
codex/prompts/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission/run.md
codex/codex_checklist/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.verify.log
```
