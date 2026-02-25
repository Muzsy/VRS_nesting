# canvases/nesting_engine/nfp_real_dxf_pairs_proof.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_real_dxf_pairs_proof.md`
> **TASK_SLUG:** `nfp_real_dxf_pairs_proof`
> **Terület (AREA):** `nesting_engine`

---

# F2-2 P0 — “3 valós DXF alakzat-pár” futtatható bizonyíték (DXF→int ring→NFP golden)

## 🎯 Funkció

A F2-2 backlog DoD-ból hiányzó “valós DXF készlet 3 alakzat-párjára helyes NFP” pontot **objektív, futtatható** bizonyítékkal le kell fedni.

A repó demo DXF készlete jelenleg:
- 1 db pozitív stock: `samples/dxf_demo/stock_rect_1000x2000.dxf`
- 1 db pozitív part (ARC/SPLINE + legalább 1 hole): `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
- 1 db negatív (nyitott lánc): `samples/dxf_demo/part_chain_open_fail.dxf` (importnak FAIL)

Ezért a “3 alakzat-pár” bizonyítékot a **pozitív** DXF-ekből, **valós DXF-ből exportált** (skálázott i64) ringekkel adjuk:
- Pár #1: stock × part (outer-only)
- Pár #2: part × stock (outer-only)
- Pár #3: part × part (outer-only)

Megjegyzés: a part DXF-ben hole-ok léteznek és ezt a smoke validálja, de a jelenlegi NFP regressziós fixture formátum outer-only. A holes-os NFP külön P0 (holes support).

Nem cél:
- F2-2 core algoritmus újranyitása
- holes támogatás bevezetése
- új dependency hozzáadása
- más fázisok (F2-3/F2-4)

---

## 🧠 Fejlesztési részletek

### Kötelező olvasmány / szabályok (prioritás)
1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md` (SCALE=1_000_000)
6. `docs/nesting_engine/json_canonicalization.md` (canonical JSON elvek)
7. `samples/dxf_demo/README.md` + a 3 DXF
8. `vrs_nesting/sparrow/input_generator.py` (DXF→raw_outer_points útvonal)
9. `rust/nesting_engine/tests/nfp_regression.rs` (fixture schema)
10. `scripts/check.sh` (quality gate)

Ha bármelyik hiányzik: STOP, pontos útvonallal jelezni.

---

### Kötelező elvek (nem alkuképes)
- **Determinista export**: DXF→outer ring→skálázott i64 → canonical ring (CCW + lex start) legyen egzakt.
- **Golden NFP**: a 3 real-dxf fixture-ben `expected_nfp` + `expected_vertex_count` kitöltött és tesztelhető.
- **DXF ↔ fixture kötés**: smoke ellenőrizze, hogy a fixture `polygon_a/polygon_b` tényleg a DXF importból jön (canonical összevetés).
- **Nem self-fulfilling CI**: “expected builder” jellegű tooling lehet, de nem fut automatikusan a gate-ben.

---

### Megoldási stratégia
1) Létrehozunk 3 db *real-dxf* NFP fixture-t a `poc/nfp_regression/` alá:
   - `real_dxf_pair_01_stock_x_part.json`
   - `real_dxf_pair_02_part_x_stock.json`
   - `real_dxf_pair_03_part_x_part.json`

2) Készül egy determinisztikus export script:
   - `scripts/export_real_dxf_nfp_pairs.py`
   - DXF import: a repó meglévő útvonalaival (`vrs_nesting.sparrow.input_generator.build_sparrow_inputs`)
   - skálázás: SCALE=1_000_000, round-half-away-from-zero (Decimal, stdlib)
   - canonical ring: CCW + lex start

3) Készül egy minimális Rust helper bin a golden expected generáláshoz (manual / task-run):
   - `rust/nesting_engine/src/bin/nfp_fixture.rs`
   - stdin: fixture JSON (polygon_a/polygon_b)
   - stdout: computed NFP canonical ring + vertex count (stable path)
   - Ezt a task run során használjuk az `expected_nfp` kitöltésére.

4) Készül egy gate-smoke, ami objektív bizonyítékot ad:
   - `scripts/smoke_real_dxf_nfp_pairs.py`
   - Ellenőrzi:
     - DXF import megvan (ezdxf), part-nál hole-ok léteznek
     - a 3 fixture `polygon_a/polygon_b` = DXF-ből exportált canonical i64 ring
     - a `nfp_fixture` bin kiszámolja az NFP-t, és az = fixture `expected_nfp` (canonical ring)
   - A smoke bekerül `scripts/check.sh`-ba, így `verify.sh` is lefedi.

---

### Érintett fájlok

**Új:**
- `scripts/export_real_dxf_nfp_pairs.py`
- `scripts/smoke_real_dxf_nfp_pairs.py`
- `rust/nesting_engine/src/bin/nfp_fixture.rs`
- `poc/nfp_regression/real_dxf_pair_01_stock_x_part.json`
- `poc/nfp_regression/real_dxf_pair_02_part_x_stock.json`
- `poc/nfp_regression/real_dxf_pair_03_part_x_part.json`
- `codex/codex_checklist/nesting_engine/nfp_real_dxf_pairs_proof.md`
- `codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md`

**Módosul:**
- `scripts/check.sh` (új smoke meghívása + chmod lista bővítés)

---

## 🧪 Tesztállapot

### DoD
- [x] 3 db valós DXF-ből exportált alakzat-pár fixture létezik `poc/nfp_regression/` alatt (outer-only)
- [x] `scripts/smoke_real_dxf_nfp_pairs.py` PASS:
  - DXF→canonical i64 ring egyezik a fixture `polygon_*` mezőkkel
  - a part DXF ténylegesen tartalmaz hole-t (evidence)
  - computed NFP == expected_nfp (3/3)
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_real_dxf_pairs_proof.md` PASS

---

## 🌍 Lokalizáció
Nem releváns.

---

## 📎 Kapcsolódások
- F2-2 canvas: `canvases/nesting_engine/nfp_computation_concave.md` (DoD hiányzó pont)
- Demo DXF set: `samples/dxf_demo/*`
- DXF import út: `vrs_nesting/sparrow/input_generator.py` → `import_part_raw()`
- Regressziós schema: `poc/nfp_regression/README.md` + `rust/nesting_engine/tests/nfp_regression.rs`
- Gate: `scripts/check.sh`, `scripts/verify.sh`
