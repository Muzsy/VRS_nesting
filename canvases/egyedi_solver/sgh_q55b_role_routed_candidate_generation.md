# Q55B — Role átadása a critical candidate generátornak

## Goal

A Q54-ben a `SkeletonRole` létezik, de **nem irányítja** a candidate-generálást (utólagos címke). A
Q55B a role-t valódi **routing-bemenetté** teszi: a `try_admit_critical` megkapja a role-t + a skeleton
state-et + a maradék critical profilokat, és **role-specifikus candidate-útvonalakat** futtat.

```
Anchor      → sheet-edge anchor candidates (Q55A)
Interlock   → anchor-targeted feature candidates (a meglévő feature-pár generátor)
BandInsert  → free-space band candidates (Q55C)
```

## Háttér

A Q54E megfigyelése: a band-insert csak besorolás, a candidate-generálás minden szerepre ugyanaz
(általános feature-seed). A Q55B a routing-infrastruktúrát adja, amelyre a Q55A (anchor) és Q55C
(band-insert) generátorok csatlakoznak. A Q55B önmagában még nem hozza a 3/tábla-t — a routing-vázat
építi, role-by-role diagnosztikával.

Érintett valós kódpontok:

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
  - `try_admit_critical` (aláírás bővítés: role + skeleton_state + remaining_critical_profiles),
    `build_critical_aware_seed` (a hívó: a role-t már számolja a Q54A bekötés)
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — `SkeletonRole`, `SheetSkeletonState`
- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs` — role-specifikus belépők
- `rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs` — `PartShapeProfile` (remaining profiles)
- `rust/vrs_solver/src/io.rs`, `diagnostics.rs`

## Globális guardrailek

- Continuous rotation marad continuous; nincs NFP / bbox-corner primary; nincs hardcoded `Lv8`/3+3.
- CDE a collision truth; final acceptance csak CDE-valid.
- Gated (`VRS_SHEET_BUILDER_SKELETON`), default off → no-regression.
- A role **nem** vezethet darabszám-előrejelzéshez; a routing a szerepből + a sheet-geometriából dolgozik.
- Scope-fegyelem: `bpp_reduction.rs` (aláírás + routing) + `feature_candidate_generator.rs` (belépők).

## Feladat

### Role átadás

- `try_admit_critical` kapja: `role: Option<SkeletonRole>`, `skeleton_state: Option<&SheetSkeletonState>`,
  `remaining_critical_profiles: &[Rc<PartShapeProfile>]` (a még el nem helyezett critical-ok profilja).
- A `build_critical_aware_seed` (a Q54A-ban már számolja a role-t) átadja ezeket.

### Role-specifikus útvonalak

- `Anchor` → Q55A sheet-edge anchor candidate-ek (primary).
- `Interlock` → a meglévő anchor-targeted feature-pár candidate-ek.
- `BandInsert` → Q55C free-space band candidate-ek (a Q55B-ben még stub/hook, a Q55C tölti).

### Diagnosztika (kötelező)

```
anchor_candidates_generated / anchor_candidates_accepted
interlock_candidates_generated / interlock_candidates_accepted
band_insert_candidates_generated / band_insert_candidates_accepted
role_candidate_rejection_summary
```

### DoD

- A `try_admit_critical` role-tudatos: a role szerint választ candidate-forrást (a Q55A/C csatlakozási
  pontokkal); a role-by-role diagnosztika kitöltődik.
- Unit/integrációs teszt: a role-routing a megfelelő ágat választja (anchor → sheet-edge; interlock →
  feature-pár; band → band-hook), és a diagnosztika role-onként számol.
- Default off → byte-azonos.

## Runner / verification

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml role_rout`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml skeleton`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q55b_role_routed_candidate_generation.md`

## Rollback

- Ha a role-routing regressziót okoz, gate off → a Q54 egységes feature-path érintetlen.
- Az aláírás-bővítés additív (Option-ök None-nal = a régi viselkedés).
