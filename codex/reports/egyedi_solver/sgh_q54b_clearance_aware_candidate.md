# SGH-Q54B — Clearance-aware, edge-anchored candidate generation

## 1. Executive summary

A Q53 0-accepted **mikró-gyökerének** javítása. A Q53 `point_alignment_seed` a moving feature-pontot
**pontosan** a szomszéd/anchor pontjára tette (offset nélkül) → a spacing-expanded kontúrok garantáltan
ütköztek → 306/306 `seed_not_clear`. A Q54B a feature-illesztéseket **clearance-aware**-ré teszi: a
target a feature-normál (edge/protrusion) ill. a neighbour-centroid (vertex/edge-projection) mentén
`clearance`-szel **kifelé** tolódik, így a két spacing-expanded kontúr **éppen érinti** egymást, nem
fed. A `clearance` ≈ a technológiai spacing, a half-spacing-expanded collision shape vs az eredeti base
shape bbox-különbségéből visszanyerve. `clearance = 0` pontosan a Q53 pont-pont seedet adja vissza.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `optimizer/sparrow/feature_candidate_generator.rs` | `MovingFeatureSpec.clearance`; a 3 neighbour-illesztés target-eltolása (edge_midpoint_parallel: `±(EPS+clearance)·normal`; protrusion_into_concavity: target a zone-inward ellenében; point/vertex→edge: a neighbour-centroidtól kifelé); `clearance_from_instance` + `bbox_span`; `generate_feature_candidate_seeds_debug` + `clearance` param |
| `tests/sparrow_feature_candidates.rs`, `sparrow_feature_refine.rs` | a meglévő debug-hívók `clearance=0.0` (Q53 viselkedés megőrzve); új `q54b_clearance_offsets_neighbour_seeds_off_point_on_point` |

## 3. Hogyan működik

- **Clearance-offset:** mindhárom neighbour-driven illesztés (`edge_midpoint_parallel`,
  `protrusion_into_concavity`, `point_to_vertex` / `*_edge_projection`) a target-ot `clearance`-szel
  kifelé tolja — a CDE továbbra is az egyetlen clearance-igazság, ez csak a seed-pozíció.
- **Edge-anchored (Anchor szerep):** a `sheet_edge_candidates` már a domináns él ↔ tábla-él
  párhuzamosítást adja (continuous rotation); a boundary-t a sima base shape ellenőrzi (a margin a
  margin-inset sheet-extentekben), így a sheet-edge seed nem igényel spacing-offsetet.
- **Clearance forrás:** a `for_sheet` (valódi critical admission út) a `clearance_from_instance`-szel a
  SPInstance spacing-collision shape-jéből becsli a spacing-et; a debug API (teszt) explicit paramétert
  kap. `spacing = 0` → `clearance = 0` (ugyanaz a shape) → Q53 viselkedés.

## 4. Guardrailek

- CDE a collision truth; a clearance-offset **nem** collision döntés, csak seed-pozíció.
- Nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- **Continuous rotation érintetlen** (a clearance csak transzláció; a rotáció a meglévő
  `resolve_seed_rotation` / refine).
- A clearance-aware seed a feature-critical úton (Q53D `VRS_SHEET_BUILDER_FEATURE_CRITICAL`, default
  **off**) aktív; a default út byte-azonos (a `for_sheet` aláírás nem változott, a 21-blokkos suite zöld).
- Scope-fegyelem: egy forrásfájl (`feature_candidate_generator.rs`) + tesztek.

## 5. Tesztek

- `tests/sparrow_feature_candidates.rs::q54b_clearance_offsets_neighbour_seeds_off_point_on_point`:
  `clearance > 0` esetén **egyetlen** neighbour-seed sem esik a Q53 pont-pont pozícióra (azonos
  kind+rotation), és **van** seed pontosan `clearance` távolságra (a mechanizmus magnitúdója).
- A meglévő Q53B/Q53C feature tesztek `clearance = 0`-val zöldek (a Q53 viselkedés megőrizve).
- Teljes `vrs_solver` suite zöld (21 ok blokk, 0 failed); default-off no-regression.

## 6. DoD → Evidence

| DoD | Evidence |
| --- | --- |
| interlock seed clearance-offsettel (nem pont-pont) | `q54b_clearance_offsets_neighbour_seeds_off_point_on_point` (no-coincidence + exact-offset) |
| anchor él-párhuzamos (nem bbox-sarok) | `sheet_edge_candidates` (változatlan) + `feature_candidate_sheet_edge_alignment_exists_for_long_part` |
| default off → byte-azonos | a `for_sheet` aláírás változatlan; 21-blokkos suite zöld; clearance=0 = Q53 |
| nincs NFP / bbox shortcut; continuous rotation | `feature_candidate_generator.rs` (csak transzláció-offset; CDE dönt) |

## 7. Verdikt

**PASS — a mikró-gyökér javítva.** A feature-illesztések clearance-aware-ek: a seed gap-pel ül, nem
pont-pontra (a Q53 `seed_not_clear` oka). A clearance ≈ spacing, automatikusan a SPInstance-ből. A
seedek tényleges separation-be kötése (overlap-toleráns, a critical set együtt) a **Q54C**; a
skeleton-vázba ágyazás a Q54D/E.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-18T22:06:52+02:00 → 2026-06-18T22:10:02+02:00 (190s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.verify.log`
- git: `main@7df600c`
- módosított fájlok (git status): 29

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |  5 ++
 .../src/optimizer/sparrow/bpp_reduction.rs         | 38 +++++++++
 .../sparrow/feature_candidate_generator.rs         | 90 ++++++++++++++++++++--
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  1 +
 rust/vrs_solver/tests/sparrow_contour_features.rs  | 60 ++++++++++-----
 .../vrs_solver/tests/sparrow_feature_candidates.rs | 57 +++++++++++++-
 rust/vrs_solver/tests/sparrow_feature_refine.rs    |  3 +
 scripts/check.sh                                   |  8 ++
 8 files changed, 234 insertions(+), 28 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/tests/sparrow_contour_features.rs
 M rust/vrs_solver/tests/sparrow_feature_candidates.rs
 M rust/vrs_solver/tests/sparrow_feature_refine.rs
 M scripts/check.sh
?? canvases/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md
?? canvases/egyedi_solver/sgh_q54b_clearance_aware_candidate.md
?? canvases/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
?? canvases/egyedi_solver/sgh_q54d_freespace_band_insert.md
?? canvases/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md
?? codex/codex_checklist/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md
?? codex/codex_checklist/egyedi_solver/sgh_q54b_clearance_aware_candidate.md
?? codex/codex_checklist/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
?? codex/codex_checklist/egyedi_solver/sgh_q54d_freespace_band_insert.md
?? codex/codex_checklist/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54a_skeleton_state_role_assignment.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54b_clearance_aware_candidate.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54c_overlap_tolerant_separation.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54d_freespace_band_insert.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q54e_lv8_skeleton_proof.yaml
?? codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.md
?? codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.verify.log
?? codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.md
?? codex/reports/egyedi_solver/sgh_q54b_clearance_aware_candidate.verify.log
?? rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
?? rust/vrs_solver/tests/sparrow_sheet_skeleton.rs
```

<!-- AUTO_VERIFY_END -->
