# SGH-Q54C — Overlap-toleráns critical separation (continuous rotation)

## 1. Executive summary

A Q53 0-accepted **separation-szintű gyökerének** javítása. A Q53D feature-first ág két dologon bukott:
(1) a co-movable lépés a `feature_seeds.iter().filter(|s| s.refine_success)`-szel **eldobta** a
nem-azonnal-clear seedeket (a Q54B clearance-aware seedek többségét) — a `refine_feature_candidates`
not-clear-nél azonnal feladott; (2) az overlap-toleráns separator (`density_biased_separate`, Q52,
rotation-correct) csak a `VRS_ADMISSION_DENSITY_BIAS` knob mögött volt aktív. A Q54C a **skeleton gate**
mögött mindkettőt feloldja: a feature-first ág nem szűr `refine_success`-re (az overlap-toleráns
separator tisztítja a seedet), és a `density_biased_separate` default súllyal (2.0) aktív — a critical
set együtt mozog/forog continuous rotation-nel a CDE-feasible állapotig.

**Köztes mérés (6× `Lv8_11612`, spacing 5):** a feature admission most **2 candidate-et elfogad**
(`bpp_feature_candidates_accepted = 2`, `attempts = 16`) — szemben a **Q53 0-accepted**-jével. A
`max big/sheet` még **2** (nem 3): a mikró-gyökér (accepted > 0) javítva, de a **3/tábla** a free-space-
megőrző elhelyezést + band-insertet (Q54D) igényli. Ez a "kettő egyben" terv szerinti: a mikró (B+C)
bizonyított, a makró (A+D) hozza a 3-at.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `optimizer/sparrow/bpp_reduction.rs` | `try_admit_critical`: a `feature_first` a skeleton gate alatt is aktív (Q53D gate-ek nélkül is); a co-movable ág **nem** szűr `refine_success`-re a skeleton úton (`take(24)`); `try_seeded_critical_separation`: `w_density = bias.max(skeleton ? 2.0 : 0.0)` → density_biased_separate a skeleton úton |
| `tests/sparrow_sheet_skeleton.rs` | a Q54A placement-invariancia teszt frissítve a Q54C valós viselkedésére: valid + role rögzítve + **feature-path fut** (`attempts > 0`) + no-regression a used-sheet count-on |

## 3. Hogyan működik

- **Nincs refine-clear előszűrés (skeleton út):** a Q54B clearance-aware (akár még overlapos) seedek
  mind a `try_seeded_critical_separation`-be kerülnek; az overlap-toleráns separator tisztít.
- **Overlap-toleráns separator:** `density_biased_separate` (Q52) — lexikografikus clear-first, density
  ranking, spacing-collision gap-tartó shape, **continuous rotation** (`density_rotation_candidates`,
  a Q52 rotation-fix). A critical set együtt mozog/forog; a final acceptance csak
  `final_validation_tracker().is_feasible()`.
- **Gate:** `VRS_SHEET_BUILDER_SKELETON` aktiválja a teljes feature-first utat (a candidate-generálással
  együtt). Default off → a Q53D gate-ek döntenek → byte-azonos.

## 4. Guardrailek

- CDE a collision truth; acceptance csak final-validation feasible.
- Nincs NFP, nincs bbox shortcut; **continuous rotation** a separator rotation-setjéből (nincs snap).
- Default off → byte-azonos (a 21-blokkos suite zöld); a skeleton út csak gate ON mellett.
- Scope-fegyelem: egy forrásfájl (`bpp_reduction.rs`) + a meglévő integrációs teszt frissítése.

## 5. Tesztek

- `tests/sparrow_sheet_skeleton.rs::skeleton_admission_is_valid_records_roles_and_runs_feature_path`:
  skeleton ON → valid (0 pair, 0 boundary), role-ok rögzítve (≥1 Anchor), **feature admission fut**
  (`attempts > 0`), used-sheet count nem regresszál; skeleton OFF → role-count (0,0,0).
- `bpp_reduction.rs::q50_tests::density_biased_separate_resolves_overlap_into_interlock`: az
  overlap-toleráns separator overlapból CDE-clear interlockot ad (unit).
- Teljes `vrs_solver` suite zöld (21 ok blokk, 0 failed).

## 6. DoD → Evidence

| DoD | Evidence |
| --- | --- |
| not-clear seed nem bukik azonnal (overlap-toleráns) | `bpp_reduction.rs` `take(24)` szűrés nélkül + `density_biased_separate`; köztes mérés: 0→2 accepted |
| critical set együtt, continuous rotation | `try_seeded_critical_separation` → `density_biased_separate` (w≥2.0, `density_rotation_candidates`) |
| default off → byte-azonos | a 21-blokkos suite zöld; a feature_first skeleton-off ágon a Q53D gate-ek döntenek |
| valós separation (nem azonnali feladás) | `skeleton_admission_..._runs_feature_path` (`attempts > 0`) |

## 7. Verdikt

**PASS — a separation-szintű 0-accepted gyökér javítva.** A skeleton út feature admission-je most
**elfogad** candidate-eket (2 vs Q53 0), overlap-toleráns separation-nel, continuous rotation-nel. A
`max big/sheet` = 2 (még nem 3) — a 3/tábla **nem** a mikró-separation, hanem a free-space-megőrző
makró-stratégia (anchor/interlock úgy üljön, hogy a 3.-nak marad edge-connected sáv) kérdése: **Q54D**.
A teljes LV8 proof: **Q54E**.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-19T06:24:06+02:00 → 2026-06-19T06:27:14+02:00 (188s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.verify.log`
- git: `main@465505e`
- módosított fájlok (git status): 5

**git diff --stat**

```text
 .../sgh_q54c_overlap_tolerant_separation.md        | 32 ++++++-------
 .../src/optimizer/sparrow/bpp_reduction.rs         | 30 +++++++++++--
 rust/vrs_solver/tests/sparrow_sheet_skeleton.rs    | 52 +++++++++++-----------
 3 files changed, 69 insertions(+), 45 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/codex_checklist/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/tests/sparrow_sheet_skeleton.rs
?? codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
?? codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.verify.log
```

<!-- AUTO_VERIFY_END -->
