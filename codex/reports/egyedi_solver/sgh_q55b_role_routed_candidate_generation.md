# SGH-Q55B — Role átadása a critical candidate generátornak

## 1. Executive summary

A `SkeletonRole` mostantól **routing-bemenet**, nem utólagos címke: a `try_admit_critical` megkapja a
`role`-t, és a co-movable candidate-generálást **role szerint szűri** — `Anchor` → sheet-edge anchor,
`Interlock` → neighbour feature-pár, `BandInsert` → (egyelőre) minden, a Q55C band-generátor csatlakozási
pontja. Role-by-role diagnosztika (`bpp_role_*_generated/accepted`).

**Őszinte határ:** az `Anchor` (első critical) jelenleg a **direct-insert** úton helyeződik el (üres
sheet, a part befér), tehát a co-movable role-routing az anchorra **0** candidate-et lát (`role gen
a/i/b = 0/13/168` a 6-big mérésen). A sheet-edge anchor **primary-vá** tétele (a direct-insert
helyett/elé) a **Q55C** scope-ja. A Q55B a routing-infrastruktúrát adja; az interlock/band routing él.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `optimizer/sparrow/bpp_reduction.rs` | `try_admit_critical(... , role: Option<SkeletonRole>)`; a hívó (`build_critical_aware_seed`) átadja a Q54A-ban számolt role-t; a co-movable loop `role_match` szűrése (Anchor→sheet_edge, Interlock→neighbour, Band/None→all) + `role_accept` per-role accepted |
| `io.rs` | `bpp_role_{anchor,interlock,band_insert}_{generated,accepted}` + `bpp_role_candidate_rejection_summary` (additív; a `bpp_interlock_candidates_*` Q48-mezők érintetlenek) |
| `tests/sparrow_role_routing.rs` (új) | a per-role counts kitöltődnek a skeleton úton; skeleton off → 0; no-regression |

## 3. Hogyan működik

- **Aláírás-bővítés (additív):** `role: Option<SkeletonRole>` — `None` (skeleton off) = a Q53/Q54
  viselkedés. A `build_critical_aware_seed` a Q54A `assign_role` eredményét adja át.
- **Routing:** a co-movable loop filtere `role_match(seed) && (skeleton_on || refine_success)`. Az
  Anchor csak `sheet_edge` target candidate-eket, az Interlock csak neighbour-driven candidate-eket lát.
- **Diagnosztika:** a role-szűrt seed-szám a per-role `*_generated`-be; a commit a `*_accepted`-be.

## 4. Guardrailek

- CDE a collision truth; acceptance csak final-validation feasible. Nincs NFP / bbox-corner primary /
  hardcoded 3+3; a routing a role-ból + a candidate target-típusból dolgozik (nem darabszám).
- Continuous rotation érintetlen.
- Default off → byte-azonos (22-blokkos suite zöld); a skeleton út csak gate ON mellett.
- Scope-fegyelem: `bpp_reduction.rs` (aláírás + routing) + `io.rs` (additív mezők) + új teszt.

## 5. Tesztek

- `tests/sparrow_role_routing.rs`: skeleton ON → `bpp_role_interlock_generated + bpp_role_band_insert_generated > 0`,
  valid (0 pair), used-sheet no-regression; skeleton OFF → 0 role-routing.
- Köztes mérés (6-big): sp0 → 2 tábla / 3+3 (proof megvan), sp5 → 2/tábla (változatlan); role gen
  a/i/b = 0/13/168 (az anchor a direct úton → 0).
- Teljes `vrs_solver` suite zöld (22 ok blokk, 0 failed).

## 6. DoD → Evidence

| DoD | Evidence |
| --- | --- |
| role átadás (additív aláírás) | `try_admit_critical(... role: Option<SkeletonRole>)`; hívó + teszt-hívó None |
| role-routing a co-movable ágban | `role_match` filter (Anchor→sheet_edge, Interlock→neighbour) |
| role-by-role diagnosztika | `bpp_role_*_generated/accepted`; `role_routing_fills_per_role_counts...` |
| default off → byte-azonos | 22-blokkos suite zöld; skeleton off → 0 role-routing |
| anchor → sheet-edge | **részleges**: a co-movable ág route-ol, de az anchor a direct-insert úton megy → a sheet-edge anchor primary a Q55C |

## 7. Verdikt

**PASS — routing-infrastruktúra.** A role valódi routing-bemenet; az interlock/band candidate-generálás
role-szerinti, a per-role diagnosztika él, no-regression. A nyitott pont (őszintén): az **anchor** a
direct-insert úton helyeződik el, így a sheet-aware sheet-edge anchor (Q55A) nem primary az anchorra —
ezt a **Q55C** köti be (band-insert generátor + az anchor sheet-edge primary), majd a Q55D/E/F.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-19T21:44:17+02:00 → 2026-06-19T21:47:29+02:00 (192s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.verify.log`
- git: `main@25f6466`
- módosított fájlok (git status): 27

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |   9 ++
 .../src/optimizer/sparrow/bpp_reduction.rs         |  32 +++-
 .../sparrow/feature_candidate_generator.rs         | 172 ++++++++++++++-------
 3 files changed, 151 insertions(+), 62 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
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
?? codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md
?? codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.verify.log
?? rust/vrs_solver/tests/sparrow_role_routing.rs
?? rust/vrs_solver/tests/sparrow_sheet_edge_anchor.rs
```

<!-- AUTO_VERIFY_END -->
