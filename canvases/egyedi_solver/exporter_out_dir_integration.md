# Exporter out/ konyvtar bekotese a run_dir strukturaiba

## 🎯 Funkcio
A task celja, hogy a futasi artifact struktura reszekent legyen egy standard kimeneti konyvtar:
`runs/<run_id>/out/`.

Az exporter futtathato legyen ugy is, hogy eleg csak a `run_dir`-t megadni, es a sheet-enkenti DXF-ek automatikusan a `run_dir/out/` ala keszuljenek.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `vrs_nesting/run_artifacts/run_dir.py` kiegeszitese: `out/` konyvtar letrehozasa a run_dir alatt, es expose-olasa a RunContext-ben.
  - `vrs_nesting/dxf/exporter.py` CLI kiegeszitese `--run-dir` opcioval:
    - ha `--run-dir` meg van adva, alapertelmezett:
      - input: `<run_dir>/solver_input.json`
      - output: `<run_dir>/solver_output.json`
      - out-dir: `<run_dir>/out`
    - a korabbi `--input/--output/--out-dir` interface maradjon kompatibilis.
  - Reprodukálhato smoke: uj script, ami letrehoz egy ideiglenes run_dir-t, beir minimalis solver_input/output JSON-t, lefuttatja az exportert `--run-dir`-rel, majd ellenorzi, hogy `out/sheet_001.dxf` letrejott.
  - A smoke keruljon be a repo standard gate-be (`scripts/check.sh`), hogy a verify mar ezt is lefedje.
- Nincs benne:
  - End-to-end “vrs_nesting/cli.py run -> solver -> validator -> exporter -> report.json” teljes pipeline (ez a #1 task).
  - `report.json` vegleges osszeallitas (az #1 task resze).
  - Shaped stock bbox/outer_points export specialitasa (kulon scope, ha kell).

### Erintett fajlok
- `vrs_nesting/run_artifacts/run_dir.py`
- `vrs_nesting/dxf/exporter.py`
- `scripts/check.sh`
- `scripts/smoke_export_run_dir_out.py`
- `codex/codex_checklist/egyedi_solver/exporter_out_dir_integration.md`
- `codex/reports/egyedi_solver/exporter_out_dir_integration.md`

### DoD
- [ ] A `create_run_dir(...)` mindig letrehozza: `runs/<run_id>/out/` (vagy az adott run_root alatt), es a RunContext expose-olja az `out_dir` path-ot.
- [ ] Az exporter futtathato: `python3 vrs_nesting/dxf/exporter.py --run-dir <run_dir>` es ilyenkor defaultban a `<run_dir>/solver_input.json`, `<run_dir>/solver_output.json`, `<run_dir>/out` pathokat hasznalja.
- [ ] A `--run-dir` nem hasznalhato egyutt explicit `--input/--output/--out-dir` kapcsolokkal; a hiba egyertelmu es determinisztikus.
- [ ] Letrejon uj smoke script: `scripts/smoke_export_run_dir_out.py`, ami ezt automatizaltan ellenorzi.
- [ ] A smoke benne van a standard gate-ben: `./scripts/check.sh`.
- [ ] Verify gate PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/exporter_out_dir_integration.md`.

### Kockazat + mitigacio + rollback
- Kockazat: CLI backward compatibility torik, ha a kapcsolok osszeakadnak.
- Mitigacio: `--run-dir` legyen opcionális, es legyen mutual-exclusion szabaly a parserben (`--run-dir` vs explicit `--input/--output/--out-dir`).
- Rollback: exporter CLI visszaallithato a korabbi interface-re; a run_dir out/ letrehozas megmaradhat (nem tor).

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/exporter_out_dir_integration.md`
- Task-specifikus ellenorzes:
  - `scripts/smoke_export_run_dir_out.py` lefut a `scripts/check.sh` reszekent.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `vrs_nesting/run_artifacts/run_dir.py`
- `vrs_nesting/dxf/exporter.py`
- `scripts/check.sh`
- `scripts/verify.sh`
- `canvases/egyedi_solver/dxf_export_per_sheet_mvp.md`
- `docs/solver_io_contract.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
