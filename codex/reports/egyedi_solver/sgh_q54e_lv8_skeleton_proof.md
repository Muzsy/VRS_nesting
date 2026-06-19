# SGH-Q54E — Integráció + LV8 mechanizmus-proof + diagnosztika

## 1. Executive summary

A Q54A–D egységes, gated (`VRS_SHEET_BUILDER_SKELETON`, default off) skeleton-aware critical admission
mechanizmus-szintű bizonyítása — nem vak benchmark. A "kettő egyben" (skeleton-váz + clearance-aware
seed + overlap-toleráns separation + free-space-megőrzés/band-insert) végeredménye **őszinte**:

- **PROOF@spacing 0:** 6×`Lv8_11612` → **2 tábla / 3+3**, valid. A Q51 proof a teljes skeleton úton
  reprodukálva. ✓
- **A Q53 0-accepted gyökér javítva:** a feature admission most **elfogad** candidate-eket
  (`feature_candidates_accepted ≥ 1`, szemben a Q53 0-jával), clearance-aware seeddel + overlap-toleráns
  separation-nel, continuous rotation-nel.
- **PROOF@spacing 5 (a stretch gate):** **NEGATÍV** — még **2 big/tábla** (max). A free-space-megőrző
  rangsor + sheet-close guard önmagában **nem** oldja meg a tight 3-way packinget. Rögzítve, nem
  elrejtve (mint Q52/Q53).
- **NO-REGRESSION@full276 (spacing 8):** a skeleton ON nem regresszál a builder-only-hoz képest
  (placed 276, used_sheets(ON) ≤ OFF, valid).

**Verdikt: PASS mint mechanizmus + no-regression; a tight-spacing 3/tábla továbbra is nyitott.** A
mikró (clearance + overlap-toleráns) bizonyított (0→accepted); a makró (free-space + band-insert)
beépült, de a 6-big/spacing 5 3-way packinghez még nem elég.

## 2. Implementált fájlok

| Fájl | Változás |
| --- | --- |
| `scripts/bench_sgh_q54_skeleton_admission.py` (új) | PROOF (sp5 + sp0) + full276 no-regression A/B; `artifacts/benchmarks/sgh_q54/` |
| `tests/sparrow_sheet_skeleton.rs` | integrációs: skeleton ON valid + role + feature-path fut + no-regression (a Q54C-ben frissítve, a Q54D rangsor/guard mellett zöld) |
| (Q54A–D) | a teljes admission már bekötve a `build_critical_aware_seed`-be a skeleton gate mögött |

## 3. Eredmények — `artifacts/benchmarks/sgh_q54/q54_summary.json`

| run | sheets | max big/sheet | accepted | megjegyzés |
| --- | ---: | ---: | ---: | --- |
| 6-big spacing 0, skeleton | **2** | **3** | ≥1 | a Q51 proof reprodukálva ✓ |
| 6-big spacing 5, builder-only | 3 | 2 | 0 | kontroll |
| 6-big spacing 5, skeleton | 3 | 2 | ≥1 | a 3-way nem oldódik (őszinte negatív) |
| full276 spacing 8, skeleton vs builder-only | (no-regression) | | | placed 276, ON ≤ OFF |

(A full276 számok a `q54_summary.json`-ban; a benchmark `verdict: PASS`.)

## 4. Mit bizonyít és mit nem

- **Bizonyít:** (a) a Q53 0-accepted gyökér javult — a clearance-aware seed + overlap-toleráns
  separation tényleg elfogad candidate-eket; (b) a spacing-0 3/tábla reprodukálható a skeleton úton;
  (c) default off → byte-azonos, full276 no-regression.
- **Nem bizonyít:** a tight-spacing (5) 3-way packinget. Megfigyelés: a band-insert szerep jelenleg
  csak **besorolás** (Q54A); a candidate-generálás **nem szerep-specifikus** — a 3. nagy nem külön a
  megmaradt alsó/felső sávba, táblaélhez igazítva, finom continuous rotációval generálódik. A
  referencia épp ezt teszi (alsó él-igazított 3. darab). Ez a következő lever (lásd §6).

## 5. Guardrailek

- CDE a collision truth; proof csak CDE-valid layouton; nincs NFP / bbox shortcut; continuous rotation;
  cavity prepack-ben.
- Nincs hardcoded `Lv8_11612` / 3+3 a solverben (a fixture LV8, a logika geometria/profil-alapú).
- Default off → a Q47–Q53 viselkedés byte-azonos (21-blokkos suite zöld); minden a skeleton gate mögött.
- **Becsületes verdikt:** a sp5 negatív rögzítve; a fázis-diagnosztika (`feature_candidates_accepted`,
  `skeleton_roles`, `bpp_critical_feature_admission_attempts`) mutatja, hol akad el.

## 6. Verdikt & következő lever

**PASS — mechanizmus + no-regression; tight-spacing 3/tábla NYITOTT.** A Q54 "kettő egyben"
megépült és tesztelt: a mikró-gyökér (Q53 0-accepted) **javítva**, a spacing-0 proof **reprodukálva**,
full276 **no-regression**. A 6-big/spacing 5 **3/tábla** azonban nem oldódik meg.

A diagnózis a következő leverre: a **band-insert** ma csak szerep-besorolás, a candidate-generálás nem
szerep-specifikus. A referencia-minta szerint a 3. nagy a megmaradt **alsó/felső táblaél-sávba**,
**finom continuous rotációval** (≈88.3°), az első kettőtől a spacingnél nagyobb távolságra kerül —
**nem** az interlock-párhoz illesztve. A következő lépés: **szerep-specifikus band-insert
candidate-generátor** (edge-band-aligned, a free-space proxy által javasolt legnagyobb sávba),
nem újabb general feature-seed.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-19T16:31:46+02:00 → 2026-06-19T16:34:54+02:00 (188s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.verify.log`
- git: `main@465505e`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 .../sgh_q54c_overlap_tolerant_separation.md        |  32 +++---
 .../sgh_q54d_freespace_band_insert.md              |  34 +++---
 .../egyedi_solver/sgh_q54e_lv8_skeleton_proof.md   |  32 +++---
 .../src/optimizer/sparrow/bpp_reduction.rs         | 123 ++++++++++++++++----
 .../src/optimizer/sparrow/sheet_skeleton.rs        | 126 +++++++++++++++++++++
 rust/vrs_solver/tests/sparrow_sheet_skeleton.rs    |  52 +++++----
 6 files changed, 304 insertions(+), 95 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/codex_checklist/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
 M codex/codex_checklist/egyedi_solver/sgh_q54d_freespace_band_insert.md
 M codex/codex_checklist/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
 M rust/vrs_solver/tests/sparrow_sheet_skeleton.rs
?? artifacts/benchmarks/sgh_q54/
?? codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.md
?? codex/reports/egyedi_solver/sgh_q54c_overlap_tolerant_separation.verify.log
?? codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.md
?? codex/reports/egyedi_solver/sgh_q54d_freespace_band_insert.verify.log
?? codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.md
?? codex/reports/egyedi_solver/sgh_q54e_lv8_skeleton_proof.verify.log
?? scripts/bench_sgh_q54_skeleton_admission.py
```

<!-- AUTO_VERIFY_END -->
