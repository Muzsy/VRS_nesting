# Valos DXF nesting pipeline (Sparrow): import bovitese + instance generator + multi-sheet + eredeti export

## 🎯 Funkcio
Valos DXF alapú nesting end-to-end pipeline bevezetese a repoba (Sparrow alapon), az alabbi komponensekkel:

1) DXF import bovitese:
   - ARC/SPLINE kezeles (poligonizalas)
   - kontur chaining (szegmensek osszefuzese zart konturra)
2) Sparrow input (instance.json) generator:
   - part/stock konturok + holes kinyerese
   - spacing/margin offset alkalmazasa
   - konvenciok betartasa (layer/nev/egysegek)
3) Multi-sheet wrapper Sparrowhoz:
   - iterativ futtatas több tablára / stock peldanyra
   - unplaced kezelese + determinisztikus run artefaktok
4) Export eredeti geometriaval:
   - eredeti DXF entitasok (vagy legalabb eredeti kontur) exportja placement szerinti transzformalassal
   - sheet_XXX.dxf per tablankent, preferaltan BLOCK/INSERT megoldassal

A table-solver CLI flow (vrs_nesting/cli.py run) nem torhet.

## 🧠 Fejlesztesi reszletek

### Meglevo alapok (amit hasznalunk, nem ujrairunk)
- DXF import: `vrs_nesting/dxf/importer.py`
- Geometria clean/polygonize/offset: 
  - `vrs_nesting/geometry/clean.py`
  - `vrs_nesting/geometry/polygonize.py`
  - `vrs_nesting/geometry/offset.py`
- Sparrow runner: `vrs_nesting/runner/sparrow_runner.py`
- Multi-sheet terv: `docs/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- DXF export (MVP): `vrs_nesting/dxf/exporter.py` + doksi: `docs/dxf_nesting_app_8_dxf_export_tablankent_reszletes.md`
- Import/polygonize terv: 
  - `docs/dxf_nesting_app_2_dxf_import_konturok_kinyerese_konvencioval_reszletes.md`
  - `docs/dxf_nesting_app_3_ivek_spline_ok_poligonizalasa_geometria_clean_reszletes.md`
- Sparrow IO generator terv:
  - `docs/dxf_nesting_app_5_sparrow_input_json_generator_reszletes.md`
  - `docs/dxf_nesting_app_6_sparrow_futtatas_output_parse_reszletes.md`

### Uj end-to-end cel (javasolt forma)
A valos DXF nesting legyen uj CLI alparancs / script, hogy a table-solver schema ne keveredjen:
- preferalt: uj CLI subcommand a `vrs_nesting/cli.py`-ban, pl. `dxf-run` (vagy `sparrow-run`)
  - bemenet: uj project json (DXF referenciakkal)
  - kimenet: run_dir (stdout-on csak path), run artefaktok a run_dir alatt

Valasztott implementacio:
- CLI belepesi pont: `python3 -m vrs_nesting.cli dxf-run <project.json> --run-root runs`
- Script wrapper: `python3 scripts/run_real_dxf_sparrow_pipeline.py --project <project.json>`
  (a script a CLI same pipeline-jat hasznalja, stdout-on csak run_dir path)

### Uj project schema (DXF flow)
A jelenlegi MVP project schema (`docs/mvp_project_schema.md`, `vrs_nesting/project/model.py`) csak table-solverhez jo.
A DXF flow-hoz vezess be kulon schema verziót (pl. `dxf_v1`), hogy:
- strict maradjon
- ne torje a table-solver `version=v1` flow-t

Javasolt minimum:
- top-level:
  - `version: "dxf_v1"`
  - `name`, `seed`, `time_limit_s`
  - `units` (pl. "mm") vagy egy explicit scale policy
  - `spacing_mm` / `margin_mm` (offset policy)
  - `stocks_dxf`: lista (id, path, quantity, optional rotation policy)
  - `parts_dxf`: lista (id, path, quantity, optional rotation policy, optional layer mapping)
- A schema implementacio: `vrs_nesting/project/model.py` kiterjesztese ugy, hogy:
  - `version=v1` viselkedes valtozatlan
  - `version=dxf_v1` uj tipus es validator

Valasztott schema:
- `version: "dxf_v1"`
- strict top-level: `version`, `name`, `seed`, `time_limit_s`, `units`, `spacing_mm`, `margin_mm`, `stocks_dxf`, `parts_dxf`
- strict item schema (`stocks_dxf` / `parts_dxf`): `id`, `path`, `quantity`, optional `allowed_rotations_deg`

### DXF import bovitese: ARC/SPLINE + chaining
Cel: a `vrs_nesting/dxf/importer.py` adjon ki olyan konturokat, amibol:
- zart outer kontur (polygon)
- 0..n hole kontur (polygon)

Kotelezo kepessegek:
- ARC -> polyline approximacio (max chord error / segment length policy)
- SPLINE -> polyline approximacio (mint a docban)
- chaining:
  - a szegmensek osszefuzese kozel-toleranciaval (epsilon)
  - iranyhelyesites + zartsag ellenorzes
- error policy:
  - ha nincs zart outer kontur: ertelmes hiba, run fail okkal a reportban

### Sparrow input generator
Hozz letre egy dedikalt modult (ne a runnerbe zsufold):
- pl. `vrs_nesting/sparrow/input_generator.py` (uj mappa engedelyezett)
Funkcio:
- beolvassa a DXF projectet
- importal: outer+holes poligonokat
- clean/polygonize/offset a spacing/margin szerint
- eloallit egy Sparrow-kompatibilis instance JSON-t
- a run_dir-be ment:
  - `sparrow_instance.json`
  - `sparrow_input_meta.json` (units/offset params, file lista, hash)

### Multi-sheet wrapper Sparrowhoz
Implementald a wrapper logikat a terv szerint (docs/7):
- uj modul: `vrs_nesting/sparrow/multi_sheet_wrapper.py` (vagy hasonlo)
- felelos:
  - tobb stock peldany kezelese (quantity)
  - iterativ futtatas: minden körben Sparrow, majd maradek partokkal tovabb
  - output parse: placementek + unplaced lista okokkal
- run artefaktok:
  - `sparrow_stdout.log`, `sparrow_stderr.log`
  - `sparrow_output.json` (nyers)
  - `solver_output.json` kompatibilis formatum (ha mar van validátor), vagy `nesting_output.json` uj formatum, de legyen doksival.

Valasztott run artefakt lista a dxf-run flowban (`runs/<run_id>/`):
- `project.json`
- `sparrow_instance.json`
- `sparrow_input_meta.json`
- `sparrow_output.json`
- `solver_input.json`
- `solver_output.json`
- `sparrow_stdout.log`
- `sparrow_stderr.log`
- `out/sheet_001.dxf` (es tovabbi sheet-ek)

### Export eredeti geometriaval
A cel az, hogy a kimeneti DXF-ben ne “ujrarajzolt” poligon legyen, hanem:
- preferalt: eredeti DXF entitasok blokkba mentese, majd INSERT transzformmal (forgatas + eltolás)
- legalabb: eredeti outer/hole konturok exportja (ha entitasmegtartas tul nagy scope), de a task cime szerint az eredeti geometriat kell celozni.

Javasolt megoldas:
- az import lepes tarolja a “source geometry reference”-t (file path, layer, entity ids / vagy legalabb a nyers DXF blokk tartalom)
- exporter kapjon hozzaferest ehhez a referenciához
- kimenet:
  - `runs/<run_id>/out/sheet_001.dxf`, stb.

### Erintett fajlok (minimum)
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/geometry/clean.py`
- `vrs_nesting/geometry/polygonize.py`
- `vrs_nesting/geometry/offset.py`
- `vrs_nesting/runner/sparrow_runner.py`
- (uj) `vrs_nesting/sparrow/input_generator.py`  (vagy ekvivalens)
- (uj) `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- `vrs_nesting/dxf/exporter.py` (eredeti geometria export)
- `vrs_nesting/cli.py` (uj subcommand, ha ezt valasztjuk)
- `docs/mvp_project_schema.md` + (uj) `docs/dxf_project_schema.md` (ha schema uj verzio)
- `scripts/check.sh`
- (uj) `scripts/smoke_real_dxf_sparrow_pipeline.py` (vagy .sh)
- `codex/codex_checklist/egyedi_solver/real_dxf_nesting_sparrow_pipeline.md`
- `codex/reports/egyedi_solver/real_dxf_nesting_sparrow_pipeline.md`

### DoD
- [ ] Bevezetve uj DXF project schema (`version=dxf_v1` vagy ekvivalens), strict validacioval, table-solver schema erintetlen.
- [ ] DXF import kezeli az ARC es SPLINE elemeket poligonizalassal, es chaininggel zart konturt epit.
- [ ] Generator eloallit egy Sparrow instance JSON-t run_dir-be mentve.
- [ ] Multi-sheet wrapper vegig tud futni több stock peldanyon, es placement/unplaced outputot ad.
- [ ] Export sheet-enkent keszul `runs/<run_id>/out/sheet_001.dxf`... es az eredeti geometriat hasznalja (BLOCK/INSERT preferalt).
- [ ] Van smoke teszt, ami egy minimal demo DXF keszlettel lefut (repo alatt), es a gate (`scripts/check.sh`) futtatja.
- [ ] Verify gate PASS.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/real_dxf_nesting_sparrow_pipeline.md`
- Task-specifikus smoke:
  - `scripts/smoke_real_dxf_sparrow_pipeline.py` (a gate resze)

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `docs/dxf_nesting_app_2_dxf_import_konturok_kinyerese_konvencioval_reszletes.md`
- `docs/dxf_nesting_app_3_ivek_spline_ok_poligonizalasa_geometria_clean_reszletes.md`
- `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`
- `docs/dxf_nesting_app_5_sparrow_input_json_generator_reszletes.md`
- `docs/dxf_nesting_app_6_sparrow_futtatas_output_parse_reszletes.md`
- `docs/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- `docs/dxf_nesting_app_8_dxf_export_tablankent_reszletes.md`
- `docs/dxf_nesting_app_terv_sparrow_jagua_rs_alap.md`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/runner/sparrow_runner.py`
- `vrs_nesting/dxf/exporter.py`
- `scripts/check.sh`
- `scripts/verify.sh`
