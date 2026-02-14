PASS

## 1) Meta

- **Task slug:** `export_original_geometry_block_insert_impl`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/export_original_geometry_block_insert_impl.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_export_original_geometry_block_insert_impl.yaml`
- **Futas datuma:** `2026-02-14`
- **Branch / commit:** `main@fa3e661`
- **Fokusz terulet:** `Geometry | Scripts | IO Contract`

## 2) Scope

### 2.1 Cel

- DXF exporter bovitese `source` geometriamoddal (`BLOCK`+`INSERT`) az eredeti entitas tipusaival.
- Stabil part_id -> source DXF mapping elerhetove tetele explicit run_dir artefaktumban.
- Uj smoke teszt, ami bizonyitja az `INSERT` jelenletet es az `ARC/SPLINE` entitas jelenletet a referalt blokkban.
- Gate frissitese, hogy az uj smoke a standard `check.sh` resze legyen.

### 2.2 Nem-cel (explicit)

- DXF importer algoritmikus tovabbfejlesztese (chaining policy tuning).
- Multi-sheet optimalizalas / solver viselkedes modositas.
- Layer/preset rendszer bevezetese.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok

- **Canvas:**
  - `canvases/egyedi_solver/export_original_geometry_block_insert_impl.md`
- **Pipeline mapping:**
  - `vrs_nesting/sparrow/input_generator.py`
  - `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- **Exporter:**
  - `vrs_nesting/dxf/exporter.py`
- **Smoke + gate:**
  - `scripts/smoke_export_original_geometry_block_insert.py`
  - `scripts/check.sh`
- **Codex artefaktok:**
  - `codex/codex_checklist/egyedi_solver/export_original_geometry_block_insert_impl.md`
  - `codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md`

### 3.2 Miert valtoztak?

- A task kovetelmenye szerint a DXF exportnak dxf-flow esetben az eredeti geometriat kell kivinnie `BLOCK`+`INSERT` formatumban.
- Ehhez explicit source mappingra es source smoke bizonyitekra volt szukseg.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `python3 scripts/smoke_export_run_dir_out.py` -> PASS
- `python3 scripts/smoke_export_original_geometry_block_insert.py` -> PASS
- `./scripts/check.sh` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-14T23:22:47+01:00 → 2026-02-14T23:24:19+01:00 (92s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.verify.log`
- git: `main@fa3e661`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 scripts/check.sh                           |   4 +
 vrs_nesting/dxf/exporter.py                | 385 +++++++++++++++++++++++++++--
 vrs_nesting/sparrow/input_generator.py     |  10 +-
 vrs_nesting/sparrow/multi_sheet_wrapper.py |  48 ++++
 4 files changed, 430 insertions(+), 17 deletions(-)
```

**git status --porcelain (preview)**

```text
 M scripts/check.sh
 M vrs_nesting/dxf/exporter.py
 M vrs_nesting/sparrow/input_generator.py
 M vrs_nesting/sparrow/multi_sheet_wrapper.py
?? canvases/egyedi_solver/export_original_geometry_block_insert_impl.md
?? codex/codex_checklist/egyedi_solver/export_original_geometry_block_insert_impl.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_export_original_geometry_block_insert_impl.yaml
?? codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md
?? codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.verify.log
?? scripts/smoke_export_original_geometry_block_insert.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| Exporter tud `source` geometriamodban exportalni `BLOCK`+`INSERT` formatumban, eredeti entitas tipusaival | PASS | `vrs_nesting/dxf/exporter.py:419`, `vrs_nesting/dxf/exporter.py:499`, `vrs_nesting/dxf/exporter.py:716` | Beepult a `--geometry-mode approx|source`; `source` modban a blokk entitasok `LINE/ARC/SPLINE/CIRCLE/LWPOLYLINE` alapjan epulnek es modelspace-be `INSERT` kerul. | `python3 scripts/smoke_export_original_geometry_block_insert.py` |
| A dxf pipeline exportja ezt a modot hasznalja (default vagy explicit) | PASS | `vrs_nesting/sparrow/multi_sheet_wrapper.py:263`, `vrs_nesting/sparrow/multi_sheet_wrapper.py:271`, `vrs_nesting/dxf/exporter.py:579` | A wrapper `solver_output.json`-ba `geometry_mode: source` jelzest ir es `source_geometry_map.json`-t keszit; run-dir export ezt preferalja. | `python3 scripts/smoke_real_dxf_sparrow_pipeline.py` (a check gate reszekent) |
| Uj smoke PASS: output DXF-ben INSERT + BLOCK-ban ARC/SPLINE jelen van | PASS | `scripts/smoke_export_original_geometry_block_insert.py:42`, `scripts/smoke_export_original_geometry_block_insert.py:128`, `scripts/smoke_export_original_geometry_block_insert.py:136` | A smoke valodi fixture-rel fut, `source` modban exportal, majd DXF parse utan assertalja az `INSERT` es `ARC/SPLINE` jelenletet. | `python3 scripts/smoke_export_original_geometry_block_insert.py` |
| `scripts/check.sh` futtatja az uj smoke-ot | PASS | `scripts/check.sh:33`, `scripts/check.sh:99` | A gate script chmod listaba es futasi szekvenciaba is bekerult az uj smoke. | `./scripts/check.sh` |
| Verify PASS (`./scripts/verify.sh --report ...`) | PASS | `codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.verify.log` | A kotelezo wrapper futtatja a teljes gate-et es frissiti az AUTO_VERIFY blokkot. | `./scripts/verify.sh --report codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md` |

## 8) Advisory notes (nem blokkolo)

- Source modban a mapping hiany fail-fast hibara fut, best-effort fallback nincs hasznalt part eseten.
- A source entitasok kozul az ismeretlen tipusok kihagyasra kerulnek warning mellett.
