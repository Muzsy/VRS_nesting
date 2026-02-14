# canvases/egyedi_solver/export_original_geometry_block_insert_impl.md

# Export “eredeti geometriaval” (BLOCK/INSERT, nem ujrarajzolt poligon) – implementacio

## 🎯 Funkcio
A DXF export **ne pontlistabol ujrarajzolt** (LINE/LWPOLYLINE) konturokat irjon, hanem a **forras DXF eredeti entitasait** (LINE/ARC/SPLINE/CIRCLE/LWPOLYLINE stb.) tartsa meg.

MVP definicio:
- minden part **BLOCK definiciokent** bekerul a kimeneti DXF-be
- placementenkent **INSERT** (eltolas + rotacio) helyezi el a partot a megfelelo sheet-en
- sheet-enkent: `runs/<run_id>/out/sheet_001.dxf` stb.

A table-solver (rect) export backward-compatible maradjon: ott tovabbra is lehet “approx” (pontlista) export.

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - Exporter tudjon “source geometry” modban dolgozni: BLOCK+INSERT, eredeti entitasokkal
  - A DXF pipeline (dxf-run / sparrow-run) exportja defaultban “source geometry” legyen
  - Smoke teszt: valodi DXF fixture (ARC + SPLINE) export utan a kimenetben legyen:
    - legalabb 1 INSERT
    - a kapcsolodo BLOCK-ban legyen legalabb 1 ARC vagy 1 SPLINE
  - Gate-be kotes: `scripts/check.sh`

- Nincs benne:
  - DXF import bovitese / chaining javitas (kulon task)
  - Multi-sheet wrapper algoritmikus tuning (kulon task)
  - Layer/preset rendszer (kulon task)

### Elvart adatfolyam (source geometry mapping)
Az exporternek tudnia kell: placement -> melyik forras DXF-bol jon a part geometriája.
A feladat az, hogy a jelenlegi pipeline-ban ez **stabilan es determinisztikusan** elerheto legyen.

Elfogadott megoldasok (Codex a repo mintaihoz igazodva valasszon):
- A nesting output (pl. `nesting_output.json` vagy `solver_output.json`) tartalmazza partonkent:
  - `part_id`
  - `source_dxf_path`
  - `source_layers` (outer/inner)
  - opcionális `source_base_offset_mm` (ha a forras nem origoban van)
VAGY
- Kulon mapping file a run_dir-ben:
  - `runs/<run_id>/source_geometry_map.json` (part_id -> forras meta)

Kovetelmeny: export idoben ne legyen “best-effort”; ha nincs mapping, legyen ertelmes hiba (reportban).

### Felderitesi pontositas (repo-aktualis)
- A `dxf-run` pipeline jelenleg a `run_dir`-be mar irja:
  - `solver_input.json` (part meta + source geometriara utalo mezo(k))
  - `solver_output.json` (placement lista)
- A stabil, explicit mapping ehhez a taskhoz kulon filekent kerul be:
  - `runs/<run_id>/source_geometry_map.json`
  - kulcs: `part_id`
  - minimum mezo: `source_dxf_path`, `source_layers` (`outer`,`inner`)
  - opcionális: `source_base_offset_mm` (`x`,`y`)
- Exporter olvasasi sorrend source modban:
  1. `source_geometry_map.json` (ha van),
  2. fallback a `solver_input.parts[*]` source mezoi.
  3. ha hasznalt `part_id`-hoz nincs mapping -> fail-fast hiba.

### CLI/kapcsolok pontositas
- `vrs_nesting/dxf/exporter.py` uj kapcsolo:
  - `--geometry-mode approx|source` (default: `approx`)
- `--run-dir` hasznalatnal:
  - ha `solver_output.json` tartalmaz explicit `geometry_mode` mezot, azt alkalmazza
  - egyebkent default `approx`
- `dxf-run` pipeline:
  - a wrapper `solver_output.json`-ba explicit `geometry_mode: "source"` jelzest ir, igy dxf flow-ban a source export lesz az alap.

### Export implementacios irany (MVP)
- `vrs_nesting/dxf/exporter.py`:
  - vezess be egy valaszthato modot:
    - `--geometry-mode approx|source` (default maradjon approx, hogy a regi hasznalat ne torjon)
  - `--run-dir` modban (ha mar letezik) a dxf pipeline eseten default legyen:
    - `--geometry-mode source` (ha felismeri, hogy DXF flow run_dir)
  - “source” mod:
    - minden unikalis part_id-hoz hozz letre egy BLOCK-ot (nev determinisztikus, pl. `P_<part_id>_<hash>`).
    - nyisd meg a forras DXF-et (cache-elve), szurd ki az engedelyezett layereken levo entitasokat (outer/inner).
    - masold be oket a BLOCK-ba (valtozatlan entitas tipusokkal).
    - a kimeneti sheet modelspace-be tegyel `INSERT`-et a placement szerint:
      - `insert=(x_mm, y_mm, 0)`
      - `rotation_deg`
      - (ha kell) scale a units policy szerint
    - ha van `source_base_offset_mm`, azt vedd figyelembe a BLOCK base pontnal vagy az INSERT location szamitasanal.
  - determinisztika:
    - block nevkepzes stabil (part_id + forras file hash + layer policy hash)
    - entity sorrend stabil (query + sort handle szerint, ha elerheto)

### Smoke teszt (MVP bizonyitek)
Uj smoke:
- `scripts/smoke_export_original_geometry_block_insert.py`
Feladata:
1) hozzon letre ideiglenes run_dir-t (a repo run_dir helperrel, ha van)
2) a run_dir-be tegyen minimal nesting outputot 1 placementtel (rotation != 0, hogy INSERT rotaciot is teszteljen)
3) mappingolja a placementet egy valodi DXF fixture part file-ra, amiben van ARC + SPLINE (a `samples/dxf_demo/` keszletbol)
4) futtassa az exportert `--run-dir`-rel (vagy a megfelelo interface-szel)
5) betolti a kimeneti `sheet_001.dxf`-et, es ellenorzi:
   - van legalabb 1 INSERT a modelspace-ben
   - a hivatkozott BLOCK definicioban van legalabb 1 ARC vagy 1 SPLINE entitas

### Erintett fajlok
- `vrs_nesting/dxf/exporter.py`
- (ha kell a mappinghoz) `vrs_nesting/sparrow/input_generator.py`
- (ha kell a mappinghoz) `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- `scripts/smoke_export_original_geometry_block_insert.py` (UJ)
- `scripts/check.sh`
- `codex/codex_checklist/egyedi_solver/export_original_geometry_block_insert_impl.md`
- `codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md`

### DoD
- [ ] Exporter tud “source geometry” modban exportalni: BLOCK+INSERT, eredeti entitas tipusokkal.
- [ ] A dxf pipeline exportja ezt a modot hasznalja (default vagy explicit).
- [ ] Uj smoke PASS: output DXF-ben INSERT + BLOCK-ban ARC/SPLINE jelen van.
- [ ] `scripts/check.sh` futtatja a smoke-ot.
- [ ] Verify PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md`

### Kockazat + mitigacio
- Kockazat: mapping hianyos / nem stabil a pipeline-ban.
  - Mitigacio: explicit mapping file a run_dir-ben; fail-fast ha hianyzik.
- Kockazat: egyes CAD-ek erzekenyek nested blockokra / units scale-re.
  - Mitigacio: egysites: mm; scale csak ha explicit units mismatch van; MVP-ben tiltott non-uniform scale.
- Kockazat: entity copy nem teljes (attribok / styles).
  - Mitigacio: MVP-ben csak geometriai entitasok (LINE/ARC/SPLINE/CIRCLE/LWPOLYLINE); a tobbi kimarad, de logolva legyen.

## 🧪 Tesztallapot
- Kotelezo:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md`
- Gate resze:
  - `./scripts/check.sh` -> `python3 scripts/smoke_export_original_geometry_block_insert.py`

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `docs/dxf_nesting_app_8_dxf_export_tablankent_reszletes.md`
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
- `canvases/egyedi_solver/dxf_export_block_insert_geometry.md` (ha letezik)
- `vrs_nesting/dxf/exporter.py`
- `scripts/check.sh`
- `scripts/verify.sh`
