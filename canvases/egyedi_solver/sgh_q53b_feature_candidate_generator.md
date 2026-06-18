# Q53B — Feature-to-feature candidate generator

## Goal

A Q53A feature-ekből valódi kontúrfeature-alapú placement candidate-eket generálni critical partokhoz, bbox-sarok primary seed nélkül.

## Háttér

Q48–Q52 alatt a `contour-near` candidate generálás neve félrevezető lett: a jelenlegi út a szomszéd kontúrvertexeit a mozgatott alkatrész rotated bbox-sarkaival igazítja. Ez olcsó seed, de konkáv/íves/low-fill alkatrészeknél rossz jelöltteret ad. A következő fejlesztési blokk célja: critical admissionben valódi kontúrfeature-alapú candidate-eket generálni, majd CDE-vel validálni.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/density.rs`
  - `contour_near_rect_mins`
  - `density_candidate_score`
  - `is_interlock_candidate`
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `density_insert_part`
  - `density_biased_separate`
  - `try_admit_critical`
  - `build_critical_aware_seed`
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs`
  - `PartShapeProfile`
  - `CriticalityTier`
- `rust/vrs_solver/src/optimizer/sparrow/model.rs`
  - `SPInstance`
  - `SparrowRotationDomain`
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs`
- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs`
- `rust/vrs_solver/src/io.rs`
  - optimizer diagnostics export

## Globális guardrailek

- Valós repo alapján dolgozz: először olvasd el az `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`, valamint a Q47–Q52 canvas/report fájlokat.
- CDE marad a collision truth. Tilos bbox/AABB collision shortcutot bevezetni.
- Tilos NFP-t visszahozni vagy pairwise NFP-kompatibilitási mátrixot számolni.
- Continuous rotation nem váltható ki diszkrét foklistával. Seed lehet, de refine/final nem snappelhet fix listára.
- Cavity/hole nincs a fő solverben; csak külső kontúrrel dolgozz.
- Nincs `part_id`-specifikus hack, nincs hardcoded `3 big per sheet` szabály.
- A régi `contour_near_rect_mins` bbox-sarok seed maradhat fallbacknek, de critical admissionnél nem lehet primary stratégia.
- Minden új viselkedés opt-in/gated legyen, amíg a regressziómentesség nincs bizonyítva.
- Minden output validáció final CDE-valid legyen: 0 collision, 0 boundary/spacing violation.


## Feladat

Hozz létre feature-to-feature candidate generátort. A cél nem final placement, hanem jobb jelölttér: moving part saját kontúrfeature + placed neighbour vagy sheet-edge feature alapján seedeljen.

### Kötelező candidate források

- `moving dominant_edge ↔ sheet edge`
- `moving long/dominant_edge ↔ neighbour long/dominant_edge`
- `moving extreme/protrusion ↔ neighbour concave zone / edge neighbourhood`
- `moving vertex/extreme ↔ neighbour vertex/edge projection`

### Candidate metadata

Minden feature candidate tartalmazzon:

- `x`, `y`, `rotation_seed`
- `source = contour_feature`
- `moving_feature_type`
- `target_feature_type`
- `alignment_kind`
- `source_score` / rank

### Kötelező viselkedés

- Critical/high-interlock partoknál a feature candidate legyen primary.
- A régi `contour_near_rect_mins` maradhat fallbackként, de külön diagnosztikában kell mérni.
- Minden candidate final clearance-e CDE-n keresztül történik.
- Discrete rotation policy esetén csak allowed rotation lehet. Continuous esetén a seed nem constraint.

### DoD

- Unit teszt bizonyítja, hogy a generator nem a moving bbox sarkait illeszti.
- Sheet-edge alignment candidate létrejön hosszú/critical partnál.
- Neighbour feature alignment candidate létrejön konkáv/feature-rich partpárnál.
- Diagnosztika külön számolja: feature candidates vs bbox-corner fallback candidates.


## Runner / verification

Ajánlott célzott parancsok:

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml density`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.md`

A végső gate mindig:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.md
```

## Rollback

- Ha a feature path invalid layoutot okoz, kapcsold ki a Q53 gate-et és tartsd meg a régi Q52/Q51 fallbacket.
- Ha continuous rotation guardrail sérül, revert a Q53C/D érintett részeire.
- Ha a diagnostics mezők IO regressziót okoznak, csak additive/optional mezőként exportáld őket.
