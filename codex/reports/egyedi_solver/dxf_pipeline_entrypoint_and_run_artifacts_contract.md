PASS

## 1) Meta

- **Task slug:** `dxf_pipeline_entrypoint_and_run_artifacts_contract`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_dxf_pipeline_entrypoint_and_run_artifacts_contract.yaml`
- **Futas datuma:** `2026-02-14`
- **Branch / commit:** `main@31a6904`
- **Fokusz terulet:** `Docs | Scripts | DXF pipeline contract`

## 2) Scope

### 2.1 Cel

- DXF pipeline canonical entrypoint + run artifact szerzodes formalizalasa dedikalt doksiban.
- A meglvo real DXF smoke megerositese a szerzodes enforce-olasaert.
- report.json minimalis schema + artifact presence explicit validalasa.

### 2.2 Nem-cel (explicit)

- Uj E2E futas bevezetese a gate-be.
- CLI run/log formatum attervezese.
- Table-solver (`run`) pipeline modositas.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok

- **Canvas:**
  - `canvases/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md`
- **Docs:**
  - `docs/dxf_run_artifacts_contract.md`
- **Smoke enforcement:**
  - `scripts/smoke_real_dxf_sparrow_pipeline.py`
- **Codex artefaktok:**
  - `codex/codex_checklist/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md`
  - `codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md`

### 3.2 Miert valtoztak?

- A task explicit celja a DXF run entrypoint es run-dir contract stabilizalasa volt.
- A szerzodes akkor hasznos, ha automatizalt ellenorzes is tartozik hozza, ezert a meglvo smoke scriptbe kerult a hardening.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `python3 -m py_compile scripts/smoke_real_dxf_sparrow_pipeline.py` -> PASS
- `./scripts/check.sh` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-14T23:45:11+01:00 → 2026-02-14T23:46:43+01:00 (92s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.verify.log`
- git: `main@31a6904`
- módosított fájlok (git status): 7

**git diff --stat**

```text
 scripts/smoke_real_dxf_sparrow_pipeline.py | 109 ++++++++++++++++++++++++++++-
 1 file changed, 107 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M scripts/smoke_real_dxf_sparrow_pipeline.py
?? canvases/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md
?? codex/codex_checklist/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_dxf_pipeline_entrypoint_and_run_artifacts_contract.yaml
?? codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md
?? codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.verify.log
?? docs/dxf_run_artifacts_contract.md
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| Letrejott a dedikalt contract doksi (`docs/dxf_run_artifacts_contract.md`) | PASS | `docs/dxf_run_artifacts_contract.md:1` | A doksi tartalmazza a belepesi pontokat, stdout/stderr policy-t, run_dir policy-t, required artifact listat es report schema-t. | `./scripts/check.sh` (real DXF smoke futasa) |
| Smoke enforced: stdout = 1 sor (run_dir) | PASS | `scripts/smoke_real_dxf_sparrow_pipeline.py:92` | A smoke 1 nem-ures stdout sort var, ellenkezo esetben fail. | `./scripts/check.sh` |
| Smoke enforced: kotelezo artefaktok leteznek | PASS | `scripts/smoke_real_dxf_sparrow_pipeline.py:102` | A kotelezo top-level + `out/sheet_001.dxf` artifact lista explicit ellenorzott. | `./scripts/check.sh` |
| Smoke enforced: report.json schema + paths letezes ellenorzes | PASS | `scripts/smoke_real_dxf_sparrow_pipeline.py:130`, `scripts/smoke_real_dxf_sparrow_pipeline.py:151`, `scripts/smoke_real_dxf_sparrow_pipeline.py:170` | A report top-level, `paths`, `metrics` kulcsok es a `paths.*` altal mutatott valos file/dir ellenorzese megtortenik. | `./scripts/check.sh` |
| Smoke enforced: `out/sheet_001.dxf` letezik es nem ures | PASS | `scripts/smoke_real_dxf_sparrow_pipeline.py:119`, `scripts/smoke_real_dxf_sparrow_pipeline.py:190` | Az output file presence es meretellenorzes ket ponton validalt. | `./scripts/check.sh` |
| Repo gate PASS | PASS | `codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.verify.log` | A verify wrapper lefutott, report AUTO_VERIFY blokk frissult. | `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_pipeline_entrypoint_and_run_artifacts_contract.md` |

## 8) Advisory notes (nem blokkolo)

- A smoke a wrapper stdout szerzodeset enforced-olja; ha kesobb CLI logging policy valtozik, ezt a tesztet ehhez szinkronban kell tartani.
- A `report.paths` ellenorzes a jelenlegi `dxf-run` report mezokre epul, uj mezok hozzaadasa nem tor kompatibilitast.
- A dedikalt contract doksi lett a referenciapont a DXF run artefakt elvarasokra.
