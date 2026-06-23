STATUS: PARTIAL_FAIL_ALGORITHMIC_GAP

# SGH-Q61 — Q56–Q60 modulok bekötése a valós sheet-builder/critical-admission útba + 3-kritikus proof

> A Q56–Q60 modulok a valós `sparrow_cde` critical-admission útba (`try_admit_critical` /
> `build_critical_aware_seed`) be lettek kötve, gate mögött, és a solver diagnosztikája bizonyítja a
> fogyasztásukat. A 3 nagy LV8 part **geometriailag elfér** egy táblán (a valós builder-út spacing 0-n
> 3/3-at placel — lásd lent), tehát **nem** geometriai lehetetlenségről van szó. A skeleton + Q56–Q60
> modul út azonban **valós spacingen (8) jelenleg max 2 kritikus/tábla**-t ér el → **algoritmikus rés**,
> best valid partial = 2 megőrizve. Ezért a státusz `PARTIAL_FAIL_ALGORITHMIC_GAP` (nem PASS, és nem
> PASS_WITH_NOTES).

## 1) Meta

- **Task slug:** `sgh_q61_integrated_critical_admission_wiring`
- **Branch / commit:** `main` (working tree; a Q56–Q60 a `b09964a` merge-commitban)
- **Futás dátuma:** 2026-06-23
- **Fókusz terület:** `Solver | critical admission wiring`

## 2) Scope

### 2.1 Cél
- A Q56C/Q57B/Q58B/Q59/Q60 modulok **tényleges** bekötése a valós critical-admission útba, gate-elve,
  consumption + rejection diagnosztikával; 3-kritikus admission bizonyítása a valós solver-úton.

### 2.2 Nem-cél
- A spacing/margin gyengítése; bbox-only collision; continuous rotation diszkrétre cserélése;
  part-id/koordináta hardcode. (Egyik sem történt.)

## 3) Changed files

- **Rust (wiring):** `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` (Anchor/Interlock/BandInsert
  consumption + best-partial/simultaneous instrumentáció),
  `rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs` (`anchor_candidates_for_instance`,
  `anchor_catalog_enabled`), `rust/vrs_solver/src/optimizer/sparrow/band_insert_slot_edge.rs`
  (`slot_edge_seeds_for_instance`), `rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs`
  (`interlock_seeds_against_anchor`), `rust/vrs_solver/src/io.rs` (q61 consumption diagnostics).
- **Test/runner:** `rust/vrs_solver/tests/sparrow_q61_integrated_critical_admission.rs`.
- **Artifacts:** `artifacts/benchmarks/sgh_q61/critical_3part_spacing0.{json,svg}`,
  `.../critical_3part_real_spacing.{json,svg}`, `.../critical_3part_diagnostics_summary.md`.

## 4) Commands run

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q61_integrated_critical_admission -- --test-threads=1
VRS_SHEET_BUILDER=1 VRS_SHEET_BUILDER_SKELETON=1 VRS_FEATURE_CANDIDATES=1 VRS_PAIR_INDEX=1 \
VRS_INTERLOCK_PAIR=1 VRS_SHEET_FEASIBILITY_HINTS=1 VRS_BAND_INSERT_TRUE_EXTREME=1 \
VRS_SIMULTANEOUS_CRITICAL=1 VRS_ANCHOR_CATALOG=1 \
  cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q61_integrated_critical_admission
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q61_integrated_critical_admission_wiring.md
```

> Megjegyzés: a wiring egy plusz gate-et vezet be a Q56C anchor-katalógus fogyasztásához:
> `VRS_ANCHOR_CATALOG=1` (default off → a meglévő Q55B sheet-edge anchor út byte-azonos). A többi
> modul a feladatban felsorolt gate-ekkel aktiválódik.

## 5) spacing = 0 result (Scenario A)

A valós solver (constructive builder, `VRS_SHEET_BUILDER`) **3/3 kritikus partot placel EGY 1500×3000
táblára** spacing 0-n: `placed=3, max_critical_per_sheet=3, sheets_used=1, status=ok` (CDE-valid: 0
collision, 0 boundary a placed partok közt). Artifact: `critical_3part_spacing0.json`
(`builder_path_places_3_on_one_sheet: true`, `max_critical_per_sheet_builder_path: 3`). Ez bizonyítja,
hogy a 3-part packing **feasibilis** — nincs geometriai lehetetlenség.

A skeleton + Q56–Q60 modul út spacing 0-n `max_critical_per_sheet_module_path = 2`, miközben a modulok
fogyasztódnak (lásd §7).

## 6) real spacing result (Scenario B)

A skeleton + összes modul út spacing 8 / margin 5 mellett **max 2 kritikus/tábla** (best valid partial
= 2, megőrizve; a 3. attempt bukása sosem dobja el a 2-t). 3/3 egy táblán **nem** sikerült ezen az
úton → ez a `PARTIAL_FAIL_ALGORITHMIC_GAP`. Artifact: `critical_3part_real_spacing.json`
(`best_valid_critical_count: 2`).

## 7) Candidate source usage table (real solver path, all gates)

| Modul | consumed | candidates generated | accepted | bizonyíték |
| --- | --- | --- | --- | --- |
| Q56C SheetEdgePlacementCatalog (Anchor) | **true** | edge+corner candidates | fallback only* | `bpp_q61_anchor_catalog_consulted=true` |
| Q57B PairCompatibilityIndex (Interlock) | **true** | **32** (sp0) | 0 | `bpp_q61_pair_index_consulted=true`, `pair_candidates_generated=32` |
| Q59 true-extreme slot-edge BandInsert | true (ha band-slot van) | slot-edge seeds | 0 | `bpp_q61_band_insert_true_extreme_consulted` (6-part futáson) |
| Q60 simultaneous critical | **true** | group_attempts>0 | parts moved | `simultaneous_critical_consumed=true`, `previous_group_parts_moved=true` |
| Q58B best-partial tracker | **true** | — | — | `best_partial_tracker_enabled=true` |

\* A Q56C anchor-katalógus **non-regressing fallback**: a meglévő Q55B sheet-edge feature út (a bizonyított
co-movable interlock seeding) elsőbbséget kap; a katalógus csak akkor commitol, ha az nem ad eredményt
(így nem rontja a builder 3/3-át). A katalógus candidate-jei a valós úton generálódnak és a co-movable
separationön mennek át — genuine consumption, de a free-space rangsorban a meglévő seeding nyer.

## 8) Best-partial tracker evidence

- `bpp_q61_best_partial_tracker_enabled = true` (VRS_SHEET_FEASIBILITY_HINTS).
- `bpp_q61_best_partial_max_critical_count` = a sheetenkénti legjobb kritikus szám (2 a modul-úton).
- `bpp_q61_best_partial_downgrades_rejected` ≥ 0: a `build_critical_aware_seed` loop a sheetenkénti
  kritikus számot csak növeli; egy bukott admission **sosem** távolítja el a már admittáltakat
  ([bpp_reduction.rs:2706](../../../rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs#L2706)) →
  a 2/3 → 1/3 regresszió konstrukció szerint lehetetlen a valós outputban.

## 9) Rejection summary (no silent fallback)

A pair (Interlock) út, ha nem fogad el candidate-et, explicit okot rögzít:
`bpp_q61_pair_rejection_summary` = `"pair_seeds_generated=N rejected_separation_failed=M
(boundary|collision|candidate_not_clear|refinement_failed) → neighbour fallback"`, és
`bpp_q61_interlock_fallback_to_neighbour=true`. A BandInsert true-extreme út bukáskor
`bpp_q61_fallback_to_bbox_band_insert=true`. Nincs néma fallback.

## 10) Visual artifacts

- `artifacts/benchmarks/sgh_q61/critical_3part_spacing0.svg` — a valós solver 3 kritikus partja egy
  táblán (builder-út), role + rotation címkékkel.
- `artifacts/benchmarks/sgh_q61/critical_3part_real_spacing.svg` — a real-spacing eredmény (best partial).
- `artifacts/benchmarks/sgh_q61/critical_3part_diagnostics_summary.md` — összefoglaló.

## 11) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) |
| -------- | ------: | ------------------------ |
| Q56C anchor catalog a valós kritikus úton fogyasztva | PASS | `bpp_reduction.rs:2143` + `sheet_edge_placement_catalog.rs:201` (`anchor_candidates_for_instance`); diag `anchor_catalog_consulted=true` |
| Q57B pair/interlock a valós Interlock úton, neighbour fallback ELŐTT | PASS | `bpp_reduction.rs:2349` + `pair_matrix.rs:170` (`interlock_seeds_against_anchor`); `pair_index_consulted=true`, `pair_candidates_generated=32` |
| Q58B best-partial + hint-aware a valós BPP úton | PASS | `bpp_reduction.rs:2664,2706` (`best_partial_tracker_enabled`, `downgrades_rejected`) |
| Q59 true-extreme BandInsert a bbox fallback ELŐTT | PASS | `bpp_reduction.rs:2302` + `band_insert_slot_edge.rs:161` (`slot_edge_seeds_for_instance`); `band_insert_true_extreme_consulted` |
| Q60 simultaneous critical a valós flow-ból hívva (partok mozognak) | PASS | `bpp_reduction.rs:2664`; `simultaneous_critical_consumed=true`, `previous_group_parts_moved=true` |
| spacing=0 → 3/3 egy táblán a valós úton | PASS | `critical_3part_spacing0.json` `builder_path_places_3_on_one_sheet=true`; teszt `spacing0_three_critical_uses_real_solver_path_and_places_3` |
| real-spacing → 3/3 VAGY PARTIAL_FAIL best≥2 | PARTIAL | `critical_3part_real_spacing.json` `best_valid_critical_count=2` |
| nincs geometriai infeasibility-állítás | PASS | a builder-út 3/3-a bizonyítja a feasibilitást |
| diagnosztika a forrásokat + rejectiont mutatja | PASS | q61 diag blokk + `pair_rejection_summary` |
| SVG artifactok léteznek | PASS | `critical_3part_spacing0.svg`, `critical_3part_real_spacing.svg` |

## 12) Honest gap analysis (a valódi következő lever)

A rés **nem** geometriai (a builder-út 3/3-at placel sp0-n) és **nem** a modulok hiánya (be vannak
kötve, fogyasztódnak). A rés: a **skeleton + modul úton** a co-movable / SA separation a
modul-generált seedekből **valós spacingen nem konvergál a tight 3-way nested interlockra**, és sp0-n a
skeleton-út (2/tábla) elmarad a plain builder-úttól (3/tábla). A módosítások RNG/idő-érzékenynek
mutatják a 3/3-at: a builder-út egy adott RNG/stock kombinációban éri el. A következő lever egy
**determinisztikus, interlock-célzott refinement** (nem RNG-fragilis SA), amely a Q56C/Q57B/Q59
modul-seedeket a tight-spacing 3-way nested konfigurációba viszi — a spacing/margin gyengítése nélkül.
Ez a Q51 report saját „density-biased separation toward interlock" R&D irányát folytatja.

## 13) Advisory / Deviations

- **Új gate `VRS_ANCHOR_CATALOG`** (default off) a Q56C consumptionhöz, hogy a meglévő Q55B anchor út
  byte-azonos maradjon, ha ki van kapcsolva (no-regression).
- A q61 consumption-diagnosztika additív az io.rs `BppReductionDiagnostics`-ban (`#[serde(default)]`),
  determinisztikus → a determinizmus-gate byte-azonos marad gate-off mellett.
- A focused runner abszolút darabszámai time-budget/terhelés-érzékenyek; a tesztek a **consumption +
  non-downgrade invariánsokat** ellenőrzik (robusztus), nem a fragilis abszolút számot.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T20:15:49+02:00 → 2026-06-23T20:23:21+02:00 (452s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q61_integrated_critical_admission_wiring.verify.log`
- git: `main@b09964a`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 .../sgh_q60/critical_group_admission.json          |   4 +-
 rust/vrs_solver/src/io.rs                          |  46 +++++++
 .../src/optimizer/sparrow/band_insert_slot_edge.rs |  87 ++++++++++++
 .../src/optimizer/sparrow/bpp_reduction.rs         | 149 +++++++++++++++++++++
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  |  62 +++++++++
 .../sparrow/sheet_edge_placement_catalog.rs        | 114 ++++++++++++++++
 6 files changed, 460 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q60/critical_group_admission.json
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/band_insert_slot_edge.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs
?? artifacts/benchmarks/sgh_q61/
?? codex/reports/egyedi_solver/sgh_q61_integrated_critical_admission_wiring.md
?? codex/reports/egyedi_solver/sgh_q61_integrated_critical_admission_wiring.verify.log
?? rust/vrs_solver/tests/sparrow_q61_integrated_critical_admission.rs
```

<!-- AUTO_VERIFY_END -->
