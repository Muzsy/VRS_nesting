# SGH-Q54D — Free-space-preserving score + band-insert + sheet-close guard

## 1. Executive summary

A makró-stratégia: a critical elhelyezés ne csak valid legyen, hanem a **következő** critical-nak is
hagyjon hasznos, edge-connected szabad teret. Három elem: (1) **free-space proxy** — durva occupancy
grid, a legnagyobb **edge-connected** szabad komponens területe; (2) **candidate-rangsor** — a
co-movable admission a feasible eredmények közül azt tartja meg, amelyik a **legnagyobb** szabad sávot
hagyja (nem az első feasible-t), korlátozott számú feasible-en (a separation-budget védelme); (3)
**sheet-close guard** — a skeleton úton a critical fázis tovább nyitva marad (frontier 4 vs 2), hogy a
band-insert harmadik nagy is esélyt kapjon. A `BandInsert` szerep a Q54A besorolásból jön.

**Köztes mérés (6× `Lv8_11612`):** spacing 0 → **2 tábla / 3+3** (a Q51 proof a skeleton úton
reprodukálva ✓); spacing 5 → **még 2/tábla** (`band_insert = 0`). A free-space-megőrzés + sheet-close
guard önmagában **nem** oldja meg a tight-spacing 3-way packinget — őszinte köztes finding (mint
Q52/Q53). A teljes proof + full276 no-regression: **Q54E**.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `optimizer/sparrow/sheet_skeleton.rs` | `largest_edge_connected_free_area` (occupancy grid + connected-components, csak border-érintő komponens) + `freespace_cell_mm` (`VRS_SKELETON_FREESPACE_CELL_MM`, default 50); unit teszt |
| `optimizer/sparrow/bpp_reduction.rs` | `sheet_freespace_score` + `commit_feature_admission` helperek; a co-movable loop a skeleton úton a **legjobb free-space-ű** feasible-t tartja (max 4 feasible); sheet-close guard (`critical_frontier = skeleton ? 4 : 2`) |

## 3. Hogyan működik

- **Free-space proxy:** a sheet durva rácsán (≈50 mm) az admittált bboxok celláit foglaltnak jelöli; a
  szabad cellák connected-componensei közül a legnagyobb **border-érintő** komponens területe a score.
  A belső, körülzárt zsebek kizárva (a nagy 3. part egy ilyenbe nem fér). Rangsoroló proxy — a CDE az
  igazság.
- **Candidate-rangsor:** a skeleton úton a co-movable admission **nem** az első feasible-t commitolja,
  hanem a legnagyobb maradék-sávot hagyót (max 4 feasible-en, a separation-budget védelmében).
- **Sheet-close guard:** `critical_frontier = 4` a skeleton úton — a band-insert harmadik nagy is
  esélyt kap a tighter interlock-pár hibái után, ahelyett hogy a sheet korán lezárulna.

## 4. Guardrailek

- CDE a collision truth; a free-space score **csak rangsoroló proxy**, nem collision/validáció.
- Nincs NFP, nincs bbox collision shortcut a clearance-hez; continuous rotation érintetlen.
- Nincs `part_id` hack, **nincs hardcoded 3+3**, **nincs darabszám-előrejelzés** — a sheet-close guard
  a free-space geometriájából + a frontier-ből dönt.
- Default off → byte-azonos (21-blokkos suite zöld); a skeleton út csak `VRS_SHEET_BUILDER_SKELETON`.
- Scope-fegyelem: `sheet_skeleton.rs` (új fn) + `bpp_reduction.rs` (helperek + rangsor + guard).

## 5. Tesztek

- `sheet_skeleton.rs::skeleton_tests::freespace_picks_largest_edge_connected_band_and_excludes_enclosed`:
  üres sheet ≈ teljes terület; egy elválasztó fal → a legnagyobb band ≈ a nagyobbik fél; körülzárt
  belső zseb **kizárva**.
- `tests/sparrow_sheet_skeleton.rs`: a skeleton út valid + role + feature-path fut + no-regression
  (a Q54C-ben frissítve; a Q54D rangsor/guard mellett is zöld).
- Teljes `vrs_solver` suite zöld (21 ok blokk, 0 failed).

## 6. DoD → Evidence

| DoD | Evidence |
| --- | --- |
| free-space proxy: nagy összefüggő sáv > apró rés; körülzárt kizárva | `freespace_picks_largest_edge_connected_band_and_excludes_enclosed` |
| candidate-rangsor a maradéktér szerint | `bpp_reduction.rs` `sheet_freespace_score` + best-of-feasible loop |
| sheet-close guard (nincs korai zárás) | `critical_frontier = skeleton ? 4 : 2` |
| default off → byte-azonos | 21-blokkos suite zöld; minden a `skeleton_on` mögött |
| nincs hardcoded 3+3 / darabszám-előrejelzés | a guard free-space + frontier alapú |

## 7. Verdikt

**PASS mint mechanizmus; a tight-spacing 3/tábla NYITOTT (őszinte).** A free-space-megőrző rangsor +
sheet-close guard + band-insert besorolás kész és tesztelt. **Spacing 0:** 2 tábla / 3+3 (a Q51 proof
a skeleton úton reprodukálva). **Spacing 5:** még 2/tábla (`band_insert = 0`) — a free-space-rangsor +
guard önmagában nem elég a tight 3-way packinghez. Megfigyelés a következő lépéshez: a band-insert
jelenleg csak **besorolás** (Q54A role); a candidate-generálás még **nem szerep-specifikus** (a 3. nagy
nem külön a megmaradt alsó/felső sávba, táblaélhez igazítva generálódik). A teljes LV8 proof + full276
no-regression a **Q54E** — a verdikt ott lesz végleges (várhatóan: sp0 PASS, sp5 őszinte negatív,
full276 no-regression).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-19T16:09:08+02:00 → 2026-06-19T16:12:17+02:00 (189s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.verify.log`
- git: `main@465505e`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../sgh_q54c_overlap_tolerant_separation.md        |  32 +++---
 .../sgh_q54d_freespace_band_insert.md              |  34 +++---
 .../src/optimizer/sparrow/bpp_reduction.rs         | 123 ++++++++++++++++----
 .../src/optimizer/sparrow/sheet_skeleton.rs        | 126 +++++++++++++++++++++
 rust/vrs_solver/tests/sparrow_sheet_skeleton.rs    |  52 +++++----
 5 files changed, 288 insertions(+), 79 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/codex_checklist/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
 M codex/codex_checklist/egyedi_solver/sgh_q54d_freespace_band_insert.md
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
 M rust/vrs_solver/tests/sparrow_sheet_skeleton.rs
?? codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
?? codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.verify.log
?? codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md
?? codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.verify.log
```

<!-- AUTO_VERIFY_END -->
