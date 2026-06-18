# Q54B — Clearance-aware, edge-anchored candidate generation

## Goal

A Q53 0-accepted **mikró-gyökerének** javítása: a feature-illesztés ne **pont-pontra** tegyen (a
jelenlegi `point_alignment_seed` clearance nélkül illeszti a moving feature-pontot a szomszéd/anchor
pontjára → a spacing-expanded kontúrok garantáltan ütköznek → `seed_not_clear`). A Q54B clearance-aware
candidate-eket generál a Q54A szerepekhez: **anchor** = tábla-élhez igazított, **interlock** =
clearance-offsettel illesztett (vagy kontrollált overlappal seedelt) jelölt — **valódi continuous
rotation**-nel.

## Háttér

A Q53 audit kódszintű gyökere: `feature_candidate_generator.rs::point_alignment_seed` a moving feature
csúcsát pontosan a target (szomszéd concave anchor / él) pontjára teszi, offset nélkül. Spacing 5 (≈2.5
mm fél-offset) mellett ez 306/306 esetben `seed_not_clear`. A megoldás nem „több candidate", hanem a
seed **clearance-aware** pozícionálása: a feature-normál mentén half_spacing+ε offset (a spacing-expanded
kontúrok éppen érintik, nem fedik), illetve anchor szerepnél a tábla élével párhuzamosított, margin+spacing
távolságra húzott elhelyezés. A continuous rotation finomítás (88–92° is, nem fix 90/270) a Q52
`density_rotation_candidates` mintáját követi.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs`
  - `generate_feature_candidate_seeds_impl`, `point_alignment_seed`, `CandidateSeed`, `resolve_seed_rotation`
- `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs`
  - `ContourFeatureSet` (dominant_edges, concave_zones, protrusion_candidates, sheet_edge_alignment_angles, edge normals)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` (Q54A — role)
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `density_rotation_candidates` (continuous refine minta), `try_admit_critical`
- `rust/vrs_solver/src/optimizer/sparrow/model.rs` — `SPInstance`, `SheetShape` (margin/spacing extents)
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- CDE marad a collision truth; tilos bbox/AABB collision shortcut; a clearance-offset **nem** collision
  döntés, csak seed-pozícionálás — a végső clearance-t mindig a CDE dönti.
- Tilos NFP / pairwise NFP mátrix.
- **Continuous rotation marad continuous** — a seed lehet kiindulópont, de a candidate rotation nem
  snappel fix listára; az anchor él-párhuzamos szöge folytonos (pl. ~88.3°), nem 90.
- Cavity/hole nincs a fő solverben.
- Nincs `part_id` hack, nincs hardcoded 3+3.
- Gated (`VRS_SHEET_BUILDER_SKELETON`); a régi `point_alignment_seed` (pont-pont) és a
  `contour_near_rect_mins` bbox-sarok marad fallbacknek, de critical admissionnél nem primary.
- Scope-fegyelem: a változások a `feature_candidate_generator.rs`-re és az új skeleton-modulra
  korlátozódjanak; ne ömöljenek a core search-be.

## Feladat

### Clearance-aware seed pozícionálás

- `point_alignment_seed` kapjon **offset-paramétert**: a moving feature-pontot a target pont helyett a
  feature-normál mentén `half_spacing + ε` távolságra tegye (a két spacing-expanded kontúr éppen érintkezik).
  A half_spacing az `SPInstance` spacing-collision shape-jéből / a technológiai spacingből adódik.
- Alternatív mód (interlock szerep): **kontrollált kis overlap** seed — a Q54C overlap-toleráns
  separatora tisztítja. A két mód közül a szerep/diagnosztika dönt.

### Edge-anchored candidate (Anchor szerep)

- A domináns hosszú él / nyúlvány a tábla szélével **párhuzamosítva** (sheet_edge_alignment_angle,
  continuous), margin+spacing távolságra a táblaszéltől, sarok-preferenciával.

### Role-tudatos generálás

- A Q54A `assign_role` szerint: `Anchor` → edge-anchored candidate-ek; `Interlock` → clearance-offset /
  kontrollált-overlap feature-pár candidate-ek a meglévő anchorhoz; `BandInsert` candidate a Q54D-ben.

### DoD

- Unit teszt: a generált anchor candidate a táblaszéllel párhuzamos, margin+spacing távolságra (nem
  bbox-sarok, nem pont-pont).
- Unit teszt: interlock candidate clearance-offsettel → szintetikus konkáv páron a seed **közvetlenül
  CDE-clear** VAGY a `seed_overlap` a kontrollált küszöb alatt (szemben a Q53 garantált ütközésével).
- Diagnosztika: `clearance_offset_applied`, `seed_directly_clear_count`, `controlled_overlap_seed_count`,
  szerepenkénti candidate count.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml clearance`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.md`

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.md
```

## Rollback

- Ha a clearance-aware seed regressziót okoz, kapcsold a gate-et off-ra; a Q53 pont-pont seed és a
  bbox-sarok fallback érintetlen marad.
- Ha a continuous rotation guardrail sérülne (snapping), azonnali revert az érintett rotation-részre.
