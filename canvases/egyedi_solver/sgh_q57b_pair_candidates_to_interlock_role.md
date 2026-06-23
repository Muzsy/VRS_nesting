# Q57B — Pair candidate-ek bekötése az Interlock szerephez

## Goal / Funkció

Kösd be a Q57A `PairCompatibilityIndex`-et a meglévő skeleton `Interlock` szerephez. A jelenlegi
Interlock út reaktív (lokális feature candidate-ek a már elhelyezett szomszédok ellen). A Q57B
proaktívvá teszi: ha a skeleton role `Interlock`, a solver először az elhelyezett Anchor-t és a
candidate kritikus partot érintő, előre számolt pair candidate-eket konzultálja.

## Context / Háttér

A pair index relatív transzformot ad (`part_a@rot_a, pos_a` + `part_b@rot_b, rel_dx, rel_dy`). Ha az
elhelyezett Anchor a part A: `candidate_x = anchor_x + rel_dx`, `candidate_y = anchor_y + rel_dy`,
`candidate_rot = rotation_b` (B esetén invertálva). A konverziónak figyelembe kell vennie a placement
reprezentációt (rect-min / candidate frame / local origin) — origin szemantika bizonyítás nélkül nem
feltételezhető. A transzformációs matek logolandó.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q57B_Pair_candidates_to_Interlock_role.md`
- Függés: Q57A `PairCompatibilityIndex`.

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — `SkeletonRole::Interlock`,
  `SheetSkeletonState`.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `try_admit_critical(...)`,
  feature-first candidate admission, role filtering, `try_seeded_critical_separation(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs` —
  `neighbour_feature_candidates(...)`, `generate_feature_candidate_seeds_for_sheet(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs` — Q57A index.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs
rust/vrs_solver/src/io.rs
```

## Scope

- Interlock role pair-index konzultáció + pair relatív transzform → sheet placement seed konverzió.
- Exact CDE / spacing-expanded validáció + role-specifikus rangsor.
- Fallback a meglévő neighbour feature candidate-ekre (megőrizve, logolva).
- JSON artifact valós kritikus szcenárióra.

## Out of scope

- Pair candidate-ek kötelező superpartként kezelése.
- A neighbour feature candidate fallback eltávolítása.
- Simultaneous triple admission (Q60).

## Required implementation

Amikor `SkeletonRole::Interlock`:
1. Azonosítsd az elhelyezett kritikus Anchor(oka)t a cél sheeten.
2. Kérdezd le a PairCompatibilityIndex-et az anchor part type + candidate kritikus part type párra.
3. Konvertáld a pair relatív transzformot placement seed-dé (origin szemantika bizonyítva, matek logolva).
4. Validáld a candidate placementet exact CDE / spacing-expanded alakokkal.
5. Rangsorolj pair score + eredő free-space score szerint.
6. Fallback a meglévő neighbour feature candidate-ekre csak ha nincs sikeres pair-index candidate.

Role-specifikus score: `+pair_index_score`, `+cde_clear` hard gate, `+compactness_gain`,
`+interlock_depth_score`, `+largest_edge_connected_free_area`, `+BandInsert slot megőrzés`,
`-collision/boundary` hard fail, `-fragmentation` (ha elérhető). Ha Q58A megvan, használd a
SheetFeasibilityHints-et a következő kritikus part kapacitás-becsléséhez.

## Required diagnostics

Bővítsd a BPP/skeleton diagnosztikát: `bpp_role_interlock_pair_index_queries`,
`bpp_role_interlock_pair_candidates_generated/valid/accepted`,
`bpp_role_interlock_pair_fallback_to_feature_candidates`, `bpp_interlock_accepted_pair_source`,
`bpp_interlock_accepted_pair_score`, `bpp_interlock_accepted_relative_transform`. Rejection okok
aggregálva: `boundary_violation`, `collision`, `pair_not_found`, `role_anchor_missing`,
`transform_invalid`, `cde_not_clear`, `score_too_low`.

Artifact: `artifacts/benchmarks/sgh_q57b/interlock_pair_admission.json` — `anchor_part_id`,
`candidate_part_id`, `role=interlock`, `pair_candidates_considered`, `accepted_candidate_source`,
`accepted_rotation`, `accepted_position`, `pair_score`, `free_space_score_after`, `cde_clear`,
`boundary_clear`.

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_interlock_pair_candidates.rs`. Ellenőrzések:

1. Az Interlock role lekérdezi a pair indexet, ha elérhető.
2. Same kritikus part pár placement seed-dé konvertálható.
3. A pair-index candidate source látható a diagnosztikában.
4. Ha a pair indexnek nincs valid candidate-je, a régi feature candidate fallback működik.
5. Az elfogadott candidate exact CDE clear.
6. A Q55B/Q56C Anchor tesztek továbbra is zöldek.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml interlock_pair
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_sheet_skeleton
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
```

## Acceptance criteria

```text
- Az Interlock role konzultálja a PairCompatibilityIndex-et.
- A pair candidate-ek placement seed-dé konvertálhatók egy elhelyezett Anchor ellen.
- Az elfogadott út pair-index Interlockként látható a diagnosztikában.
- A fallback elérhető és logolt.
- Valós kritikus teszt/artifact létezik.
```

## Hard restrictions

```text
- pair candidate nem kötelező superpart
- a neighbour feature candidate fallback nem távolítható el
- pair transzform CDE validáció nélkül nem fogadható el
- nincs part-ID / LV8 hardcode
- bbox overlap nem clearance truth
- a placement origin szemantika nem hagyható figyelmen kívül a transzform-konverziónál
- nincs NFP, nincs spacing/margin gyengítés
- continuous rotation nem cserélhető diszkrét foklistára
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- Az Interlock pair-út env-gated; kikapcsolva a meglévő reaktív neighbour-feature viselkedés marad
  (no-regression).
- Ha a transzform-konverzió hibás placementet ad, a candidate elbukik a CDE-n és a fallback lép be —
  ezt a diagnosztika rögzíti, nem rejti el.

## Deliverables

```text
canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57b_pair_candidates_to_interlock_role.yaml
codex/prompts/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role/run.md
codex/codex_checklist/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.verify.log
```
