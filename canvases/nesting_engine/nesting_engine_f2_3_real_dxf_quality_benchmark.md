# canvases/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md

## 🎯 Funkció

Valós DXF inputból (repo mintákból) származtatott, determinisztikus `nesting_engine_v2` benchmark:

- DXF -> canonical mm polygon (outer-only) import a meglévő `vrs_nesting` DXF pipeline-on keresztül
- nesting_engine fixture-ek generálása explicit példányokkal (quantity=1, egyedi id)
- BLF vs NFP futtatás több runnal
- minőség-metrikák rögzítése reportban:
  - `sheets_used`, `placed_count`, `utilization_pct` (ha elérhető)
  - determinism (hash stabilitás runok között)

**Fontos korlát:** a repo-ban csak 1 “OK” part DXF van (`part_arc_spline_chaining_ok.dxf`), ezért a dataset “valós DXF-ből származtatott, de ismételt” (ugyanaz a part sokszor). Ez ettől még értékes: end-to-end DXF->polygon eredet bizonyított.

## 🧠 Fejlesztési részletek

### Kiinduló DXF-ek (repo)
- Stock: `samples/dxf_demo/stock_rect_1000x2000.dxf`
- Part: `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`

### 1) Fixture generálás valós DXF-ből (outer-only)
Új script:
- `scripts/gen_nesting_engine_real_dxf_quality_fixture.py`

Feladat:
- `vrs_nesting.project.model.DxfProjectModel` + `vrs_nesting.sparrow.input_generator.build_sparrow_inputs` felhasználásával:
  - beolvassa a stock+part DXF-et
  - kiveszi a `solver_input.stocks[0].outer_points` és `solver_input.parts[0].outer_points` pontlistát (mm)
- kanonizál:
  - dupe pontok kiszűrése
  - zárt ring utolsó pont eldobása, ha egyezik az elsővel
  - lex-min startpoint rotálás
  - outer CCW orientáció biztosítása
  - transzform: min_x/min_y -> 0,0 (sheet és part is)
- sheet width/height:
  - stock outer AABB-ből (`max_x-min_x`, `max_y-min_y`)
- holes:
  - benchmarkhoz: `holes_points_mm = []` (outer-only), hogy az F2-3 NFP gating ne dobjon BLF fallbackra.

Generált fixture-ek:
- `poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json`
- `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`

Paraméterek:
- `--time-limit-sec` default 300
- `--spacing-mm`, `--margin-mm` default a fixture sheet mezőibe
- `--rotations` default `0,90,180,270`

Felderitesi rogzites (2026-03-01):
- Pontforras: `build_sparrow_inputs(...)` kimenetbol `solver_input.stocks[0].outer_points` es `solver_input.parts[0].outer_points`.
- Sheet meret: a canonical stock outer ring AABB-je (`width_mm=max_x-min_x`, `height_mm=max_y-min_y`).
- Outer-only indok: `holes_points_mm=[]` mellett az F2-3 NFP benchmark nem esik vissza BLF fallbackra hole-gating miatt, igy a placer-kulonbseg merese tisztabb.

### 2) Benchmark futtatás (re-use)
Használd a már meglévő scriptet:
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`

Futtatás:
- mindkét inputra `--placer both --runs 5`

### 3) Report
Új report:
- `codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md`

Tartalom:
- parancsok
- 2×2 táblázat: (200/500) × (BLF/NFP) median runtime + sheets_used + placed_count + utilization + determinism stable
- értelmezés: NFP jobb/rosszabb/azonos (csak evidence alapján, nem “kell hogy jobb legyen”).

## 🧪 Tesztállapot

### DoD
- [x] A két fixture létezik:
  - `poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json`
  - `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`
- [x] A benchmark lefut mindkettőre:
  - `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input ...`
- [x] A report tartalmazza a median összefoglalót + determinism megállapítást
- [x] `./scripts/check.sh` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_real_dxf_quality_benchmark.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `scripts/export_real_dxf_nfp_pairs.py` (mintakód: DXF->solver_input.outer_points)
- `vrs_nesting/project/model.py`
- `vrs_nesting/sparrow/input_generator.py`
- `samples/dxf_demo/stock_rect_1000x2000.dxf`
- `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`
