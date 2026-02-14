# DXF pipeline belepesi pont + run artefakt szerzodes (contract)

## 🎯 Funkcio
Rogzitsuk es “lockoljuk” a **valos DXF → Sparrow → multi-sheet → export** pipeline hivatalos belepesi pontjat, valamint a **run_dir artefakt szerzodest** (milyen fajloknak kell letrejonniuk, hol, milyen minimalis garantialt strukturaval), hogy:
- automatizalhato legyen a futtatas (stdout parsing),
- stabil maradjon a repo gate + smoke tesztek alatt,
- egyertelmu legyen a “mit hol talalok” (runs/<run_id>/...).

A table-solver pipeline (`vrs_nesting/cli.py run`) nem torhet.

## 🧠 Fejlesztesi reszletek

### 1) Hivatalos belepesi pontok (DXF pipeline)
**Primary (canonical):**
- `python3 -m vrs_nesting.cli dxf-run <project_dxf_v1.json> --run-root <runs_dir> [--sparrow-bin <path>]`

**Secondary (wrapper script):**
- `python3 scripts/run_real_dxf_sparrow_pipeline.py --project <project_dxf_v1.json> --run-root <runs_dir> [--sparrow-bin <path>]`

Elvaras: a wrapper csak a CLI-t hivja, es ne irjon extra outputot stdout-ra.

Repo-aktualis allapot:
- `scripts/run_real_dxf_sparrow_pipeline.py` kozvetlenul a `vrs_nesting.cli.main()`-t hivja a `dxf-run` paranccsal.
- A `dxf-run` jelenleg a futas vegen `print(str(ctx.run_dir))`-t ir stdout-ra.
- Hibas esetben a CLI `ERROR: ...` uzeneteket stderr-re ir.

### 2) Stdout/stderr szerzodes (kritikus)
**Sikeres futas (exit=0):**
- **stdout pontosan 1 sor**: az **abszolut** `run_dir` path (pl. `/abs/path/runs/20260214T..._deadbeef`)
- minden egyeb log/info **stderr**-re menjen (ha egyaltalan).

**Hibas futas (exit!=0):**
- stdout ne legyen parse-olhatatlan “felesleges” tartalom (preferaltan ures),
- ertelmes error `stderr`-en.

Motivacio: a smokek/CI es kesobbi toolok a stdout utolso sorabol run_dir-t olvasnak.

Repo-aktualis konkretizalas:
- sikeres futasnal a vart forma: 1 nem-ures sor (`<abs_run_dir>`),
- wrapper scriptnek nem szabad tovabbi stdout tartalmat generalnia.

### 3) run_id es run_dir allokacio policy
A DXF pipeline a `create_run_dir(run_root=...)` mechanizmust hasznalja.
- `run_root` abszolutra resolve-ol (Path.resolve)
- `run_id` formatum: `YYYYMMDDTHHMMSSZ_<8hex>`
- `run_dir = <run_root>/<run_id>`
- a `run_dir/out` konyvtar **mindig** letrejon allokaciokor
- `run_dir/run.log` **mindig** letrejon allokaciokor (legalabb uresen)

Repo-aktualis konkretizalas:
- allokacio a `vrs_nesting/run_artifacts/run_dir.py:create_run_dir()` szerint tortenik;
- `run_root` mindig `Path(run_root).resolve()` utan kerul hasznalatra.

### 4) Run artefakt szerzodes (DXF pipeline, exit=0)
Sikeres `dxf-run` futas utan a kovetkezo minimalis artefaktoknak letezniuk kell:

**Kotelezo top-level:**
- `project.json` (snapshot, validalt dxf_v1 payload)
- `run.log` (event sorok UTC idobelyeggel)
- `report.json` (DXF pipeline summary + path mapping)
- `sparrow_instance.json` (Sparrow instance)
- `solver_input.json` (solver_input v1 + DXF source metadata mezokkel, ha relevans)
- `sparrow_input_meta.json` (import/polygonize/offset policy + input file list/hash)
- `sparrow_output.json` (nyers multi-sheet futasi meta sheet-enkent)
- `solver_output.json` (placements + unplaced + status)
- `source_geometry_map.json` (DXF “eredeti geometria” exporthoz: part_id→forras DXF/layer/base offset mapping)
- `sparrow_stdout.log` + `sparrow_stderr.log` (aggregalt)

**Kotelezo kimenet:**
- `out/` konyvtar letezik
- ha van legalabb 1 sheet hasznalat: `out/sheet_001.dxf` letezik es nem ures
  - tovabbi sheet-ek: `out/sheet_002.dxf`, stb.

**Opcionális (de ha multi-sheet futott, akkor varhato):**
- `sheets/sheet_001/...` (per-sheet futtatas dir, benne pl. `instance_sheet.json`, runner outputok, logok)

### 5) report.json minimalis schema (DXF)
A `runs/<run_id>/report.json` minimalisan tartalmazza:
- `contract_version: "dxf_v1"`
- `project_name`, `seed`, `time_limit_s`
- `run_dir`, `status`
- `paths` objektum, legalabb:
  - `project_json`
  - `sparrow_instance_json`
  - `solver_input_json`
  - `sparrow_input_meta_json`
  - `sparrow_output_json`
  - `solver_output_json`
  - `out_dir`
- `metrics` objektum (placements_count, unplaced_count)
- `export_summary` (exported_count, sheets, stb. – exporter altal)

Repo-aktualis konkretizalas:
- `paths` jelenleg a kovetkezoket tartalmazza:
  - `project_json`
  - `sparrow_instance_json`
  - `solver_input_json`
  - `sparrow_input_meta_json`
  - `sparrow_output_json`
  - `solver_output_json`
  - `out_dir`
- `metrics` jelenleg:
  - `placements_count`
  - `unplaced_count`

### 6) Teszt-strategia: contract enforcement a meglvo smoke-ban
Ne tegyunk be uj, draga E2E futast a gate-be. Ehelyett:
- a meglvo `scripts/smoke_real_dxf_sparrow_pipeline.py` kerul megerositesre:
  - ellenorizze a **stdout 1 soros** szerzodest (a wrapper script outputja)
  - ellenorizze a fenti kotelezo run artefaktokat
  - ellenorizze a `report.json` kulcsait + hogy a `paths.*` konkretan letezo fajlokra mutatnak
  - ellenorizze hogy `out/sheet_001.dxf` letezik es nem ures

### 7) Erintett fajlok
- Doksi:
  - `docs/dxf_run_artifacts_contract.md` (UJ)
- Teszt/contract enforcement:
  - `scripts/smoke_real_dxf_sparrow_pipeline.py` (frissites)
- Referencia implementacio (nem feltetlen modositjuk, csak a doksi hivatkozza):
  - `vrs_nesting/cli.py` (dxf-run)
  - `scripts/run_real_dxf_sparrow_pipeline.py`
  - `vrs_nesting/run_artifacts/run_dir.py`
  - `vrs_nesting/sparrow/multi_sheet_wrapper.py`

### DoD
- [ ] Letrejott a dedikalt contract doksi: `docs/dxf_run_artifacts_contract.md` (belepesi pont + stdout/stderr + run_dir tree + report.json schema).
- [ ] `scripts/smoke_real_dxf_sparrow_pipeline.py` enforced:
  - [ ] stdout = 1 sor (run_dir)
  - [ ] kotelezo artefaktok leteznek (lista fent)
  - [ ] report.json schema + paths letezes ellenorzese
  - [ ] out/sheet_001.dxf letezik es nem ures
- [ ] Repo gate PASS: `./scripts/verify.sh --report ...`

## 🧪 Tesztallapot
- Gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md`
- Contract enforcement:
  - `scripts/smoke_real_dxf_sparrow_pipeline.py` (a gate resze via `scripts/check.sh`)

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `vrs_nesting/cli.py`
- `scripts/run_real_dxf_sparrow_pipeline.py`
- `vrs_nesting/run_artifacts/run_dir.py`
- `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- `scripts/smoke_real_dxf_sparrow_pipeline.py`
- `docs/solver_io_contract.md`
- `docs/dxf_project_schema.md`
- `scripts/check.sh`
- `scripts/verify.sh`
