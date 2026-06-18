# SGH-Q54A — Skeleton state + critical role assignment

## 1. Executive summary

A Q54 ("kettő egyben" skeleton-aware critical admission) alaprétege: egy `SheetSkeletonState`, amely
sheetenként követi az admittált critical alkatrészeket (role + world bbox), és egy `assign_role`
függvény, amely a következő critical jelöltnek `Anchor` / `Interlock` / `BandInsert` szerepet ad — a
sheet **topológiájából** (open anchor van-e) és a part **Q47-profiljából** (interlock-képes-e),
**darabszám-hardcode nélkül**.

**Kulcs-invariáns (Q54A):** ez tisztán állapot/döntés réteg — **nem változtat placementet**. Gated
(`VRS_SHEET_BUILDER_SKELETON`, default off): gate off → soha nem épül, Q51/Q52 byte-azonos; gate on →
ugyanaz a placement, csak +role-diagnosztika (a Q54B+ fog a role-ra hatni). Az integrációs teszt
byte-azonos geometriát bizonyít skeleton on/off között.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `optimizer/sparrow/sheet_skeleton.rs` (új) | `SkeletonRole`, `SheetSkeletonState` (record/critical_count/has_open_anchor/admitted/role_counts), `RoleInputs::from_profile`, `assign_role`, `skeleton_builder_enabled`; 5 unit teszt |
| `optimizer/sparrow/mod.rs` | `pub mod sheet_skeleton;` |
| `optimizer/sparrow/bpp_reduction.rs` | `build_critical_aware_seed` gated bekötés (role az admittálás előtt, `record_admission` után), `critical_world_bbox` helper, role-count diagnosztika |
| `io.rs` | `bpp_skeleton_anchor/interlock/bandinsert_count` (additív) |
| `tests/sparrow_sheet_skeleton.rs` (új) | placement-invariancia (byte-azonos on/off) + role rögzítve |

## 3. Hogyan működik

- **Szerep (`assign_role`):** `Anchor`, ha a sheeten még nincs critical (élhez-anchorolt első nagy);
  `Interlock`, ha van **open anchor** (anchor interlock-partner nélkül) ÉS a jelölt interlock-képes
  (`is_high_interlock_potential || is_concave_like`); különben `BandInsert` (a pár lezárva → külön
  edge-connected sáv). A döntés a sheet állapotából + a profil-jelekből; nem látja a queue méretét.
- **State:** `record_admission(sheet, instance, role, bbox)` — a bbox a Q54D free-space proxyjához
  rögzített geometria (a `critical_world_bbox` a placement rect-min/rotated-dims konvencióval számolja).
- **Bekötés:** a `build_critical_aware_seed` critical admission loopjában a role az admittálás **előtt**
  számolódik, sikeres admittálás **után** rögzül; a `try_admit_critical` hívás változatlan → placement
  nem változik.

## 4. Guardrailek

- CDE a collision truth; nincs NFP, nincs bbox collision shortcut, nincs cavity/hole fősolver logika.
- Continuous rotation érintetlen (Q54A nem nyúl rotációhoz).
- Nincs `part_id` hack, **nincs hardcoded 3+3** — a szerep topológia+profil alapú.
- Default off → byte-azonos; gate on is placement-invariáns (csak diagnosztika).
- Scope-fegyelem: új logika új modulban; a `bpp_reduction.rs` változása a gated bekötésre + a bbox
  helperre + a diagnosztikára korlátozódik.

## 5. Tesztek

- `sheet_skeleton.rs::skeleton_tests` (5): üres sheet → `Anchor`; 3-critical szekvencia →
  `Anchor→Interlock→BandInsert`; non-interlock 2. critical → `BandInsert`; szerep független a queue
  méretétől; determinizmus ismétlésen.
- `tests/sparrow_sheet_skeleton.rs`: skeleton on geometria **byte-azonos** a skeleton off-fal +
  role-count > 0 + ≥1 `Anchor`; skeleton off → role-count (0,0,0).
- Teljes `vrs_solver` suite zöld (21 ok blokk, 0 failed); default-off no-regression.

## 6. DoD → Evidence

| DoD | Evidence |
| --- | --- |
| `assign_role` determinisztikus Anchor→Interlock→BandInsert | `sheet_skeleton.rs::skeleton_tests::three_critical_sequence_is_anchor_interlock_bandinsert` |
| üres sheet → Anchor; darabszám-független | `empty_sheet_first_critical_is_anchor`, `role_is_independent_of_queue_size` |
| default off → byte-azonos; gate on placement-invariáns | `tests/sparrow_sheet_skeleton.rs::skeleton_records_roles_without_changing_placement` |
| diagnosztika a tényleges viselkedésről | `io.rs` `bpp_skeleton_*_count`, `bpp_reduction.rs::build_critical_aware_seed` role-count |
| nincs NFP / bbox shortcut / 3+3 hack | `sheet_skeleton.rs::assign_role` (topológia+profil, nincs darabszám) |

## 7. Verdikt

**PASS — alapréteg.** A skeleton state + role-besorolás kész, tesztelt, gated, és bizonyítottan
placement-invariáns (Q54A nem mozgat semmit). Ez a váz, amelyre a Q54B (clearance-aware candidate),
Q54C (overlap-toleráns separation), Q54D (free-space + band-insert) és Q54E (LV8 proof) épül.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-18T21:35:10+02:00 → 2026-06-18T21:38:21+02:00 (191s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q54a_skeleton_state_role_assignment.verify.log`
- git: `main@7df600c`
- módosított fájlok (git status): 24

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |  5 ++
 .../src/optimizer/sparrow/bpp_reduction.rs         | 38 ++++++++++++++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  1 +
 rust/vrs_solver/tests/sparrow_contour_features.rs  | 60 ++++++++++++++--------
 scripts/check.sh                                   |  8 +++
 5 files changed, 92 insertions(+), 20 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/tests/sparrow_contour_features.rs
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
?? rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
?? rust/vrs_solver/tests/sparrow_sheet_skeleton.rs
```

<!-- AUTO_VERIFY_END -->
