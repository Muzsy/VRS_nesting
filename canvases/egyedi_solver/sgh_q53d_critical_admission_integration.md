# Q53D — Critical admission integration

## Goal

A feature candidate + continuous refine út bekötése a Q51 critical admissionbe, filler/medium előtti konstruktív sheet építésnél.

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

Kösd be a Q53 feature candidate/refine utat a critical-aware builder admission fázisába. A cél: critical partoknál ne a bbox-corner density seed legyen az elsődleges próbálkozás.

### Kötelező path

`try_admit_critical` új sorrendje:

1. Feature-based direct admission, CDE clear final.
2. Feature-based co-movable admission: existing critical anchors + candidate mozgatható.
3. Density/bbox-corner fallback csak másodlagosan, diagnosztikában elkülönítve.

### Kötelező viselkedés

- Critical phase alatt filler/medium ne zárja le a teret.
- Existing critical anchors mozgathatók maradnak admission közben.
- Critical admission phase close reason kötelező.
- Nincs part-id hack és nincs előre kikényszerített darabszám.
- Default/gate regressziómentesség bizonyítva.

### Diagnosztika

- critical_feature_admission_attempts
- critical_feature_admission_successes
- critical_feature_admission_failures
- feature_candidates_generated/accepted
- fallback_bbox_candidates_generated/accepted
- accepted_feature_pair_type
- critical_phase_close_reason
- candidate rejection reason summary

### DoD

- Q51 builder path feature-first critical admissiont használ opt-in módban.
- Feature path futását diagnosztika bizonyítja.
- Fallback explicit és mérhető.
- Final output CDE-valid.


## Runner / verification

Ajánlott célzott parancsok:

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_feature_admission`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml sparrow_sheet_builder`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53d_critical_admission_integration.md`

A végső gate mindig:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53d_critical_admission_integration.md
```

## Rollback

- Ha a feature path invalid layoutot okoz, kapcsold ki a Q53 gate-et és tartsd meg a régi Q52/Q51 fallbacket.
- Ha continuous rotation guardrail sérül, revert a Q53C/D érintett részeire.
- Ha a diagnostics mezők IO regressziót okoznak, csak additive/optional mezőként exportáld őket.
