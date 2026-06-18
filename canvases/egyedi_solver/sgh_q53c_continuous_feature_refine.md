# Q53C — Continuous rotation refinement for feature candidates

## Goal

Feature candidate seedekből valódi continuous rotation + translation refine út, snapping nélkül.

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

A Q53B feature candidate még csak seed. Ebben a taskban az elfogadási út kapjon continuous local refine lépést.

### Kötelező elvek

- Continuous rotation esetén a seed rotation csak kezdőérték.
- A refine valós rotációs változóval dolgozzon, ne allowed-degree listával.
- Nincs snapping 0/45/90/270 vagy hasonló listára.
- Discrete rotation policy esetén viszont csak a megengedett rotációk használhatók.
- Final candidate CDE-validáció kötelező.

### Javasolt technika

- Kis lokális translation + rotation perturbáció.
- Coord-descent jellegű refine a meglévő `sample/coord_descent.rs` mintáját követve, de feature seedre illesztve.
- A score primary: CDE clear / collision proxy javulás; secondary: density/free-space/edge anchor score.

### DoD

- Continuous partnál `seed_rotation` és `refined_rotation` külön diagnosztikában látszik.
- LV8-szerű nagy partnál exact 90/270 mellett nem exact 90/270 körüli refined rotációk is megjelenhetnek.
- Discrete policy guardrail teszt zöld.
- A refine nem rontja final validationt.


## Runner / verification

Ajánlott célzott parancsok:

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml continuous_feature_refine`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53c_continuous_feature_refine.md`

A végső gate mindig:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53c_continuous_feature_refine.md
```

## Rollback

- Ha a feature path invalid layoutot okoz, kapcsold ki a Q53 gate-et és tartsd meg a régi Q52/Q51 fallbacket.
- Ha continuous rotation guardrail sérül, revert a Q53C/D érintett részeire.
- Ha a diagnostics mezők IO regressziót okoznak, csak additive/optional mezőként exportáld őket.
