# Q53E — LV8 proof + diagnostics

## Goal

A Q53 mechanizmus bizonyítása célzott LV8 critical admission futással és teljes diagnosztikával.

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

Ez nem új vak benchmark, hanem mechanizmus-gate. A kérdés: a feature-first critical admission képes-e spacing 5 mellett legalább egy sheeten 3 nagy critical alkatrészt CDE-valid módon létrehozni.

### Kötelező futások

- `6× Lv8_11612`, sheet `1500×3000`, spacing `5`, margin `5`, continuous rotation.
- Kontroll: Q52/Q51 builder-only vagy feature-off arm.
- Feature-on arm: Q53 feature critical admission bekapcsolva.
- Opcionális: spacing `8` és full276 csak regressziós/advisory, nem primary acceptance.

### Acceptance

Primary:

- Feature-on futás valid.
- Legalább egy sheeten 3 `Lv8_11612` példány CDE-valid.
- Diagnosztika bizonyítja, hogy feature candidates futottak és legalább egy accepted critical admission ezekből származott, vagy ha nem, pontos fail reason.

Nem acceptance:

- Full276 2 sheet nem kötelező ebben a taskban.
- Nem kell production defaultot bekapcsolni.

### Kötelező artefaktok

- `artifacts/benchmarks/sgh_q53/q53_summary.json`
- `artifacts/benchmarks/sgh_q53/q53_report.md`
- `artifacts/benchmarks/sgh_q53/outputs/*.json`
- `artifacts/benchmarks/sgh_q53/renders/*.svg`
- `artifacts/benchmarks/sgh_q53/renders/*.png`, ha a repo render toolingja elérhető.
- `artifacts/benchmarks/sgh_q53/logs/*.log`

### Diagnosztika

- feature_candidates_generated / accepted
- bbox_corner_candidates_generated / accepted
- accepted_feature_pair_type
- seed_rotation / refined_rotation
- edge_distance
- CDE rejection reason summary
- critical admission success/fail
- critical phase close reason
- big parts per sheet


## Runner / verification

Ajánlott célzott parancsok:

- `python3 scripts/bench_sgh_q53_feature_admission.py --case 6big --spacing 5 --time-limit 600`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_feature_admission`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md`

A végső gate mindig:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md
```

## Rollback

- Ha a feature path invalid layoutot okoz, kapcsold ki a Q53 gate-et és tartsd meg a régi Q52/Q51 fallbacket.
- Ha continuous rotation guardrail sérül, revert a Q53C/D érintett részeire.
- Ha a diagnostics mezők IO regressziót okoznak, csak additive/optional mezőként exportáld őket.
