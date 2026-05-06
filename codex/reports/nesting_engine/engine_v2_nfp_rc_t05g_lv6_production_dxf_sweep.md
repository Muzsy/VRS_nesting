# T05g — LV6 Production DXF Sweep / CGAL Geometry Robustness Audit

**Dátum:** 2025-05-05
**Fázis:** T05g (LV6 production DXF audit)
**Állapot:** PASS

---

## 1. Státusz

**PASS**

Minden cél teljesült:
- T05f regression: PASS
- 11/11 LV6 DXF inventory készült
- 7 NFP pair fixture készült
- CGAL sidecar: 7/7 success
- T07 correctness: 7/7 PASS
- output_holes előfordult: igen (pair_06)
- Hole boundary sampling aktív: igen (pair_06)

---

## 2. Regressziós ellenőrzés

**T05f output-hole-os eset:** `real_work_dxf_holes_pair_02`

```
CGAL: status=success, output_holes=1, runtime=9.45ms
T07: PASS, FP=0, FN=0
     HOLES_AWARE: 1 hole(s) parsed from holes_i64
     boundary_holes=true, hole_boundary_samples=2
     hole_boundary_penetration_max_mm=0.01
```

**REGRESSZIO: PASS** ✓

---

## 3. LV6 DXF Inventory összesítő

| Metrika | Érték |
|---------|-------|
| total_dxf | 11 |
| import_ok | 11 |
| import_ok_with_holes | 11 |
| import_ok_outer_only | 0 |
| import_failed | 0 |
| preflight_ok | 0 |
| preflight_failed | 11 |
| with_holes | 11 |
| with_text | 11 |
| quantity_parsed | 11/11 |

**Kulcs megfigyelések:**
- Mind a 11 LV6 DXF hole-os geometriát tartalmaz (nem outer-only)
- Mind a 11 tartalmaz TEXT/MTEXT entity-t (feliratozás)
- Preflight chain mind a 11-nél TypeError-ral elbukik — ez várt viselkedés, mert a preflight role resolver nem ismeri fel a nem-standard layer neveket ("Gravír", "Gravir", "jel")
- Az LV6 DXF-ek NEM a `CUT_OUTER`/`CUT_INNER` konvenciót használják
- A darabszám mind a 11 fájlból sikeresen kinyerhető a fájlnévből

**Quantity parsing:**
```
Quantities: [1, 3, 6, 7, 8, 9, 9, 12, 12, 22, 23]
```

**Layer/Entity összesítő:**
```
Layers: ['0', 'Gravir', 'Gravír', 'jel']
Entity types: ['ARC', 'CIRCLE', 'LINE', 'LWPOLYLINE', 'MTEXT', 'TEXT']
```

---

## 4. DXF részletes inventory (import kategória alapján)

| File | Outer verts | Holes | Hole verts | Area mm² | Qty | Notes |
|------|-------------|-------|------------|----------|-----|-------|
| LV6_01513_9db REV6 | 28 | 2 | 24 | 7,007 | 9 | holes_on_layer0 |
| LV6_01745_6db L módosítva CSB REV10 | 181 | 15 | 180 | 324,888 | 6 | complex |
| Lv6_08089_1db REV2 MÓDOSÍTOTT! | 143 | 9 | 210 | 135,234 | 1 | |
| Lv6_13779_22db Módósitott NZ REV2 | 95 | 7 | 89 | 98,960 | 22 | |
| Lv6_14511_23db REV1 | 16 | 2 | 24 | 3,697 | 23 | smallest |
| Lv6_15202_8db REV0 Módosított N.Z. | 144 | 9 | 298 | 158,237 | 8 | |
| Lv6_15205_12db REV0 Módosított N.Z. | 144 | 9 | 284 | 143,018 | 12 | |
| Lv6_15264_9db REV2 +2mm | 124 | 19 | 305 | 413,430 | 9 | most holes |
| Lv6_15270_12db REV2 | 181 | 17 | 204 | 324,888 | 12 | |
| Lv6_15372_3db REV0 | 228 | 4 | 48 | 293,303 | 3 | most outer verts |
| Lv6_16656_7db REV0 | 192 | 16 | 184 | 328,855 | 7 | |

---

## 5. Raw importer vs Preflight összehasonlítás

### Raw importer (vrs_nesting.dxf.importer)
- Mind a 11 DXF: `IMPORT_OK_WITH_HOLES`
- Strategy: layer="0" összes ringje → legnagyobb területű = outer, többi = hole
- A "Gravír" layer további hole ringeket adhat hozzá

### Preflight chain (T1→T2→T4)
- Mind a 11 DXF: `PREFLIGHT_FAILED` (TypeError)
- Ok: `dxf_preflight_role_resolver` nem ismeri fel a "Gravír"/"Gravir"/"jel" layer neveket
- A `CUT_OUTER`/`CUT_INNER`/`MARKING` canonical layer neveket várja
- Ez várt viselkedés: a preflight chain célja a szabványos konvenció, az LV6 DXF-ek nem szabványosak

---

## 6. NFP Pair Fixture összesítő

7 fixture készült, mind valódi LV6 DXF-ből:

| Pair ID | Part A | Part B | Pair type |
|---------|--------|--------|-----------|
| lv6_production_dxf_pair_01 | Lv6_15372_3db (228v,4h) | Lv6_14511_23db (16v,2h) | complex vs simple |
| lv6_production_dxf_pair_02 | Lv6_16656_7db (192v,16h) | LV6_01513_9db (28v,2h) | complex vs simple |
| lv6_production_dxf_pair_03 | Lv6_15270_12db (181v,17h) | Lv6_13779_22db (95v,7h) | complex vs medium |
| lv6_production_dxf_pair_04 | Lv6_15202_8db (144v,9h) | Lv6_15205_12db (144v,9h) | mid vs mid |
| lv6_production_dxf_pair_05 | LV6_01745_6db (181v,15h) | Lv6_15264_9db (124v,19h) | complex vs many-holes |
| lv6_production_dxf_pair_06 | Lv6_15264_9db (124v,19h) | Lv6_14511_23db (16v,2h) | many-holes vs simple |
| lv6_production_dxf_pair_07 | Lv6_15270_12db (181v,17h) | LV6_01513_9db (28v,2h) | complex vs simple |

---

## 7. CGAL Sidecar eredmények

| Pair | Status | Runtime ms | Input holes A | Input holes B | Output outer verts | Output holes | Output hole verts |
|------|--------|-----------|--------------|---------------|-------------------|--------------|-------------------|
| lv6_production_dxf_pair_01 | success | 8.01 | 4 | 2 | 209 | 0 | 0 |
| lv6_production_dxf_pair_02 | success | 10.36 | 16 | 2 | 251 | 0 | 0 |
| lv6_production_dxf_pair_03 | success | 26.50 | 17 | 7 | 298 | 0 | 0 |
| lv6_production_dxf_pair_04 | success | 58.16 | 9 | 9 | 195 | 0 | 0 |
| lv6_production_dxf_pair_05 | success | 44.57 | 15 | 19 | 374 | 0 | 0 |
| lv6_production_dxf_pair_06 | **success** | **10.31** | **19** | **2** | **128** | **2** | **12** |
| lv6_production_dxf_pair_07 | success | 8.33 | 17 | 2 | 242 | 0 | 0 |

**Leglassabb:** pair_04 — 58.16ms (9 holes + 9 holes, CGAL Minkowski)
**Legnagyobb output_outer_vertices:** pair_05 — 374
**output_holes előfordult:** igen — pair_06 (2 output holes)

---

## 8. T07 Correctness eredmények

| Pair | Verdict | FP | FN | boundary_holes | outer_samples | hole_samples | outer_penetration | hole_penetration | Notes |
|------|---------|----|----|----------------|---------------|--------------|-------------------|-----------------|-------|
| lv6_production_dxf_pair_01 | PASS | 0 | 0 | false | 400 | 0 | 0.0 | 0.0 | outer-only output |
| lv6_production_dxf_pair_02 | PASS | 0 | 0 | false | 400 | 0 | 0.0 | 0.0 | outer-only output |
| lv6_production_dxf_pair_03 | PASS | 0 | 0 | false | 400 | 0 | 0.0 | 0.0 | outer-only output |
| lv6_production_dxf_pair_04 | PASS | 0 | 0 | false | 400 | 0 | 0.0 | 0.0 | outer-only output |
| lv6_production_dxf_pair_05 | PASS | 0 | 0 | false | 400 | 0 | 0.0 | 0.0 | outer-only output |
| lv6_production_dxf_pair_06 | **PASS** | **0** | **0** | **true** | **390** | **10** | **0.0** | **0.01** | **HOLES_AWARE active** |
| lv6_production_dxf_pair_07 | PASS | 0 | 0 | false | 400 | 0 | 0.0 | 0.0 | outer-only output |

**HOLES_AWARE containment:** pair_06 az egyetlen, ahol aktív (2 output holes).
**hole_boundary collision count:** 10/10 — minden hole boundary minta collider.

---

## 9. FP/FN táblázat

| Pair | T07 Verdict | FP | FN | FP rate | FN rate |
|------|-------------|----|----|---------|---------|
| lv6_production_dxf_pair_01 | PASS | 0 | 0 | 0.0 | 0.0 |
| lv6_production_dxf_pair_02 | PASS | 0 | 0 | 0.0 | 0.0 |
| lv6_production_dxf_pair_03 | PASS | 0 | 0 | 0.0 | 0.0 |
| lv6_production_dxf_pair_04 | PASS | 0 | 0 | 0.0 | 0.0 |
| lv6_production_dxf_pair_05 | PASS | 0 | 0 | 0.0 | 0.0 |
| lv6_production_dxf_pair_06 | PASS | 0 | 0 | 0.0 | 0.0 |
| lv6_production_dxf_pair_07 | PASS | 0 | 0 | 0.0 | 0.0 |
| **Összesen** | **7/7 PASS** | **0** | **0** | **0.0** | **0.0** |

---

## 10. Legfontosabb megfigyelések

### 1. LV6 DXF non-standard layer konvenció
Az LV6 DXF-ek NEM a `CUT_OUTER`/`CUT_INNER` konvenciót használják. Minden kontúr a "0" layeren van. A legnagyobb területű kontúr az outer, a többi a hole. Ez a T05e tapasztalatával egyezik (lv8jav DXF-ek is non-standard).

### 2. Hole boundary mintavételezés aktív
A pair_06 (Lv6_15264_9db vs Lv6_14511_23db): 19 holes vs 2 holes → 2 output holes → T07 HOLES_AWARE containment aktív. 10 hole boundary minta, mind collider.

### 3. CGAL output hole megőrzés
A pair_06 az első LV6 eset, ahol az NFP output ténylegesen tartalmaz hole-t. Ez azt mutatja, hogy a CGAL Minkowski összeg topológiája függ a part geometriától — alacsonyabb hole-számú part_b esetén megmaradnak a hole-ok.

### 4. Preflight chain nem illeszkedik az LV6 DXF-ekre
A T2 role resolver a `CUT_OUTER`/`CUT_INNER`/`MARKING` canonical neveket várja. Az LV6 DXF-ek "Gravír", "Gravir", "jel" layer neveket használnak — emiatt a preflight chain TypeError-ral elbukik. Ez nem a CGAL vagy T07 hibája.

### 5. LV6 = mind hole-os
Ellentétben az LV8 DXF-ekkel (ahol 1 hole-os DXF volt a 12-ből), az LV6 mintában mind a 11 DXF hole-os. Ez valószínűleg a gyártási komplexitás különbsége.

---

## 11. Módosított fájlok

```
scripts/experiments/audit_production_dxf_holes.py   ÚJ — LV6 DXF inventory audit
scripts/experiments/extract_lv6_production_dxf_nfp_pairs.py  ÚJ — LV6 NFP pair extractor
tmp/reports/nfp_cgal_probe/lv6_production_dxf_inventory.json  ÚJ
tmp/reports/nfp_cgal_probe/lv6_production_dxf_inventory.md    ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_01.json  ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_02.json  ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_03.json  ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_04.json  ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_05.json  ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_06.json  ÚJ
tests/fixtures/nesting_engine/nfp_pairs/lv6_production_dxf_pair_07.json  ÚJ
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_01.json  ÚJ (CGAL output)
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_02.json  ÚJ (CGAL output)
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_03.json  ÚJ (CGAL output)
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_04.json  ÚJ (CGAL output)
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_05.json  ÚJ (CGAL output)
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_06.json  ÚJ (CGAL output)
tmp/reports/nfp_cgal_probe/lv6_production_dxf_pair_07.json  ÚJ (CGAL output)
```

---

## 12. Futtatott parancsok

```bash
# T05f regression
bash scripts/build_nfp_cgal_probe.sh
tools/nfp_cgal_probe/build/nfp_cgal_probe \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_02.json \
  --algorithm reduced_convolution \
  --output-json tmp/reports/nfp_cgal_probe/real_work_dxf_holes_pair_02.json
cargo run --bin nfp_correctness_benchmark -- \
  --fixture tests/fixtures/nesting_engine/nfp_pairs/real_work_dxf_holes_pair_02.json \
  --nfp-source external_json \
  --nfp-json tmp/reports/nfp_cgal_probe/real_work_dxf_holes_pair_02.json \
  --sample-inside 1000 --sample-outside 1000 --sample-boundary 400 --output-json

# LV6 inventory audit
python3 scripts/experiments/audit_production_dxf_holes.py \
  "/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv6 jav"

# LV6 pair extraction
python3 scripts/experiments/extract_lv6_production_dxf_nfp_pairs.py \
  "/home/muszy/projects/VRS_nesting/samples/real_work_dxf/0014-01H/lv6 jav"

# CGAL sidecar (7 fixtures)
tools/nfp_cgal_probe/build/nfp_cgal_probe --fixture ... --algorithm reduced_convolution --output-json ...

# T07 correctness (7 fixtures)
cargo run --bin nfp_correctness_benchmark -- --nfp-source external_json --nfp-json ... --sample-inside 1000 --sample-outside 1000 --sample-boundary 400 --output-json
```

---

## 13. Blocker / Limitációk

1. **Preflight chain nem illeszkedik az LV6 DXF-ekre**: A T2 role resolver explicit `CUT_OUTER`/`CUT_INNER` neveket vár. Az LV6 DXF-ek non-standard layereit ("Gravír", "Gravir", "jel") nem ismeri fel. Emiatt a preflight chain `PREFLIGHT_FAILED` minden LV6 DXF-re. Ez nem CGAL/T07 hiba — a DXF-ek nem standard konvenciót használnak.

2. **Nincs production integráció**: CGAL változatlanul prototípus/reference tool. T08 integráció nem történt.

---

## 14. Következő javasolt lépés

**T05h**: LV6 preflight role resolver kiterjesztés — a T2 role resolver floppy layer-name matching hozzáadása ("Gravír"/"Gravir" → CUT_INNER, "jel" → MARKING), hogy az LV6 DXF-ek is átmenjenek a preflight láncon. Ez nem érinti a CGAL-t vagy T07-et.

**Alternatíva**: LV7 production DXF sweep — további LV7 minták vizsgálata, hogy megértsük, mennyire elterjedtek a non-standard layer konvenciók.
