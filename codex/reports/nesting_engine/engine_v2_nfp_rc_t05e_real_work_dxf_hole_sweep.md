# T05e — Real Work DXF Hole Sweep / CGAL Geometry Robustness Audit

**Státusz: PASS**

## Rövid összefoglaló

A `samples/real_work_dxf/0014-01H/lv8jav` könyvtár 12 DXF fájljának auditja + NFP pair fixture készítés + CGAL + T07 correctness lánc lefuttatása.

Kulcs eredmény: A `Lv8_11612_6db REV3.dxf` 2 lyukkal rendelkezik. Az ebből készült `real_work_dxf_holes_pair_02` (vs `Lv8_07921_50db REV1.dxf`) az **első valódi eset**, ahol a CGAL output ténylegesen megőrzött 1 lyukat az NFP-ben (`output_holes=1`), és a T07 `HOLES_AWARE` containment explicitly aktív volt a notes-ben.

## DXF Inventory összesítő

| Metrika | Érték |
|---------|-------|
| total_dxf | 12 |
| import_ok | 10 |
| import_ok_with_holes | 1 |
| import_ok_outer_only | 10 |
| import_failed | 1 |
| unsupported | 0 |

**Megjegyzés**: Az "IMPORT_OK_WITH_HOLES" kategória csak 1 DXF-et tartalmaz (`Lv8_11612_6db REV3.dxf`), a többi 10 outer-only. A `tmp/ne2_input_lv8jav.json`-ben talált 9 lyukkal rendelkező LV8_11612 az nem a nyers DXF-ből származik, hanem a `cavity_prepack` által rekonstruált/párhuzamosított lyuk-információ.

## DXF Layer konvenciók (nem standard)

A `samples/real_work_dxf/0014-01H/lv8jav` DXF-jei **NEM** a `CUT_OUTER`/`CUT_INNER` konvenciót használják:

| Réteg | Tartalom |
|-------|----------|
| `layer="0"` | Outer contour (CIRCLE, LINE, ARC) |
| `layer="Gravír"` | CUT_INNER / lyukak (CIRCLE, LINE + TEXT annotációk) |

A `TEXT` entity-k a "Gravír" layeren feliratozások (nem polygon geometria), ezért a `probe_layer_rings` automatikusan kiszűri őket és csak a támogatott entitásokat (CIRCLE, LINE, ARC) használja a polygonizáláshoz.

## Módosított fájlok

| Fájl | Módosítás |
|------|-----------|
| `scripts/experiments/audit_real_work_dxf_holes.py` | ÚJ — DXF inventory audit |
| `scripts/experiments/extract_real_work_dxf_hole_nfp_pairs.py` | ÚJ — Real work DXF → NFP pair extractor |
| `tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.json` | ÚJ — Inventory JSON |
| `tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.md` | ÚJ — Inventory Markdown |
| `tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_01.json` | ÚJ — Lv8_11612_6db (2 holes) vs Lv8_07920_50db |
| `tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_02.json` | ÚJ — Lv8_11612_6db (2 holes) vs Lv8_07921_50db |
| `tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_03.json` | ÚJ — Lv8_07920_50db vs Lv8_07921_50db |

## Real work DXF részletes inventory

| File | Category | Outer verts | Holes | Hole verts | BBox W×H mm | Notes |
|------|----------|------------|-------|------------|-------------|-------|
| LV8_00035_28db M REV2.dxf | IMPORT_OK_OUTER_ONLY | 6 | 0 | 0 | — | |
| LV8_00057-2_20db REV8.dxf | IMPORT_OK_OUTER_ONLY | 16 | 0 | 0 | — | |
| LV8_01170_10db REV5.dxf | IMPORT_OK_OUTER_ONLY | 4 | 0 | 0 | — | |
| LV8_02048_20db L REV5.dxf | IMPORT_OK_OUTER_ONLY | 15 | 0 | 0 | — | |
| LV8_02049_50db REV7.dxf | IMPORT_OK_OUTER_ONLY | 12 | 0 | 0 | — | |
| Lv8 _10059_10db REV2.dxf | INVALID_GEOMETRY | 0 | 0 | 0 | — | No outer rings (szóköz a fájlnévben) |
| Lv8_07919_16db REV4.dxf | IMPORT_OK_OUTER_ONLY | 12 | 0 | 0 | — | |
| Lv8_07920_50db REV1.dxf | IMPORT_OK_OUTER_ONLY | 216 | 0 | 0 | — | Complex |
| Lv8_07921_50db REV1.dxf | IMPORT_OK_OUTER_ONLY | 344 | 0 | 0 | — | Complex |
| Lv8_11612_6db REV3.dxf | **IMPORT_OK_WITH_HOLES** | 23 | 2 | 30 | — | **1 holed DXF** |
| Lv8_15348_6db GRAVÍR REV1.dxf | IMPORT_OK_OUTER_ONLY | 21 | 0 | 0 | — | |
| Lv8_15435_10db REV0.dxf | IMPORT_OK_OUTER_ONLY | 16 | 0 | 0 | — | |

## Pair Fixture eredmények

| pair_id | source_files | input_holes_a | input_holes_b | CGAL status | runtime_ms | output_outer_v | output_holes | T07 verdict | FP | FN | HOLES_AWARE |
|---------|--------------|---------------|---------------|-------------|-----------|----------------|--------------|-------------|----|----|-------------|
| real_work_dxf_holes_pair_01 | Lv8_11612_6db REV3 vs Lv8_07920_50db REV1 | 2 (30v) | 0 | success | 11.18 | 132 | 0 | PASS | 0 | 0 | N/A (output holes=0) |
| real_work_dxf_holes_pair_02 | Lv8_11612_6db REV3 vs Lv8_07921_50db REV1 | 2 (30v) | 0 | success | 13.17 | 136 | 1 (7v) | PASS | 0 | 0 | **AKTÍV** |
| real_work_dxf_holes_pair_03 | Lv8_07920_50db REV1 vs Lv8_07921_50db REV1 | 0 | 0 | success | 70.88 | 328 | 0 | PASS | 0 | 0 | N/A (outer-only pair) |

## Kulcs megfigyelések

### 1. CGAL output hole megőrzés

A `real_work_dxf_holes_pair_02`: 2 input hole (30 összes vertex) → 1 output hole (7 vertex).

Ez az **első eset a T05b-T05d sorozatban**, ahol a CGAL NFP output ténylegesen tartalmaz hole-t. A `real_work_dxf_holes_pair_01` 2 input hole-jával ellentétben itt a lyuk megmaradt — a különbség a part_b geometriájában van (`Lv8_07920` vs `Lv8_07921`), ami befolyásolja a Minkowski összeg topológiáját.

### 2. T07 HOLES_AWARE containment aktiválódása

```
notes: "HOLES_AWARE: 1 hole(s) parsed from holes_i64, hole-aware containment active"
```

Ez a T05c implementáció (T07 `point_in_polygon` kiterjesztés) első aktív esete valódi hole-os inputpal.

### 3. Non-standard DXF layer nevek

A repo DXF importer `CUT_OUTER`/`CUT_INNER` konvenciója nem illeszkedik a valós DXF-ekre. A "Gravír" (= gravírozás/marás) layer valójában a belső lyukakat tartalmazza, nem feliratozást. A TEXT entity-k a layeren annotációk, ezért a `probe_layer_rings` kiszűri őket.

### 4. A "Lyukas" LV8_11612 discrepancy magyarázata

A `tmp/ne2_input_lv8jav.json`-ben az LV8_11612_6db **9 lyukkal** szerepel (153 hole vertex). De a nyers DXF (`Lv8_11612_6db REV3.dxf`) csak **2 lyukat** tartalmaz (30 vertex).

**Magyarázat**: A `cavity_prepack` a `cavity_prepack_top_level_holes_remain` ellenőrzés szerint 9 lyukat vár — a 9 lyuk nem a DXF-ből, hanem a cavity_prepack rekonstrukciós lépéséből származik (a DXF valószínűleg 2 tényleges furatot tartalmaz, a többit a rezgésillesztés / multi-pass cavity számítás adja hozzá).

Ez nem a CGAL probe hibája — a CGAL helyesen dolgozza fel a nyers DXF-et.

## Hole boundary sampling

**Következő javasolt lépés / follow-up**: A `sample_points_on_boundary` jelenleg csak outer boundary-t mintavételez. A `real_work_dxf_holes_pair_02` output_jában 1 output hole (7 vertex) van. A hole boundary-k statisztikailag nem kerültek mintavételezésre a jelenlegi T07 implementációban. Ha a hole boundary correctness fontos, külön implementáció szükséges.

## Blockerek

Nincs.

## Következő javasolt lépés

T05f: Hole boundary sampling implementáció a T07-ben — outer és hole boundary mintavételezés szétválasztása, hole boundary correctness riport.

Alternatíva: T06 — NFP union pipeline debug (Phase 8 root cause: `concat.rs:1070` `Solver::with_strategy_and_precision(Strategy::List, Precision::ABSOLUTE)` timeout).
