# SGH-Q55A — Sheet-aware edge-anchor rotation

## 1. Executive summary

Az `Anchor` szerepű nagy critical alkatrész tábla-élhez igazítása mostantól **sheet-aware**: a part
domináns élét a sheet **long** ÉS **short** edge irányához igazítja, **180° flip** variánsokkal,
**continuous** szöggel (a part ferde élét a táblaélhez forgatva, pl. ~88.3°, nem 90-snap). A korábbi
`sheet_alignment_rotation_seed` egyetlen part-tengely-seedet adott, a sheet arányát figyelmen kívül
hagyva; a Q55A rangsorolt sheet-aware rotációs jelölthalmazt ad.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `optimizer/sparrow/feature_candidate_generator.rs` | `sheet_aware_anchor_rotations` (long/short edge irány a `SheetShape` width/height alapján + 180° flip, continuous part → nyers seed, discrete → `resolve_seed_rotation` snap) + `push_sheet_edge_anchors` (a 4 él-anchor egy rotációra); a `sheet_edge_candidates` ezeket hívja az egyetlen part-axis seed helyett |
| `tests/sparrow_sheet_edge_anchor.rs` (új) | a sheet-aware seed-halmaz span long+short + flip + continuous |

## 3. Hogyan működik

- **Sheet long/short irány:** `sheet.width >= sheet.height ? (0°,90°) : (90°,0°)` — 1500×3000 esetén a
  long edge függőleges (90°), a short edge vízszintes (0°).
- **Rotációs jelölthalmaz:** minden domináns élre `{long_dir, short_dir} × {0°, 180° flip}`, a part
  élszögéhez viszonyítva: `wrap(target + flip − edge_angle)`. Continuous part → a nyers (folytonos)
  szög (a downstream refine találja a pontos ~88.3°-ot); discrete → `resolve_seed_rotation` snap az
  allowed-ra. Deduplikált.
- **Anchor-push:** rotációnként a 4 él-anchor (a meglévő horizontal/vertical bal-jobb / alsó-felső
  logika), `sheet_edge_*` alignment_kind-dal (= anchor side).

## 4. Guardrailek

- **Continuous rotation marad continuous** — a sheet-aware seed continuous partnál nem snap; a refine
  finomít. A teszt bizonyítja: a ferde-élű part seed rotációja nem 90-szorzó.
- CDE a collision truth; a sheet-aware rotáció csak seed — a CDE/refine dönt. Nincs NFP, nincs
  bbox-corner primary, nincs hardcoded `Lv8`/3+3.
- Default off → byte-azonos: a `sheet_edge_candidates` a feature-first úton fut, ami a Q53D /
  `VRS_SHEET_BUILDER_SKELETON` gate mögött van (mindkettő default off) → a default út nem hívja.
  22-blokkos suite zöld.
- Scope-fegyelem: egy forrásfájl (`feature_candidate_generator.rs`) + új teszt.

## 5. Tesztek

- `tests/sparrow_sheet_edge_anchor.rs::sheet_edge_anchor_is_sheet_aware_long_and_short_with_flips`:
  ferde-élű hosszúkás continuous part + 1500×3000 sheet → sheet-edge anchor candidate-ek, amelyek
  rotációi (a) span ≥2 orientáció (long+short), (b) tartalmaznak continuous (nem 90-snap) szöget,
  (c) tartalmaznak 180° flip variánst.
- A meglévő Q53B sheet-edge alignment teszt zöld (a refaktor megőrzi a viselkedést).
- Teljes `vrs_solver` suite zöld (22 ok blokk, 0 failed); default-off no-regression.

## 6. DoD → Evidence

| DoD | Evidence |
| --- | --- |
| seed-halmaz span long+short + flip | `sheet_edge_anchor_is_sheet_aware...` (norm ≥2 + has_flip) |
| a refined/seed rotáció continuous (nem snapping) | ugyanaz a teszt (continuous seed assert); `resolve_seed_rotation` continuous ág |
| default off → byte-azonos | 22-blokkos suite zöld; a sheet_edge_candidates a gate-elt feature úton |
| nincs NFP / bbox-corner primary / hardcoded | `sheet_aware_anchor_rotations` (geometria-alapú, sheet width/height) |

## 7. Verdikt

**PASS — alapréteg.** A sheet-edge anchor rotáció sheet-aware (long+short+flip+continuous). A teljes
CDE-clear anchor + a 3/tábla a role-routinggal (Q55B) + band-inserttel (Q55C) + szigorított free-space
(Q55D) + guard (Q55E) együtt áll össze; a végső proof a Q55F.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-19T21:24:49+02:00 → 2026-06-19T21:27:59+02:00 (190s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.verify.log`
- git: `main@25f6466`
- módosított fájlok (git status): 22

**git diff --stat**

```text
 .../sparrow/feature_candidate_generator.rs         | 172 ++++++++++++++-------
 1 file changed, 112 insertions(+), 60 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
?? canvases/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md
?? canvases/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md
?? canvases/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md
?? canvases/egyedi_solver/sgh_q55d_strict_freespace_preservation.md
?? canvases/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md
?? canvases/egyedi_solver/sgh_q55f_runner_primary_acceptance.md
?? codex/codex_checklist/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md
?? codex/codex_checklist/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md
?? codex/codex_checklist/egyedi_solver/sgh_q55c_band_insert_candidate_generator.md
?? codex/codex_checklist/egyedi_solver/sgh_q55d_strict_freespace_preservation.md
?? codex/codex_checklist/egyedi_solver/sgh_q55e_geometric_sheet_close_guard.md
?? codex/codex_checklist/egyedi_solver/sgh_q55f_runner_primary_acceptance.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55a_sheet_aware_edge_anchor_rotation.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55b_role_routed_candidate_generation.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55c_band_insert_candidate_generator.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55d_strict_freespace_preservation.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55e_geometric_sheet_close_guard.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q55f_runner_primary_acceptance.yaml
?? codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.md
?? codex/reports/egyedi_solver/sgh_q55a_sheet_aware_edge_anchor_rotation.verify.log
?? rust/vrs_solver/tests/sparrow_sheet_edge_anchor.rs
```

<!-- AUTO_VERIFY_END -->
