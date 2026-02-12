PASS_WITH_NOTES

## 1) Meta

- **Task slug:** `stock_holes_native_support`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/stock_holes_native_support.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_stock_holes_native_support.yaml`
- **Futas datuma:** `2026-02-12`
- **Branch / commit:** `main@5b9e2d2`
- **Fokusz terulet:** `IO Contract | Geometry | Scripts | CI`

## 2) Scope

### 2.1 Cel

- Natív alakos stock (`outer_points`) es hole (`holes_points`) tamogatas bevezetese a table-solver IO contractban.
- Rust solverben shape+holes alapú placement-feasibility ellenorzes.
- Python validatorban shape+holes in-bounds / hole-exclusion validacio.
- Repo quality gate smoke inputok frissitese, hogy a shape+holes ág futtatasra keruljon.

### 2.2 Nem-cel (explicit)

- Jagua-rs integracio.
- DXF importer/konverter fejlesztes.
- Optimalizacios heurisztika ujratervezese.

## 3) Valtozasok osszefoglaloja (Change summary)

### 3.1 Erintett fajlok

- **Docs:**
  - `docs/solver_io_contract.md`
- **Solver/validator:**
  - `rust/vrs_solver/src/main.rs`
  - `vrs_nesting/nesting/instances.py`
  - `scripts/validate_nesting_solution.py`
- **Gate/CI:**
  - `scripts/check.sh`
  - `.github/workflows/nesttool-smoketest.yml`
- **Codex artefaktok:**
  - `canvases/egyedi_solver/stock_holes_native_support.md`
  - `codex/goals/canvases/egyedi_solver/fill_canvas_stock_holes_native_support.yaml`
  - `codex/codex_checklist/egyedi_solver/stock_holes_native_support.md`
  - `codex/reports/egyedi_solver/stock_holes_native_support.md`

### 3.2 Miert valtoztak?

- A P0 audit blocker szerint a rectangle-only stock modell nem eleg; shape+holes natív tamogatas kellett az IO contract/solver/validator lancban.
- A smoke tesztek shape+holes inputra allitasa szukseges, hogy a minosegkapu valos coverage-et adjon erre az ágra.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/stock_holes_native_support.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` -> PASS
- `python3 scripts/validate_nesting_solution.py --help` -> PASS
- `python3 -m vrs_nesting.runner.vrs_solver_runner --help` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-12T20:32:23+01:00 → 2026-02-12T20:33:28+01:00 (65s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/stock_holes_native_support.verify.log`
- git: `main@5b9e2d2`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 .github/workflows/nesttool-smoketest.yml |   9 +-
 docs/solver_io_contract.md               |  13 +-
 rust/vrs_solver/src/main.rs              | 288 ++++++++++++++++++++++++++++---
 scripts/check.sh                         |   9 +-
 scripts/validate_nesting_solution.py     |  18 +-
 vrs_nesting/nesting/instances.py         | 189 +++++++++++++++++---
 6 files changed, 461 insertions(+), 65 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .github/workflows/nesttool-smoketest.yml
 M docs/solver_io_contract.md
 M rust/vrs_solver/src/main.rs
 M scripts/check.sh
 M scripts/validate_nesting_solution.py
 M vrs_nesting/nesting/instances.py
?? canvases/egyedi_solver/stock_holes_native_support.md
?? codex/codex_checklist/egyedi_solver/stock_holes_native_support.md
?? codex/codex_checklist/egyedi_solver_p0_audit.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_stock_holes_native_support.yaml
?? codex/reports/egyedi_solver/stock_holes_native_support.md
?? codex/reports/egyedi_solver/stock_holes_native_support.verify.log
?? codex/reports/egyedi_solver_p0_audit.md
?? codex/reports/egyedi_solver_p0_audit.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 IO contract leírja `stocks[].outer_points` + `stocks[].holes_points[]` mezoket | PASS | `docs/solver_io_contract.md` | A contract specifikacio tartalmazza a shape+holes mezoket es point formatumokat. | verify/check smoke input parse |
| #2 Rust solver shape+holes stockon nem helyez lyukba es nem log tul | PASS | `rust/vrs_solver/src/main.rs` | A solver polygon+hole geometriaval ellenorzi a candidate rectangle feasibility-t placement elott. | `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` |
| #3 Python validator shape+holes inputon in-bounds + hole-exclusion + no-overlap ellenorzes | PASS | `vrs_nesting/nesting/instances.py`, `scripts/validate_nesting_solution.py` | A validator egységesen kezeli a rectangle es polygon stockot, hole metszes tiltassal. | `python3 scripts/validate_nesting_solution.py --help` |
| #4 `scripts/check.sh` shape+holes smoke inputon fut | PASS | `scripts/check.sh` | A check gate nested smoke inputja `outer_points`+`holes_points` mezoket hasznal. | verify/check gate |
| #5 Verify gate PASS | PASS | `codex/reports/egyedi_solver/stock_holes_native_support.verify.log` | A kotelezo verify gate lefutott, a report AUTO_VERIFY blokkja frissult. | `./scripts/verify.sh --report codex/reports/egyedi_solver/stock_holes_native_support.md` |

## 6) IO contract / mintak

- Frissult contract: `docs/solver_io_contract.md`
- Uj invarians: stock definialhato `outer_points` + opcionális `holes_points` mezokkel; placement rectangle nem metszheti a hole polygonokat.
- Lefedes a gate-ben: `scripts/check.sh` es `.github/workflows/nesttool-smoketest.yml` shape+holes inputot hasznal.

## 8) Advisory notes (nem blokkolo)

- A jelenlegi solver egyszeru row-cursor heurisztikat hasznal, shape+holes tamogatassal, de nem keres teljes 2D pozicioteret.
