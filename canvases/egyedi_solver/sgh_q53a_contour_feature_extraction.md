# Q53A — Contour feature extraction

## Goal

Külső kontúrból olcsó, determinisztikus geometriai feature-öket számolni critical candidate generáláshoz, bbox-sarok illesztés nélkül.

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

Hozz létre egy új kontúrfeature réteget a `vrs_solver` Sparrow moduljában. Ez még nem változtathat placement viselkedést. Csak feature-eket számol és riportol.

### Kötelező feature típusok

- `ContourVertex`: reprezentatív vertex, lokális indexszel.
- `ContourEdge`: külső kontúr él, hossz, angle, midpoint.
- `DominantEdge`: hosszú / sheet-edge alignment szempontból hasznos él.
- `ExtremePoint`: min/max x/y vagy projection extremum.
- `ConcaveVertex` / `ConcaveZone`: külső kontúr konkáv lokális környezete.
- `ProtrusionCandidate`: lokális kiálló rész jelöltje, olcsó heurisztikával.
- `SheetEdgeAlignmentAngle`: domináns élből származtatott folyamatos rotation seed szög, nem allowed-rotation lista.

### Kötelező műszaki elvek

- A feature-ek a külső kontúrból jönnek, nem bboxból.
- A feature extraction nem validál collisiont.
- A feature extraction nem módosít rotation policyt.
- Continuous partnál a feature angle csak seed/diagnosztika; nem diszkrét rotációs constraint.
- Belső kontúr/hole/cavity mező nincs.
- Determinisztikus sorrend: azonos inputra azonos feature lista.

### Javasolt új fájlok / módosítások

- Új: `rust/vrs_solver/src/optimizer/sparrow/contour_features.rs`
- Módosítás: `rust/vrs_solver/src/optimizer/sparrow/mod.rs`
- Módosítás: `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` vagy `model.rs`, csak ha szükséges a profilhoz/instance-hez kötni.
- Teszt: `rust/vrs_solver/tests/sparrow_contour_features.rs` vagy meglévő `tests` modulba illesztve, a repo mintája szerint.
- Diagnosztika: `rust/vrs_solver/src/io.rs`, ha a feature summary exportálható.

### DoD

- A kontúrfeature számítás unit tesztekkel fedett.
- LV8 nagy alkatrésznél nem üres feature lista jön létre; vannak domináns/long-edge és concavity/protrusion jelöltek.
- Nincs collision pipeline változás.
- Nincs bbox collision shortcut.
- Nincs NFP.
- A reportban szerepel vertex count → feature count összegzés legalább egy LV8 inputra.


## Runner / verification

Ajánlott célzott parancsok:

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml contour_features`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml shape_profile`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md`

A végső gate mindig:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md
```

## Rollback

- Ha a feature path invalid layoutot okoz, kapcsold ki a Q53 gate-et és tartsd meg a régi Q52/Q51 fallbacket.
- Ha continuous rotation guardrail sérül, revert a Q53C/D érintett részeire.
- Ha a diagnostics mezők IO regressziót okoznak, csak additive/optional mezőként exportáld őket.
