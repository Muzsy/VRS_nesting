PASS

## 1) Meta

- **Task slug:** `p1_3_sparrow_dependency_risk_reduction_vendor_fallback`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_p1_3_sparrow_dependency_risk_reduction_vendor_fallback.yaml`
- **Futas datuma:** `2026-02-15`
- **Branch / commit:** `main`
- **Fokusz terulet:** `Scripts | CI | Docs`

## 2) Scope

### 2.1 Cel

- Sparrow dependency kockazat csokkentese vendor/submodule preferenciaval.
- Fallback clone/pin/build logika megtartasa biztos mukodessel.
- Sparrow bin feloldas/build logika kozpontositas `scripts/ensure_sparrow.sh` scriptbe.
- `check.sh` es workflow integracio egységesitese.

### 2.2 Nem-cel (explicit)

- Sparrow IO contract valtoztatasa.
- Geometry algoritmusok vagy DXF parser funkcionalis modositasai.
- `vrs_solver` viselkedesenek valtoztatasa.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok

- `scripts/ensure_sparrow.sh`
- `scripts/check.sh`
- `.github/workflows/sparrow-smoketest.yml`
- `.github/workflows/repo-gate.yml`
- `docs/qa/testing_guidelines.md`
- `AGENTS.md`
- `vendor/README.md`
- `codex/codex_checklist/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`
- `codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md`

### 3.2 Miert valtoztak?

- A Sparrow forras feloldasa ket helyen duplikalt volt, ami karbantartasi es external dependency kockazatot novelt.
- Az uj resolver script egysegesiti a vendor/submodule preferencia + fallback pinelt clone logikat.
- A CI checkout submodule tamogatasa elokesziti az offline-barat vendor utat.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `./scripts/check.sh` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-15T23:41:23+01:00 → 2026-02-15T23:42:59+01:00 (96s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.verify.log`
- git: `main@c7abb05`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 .github/workflows/repo-gate.yml         |  2 ++
 .github/workflows/sparrow-smoketest.yml | 26 ++++---------------
 AGENTS.md                               |  2 +-
 docs/qa/testing_guidelines.md           | 20 ++++++++++++---
 scripts/check.sh                        | 44 +++------------------------------
 5 files changed, 28 insertions(+), 66 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .github/workflows/repo-gate.yml
 M .github/workflows/sparrow-smoketest.yml
 M AGENTS.md
 M docs/qa/testing_guidelines.md
 M scripts/check.sh
?? canvases/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md
?? codex/codex_checklist/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_p1_3_sparrow_dependency_risk_reduction_vendor_fallback.yaml
?? codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.md
?? codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.verify.log
?? scripts/ensure_sparrow.sh
?? vendor/
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| Letrejott `scripts/ensure_sparrow.sh` prioritasi szabalyokkal, stdout csak bin path | PASS | `scripts/ensure_sparrow.sh` | A script a kert 1-4 prioritas szerint oldja fel/buildeli a Sparrow binarist, logolas stderr-re megy. | `./scripts/verify.sh --report ...` |
| `scripts/check.sh` `ensure_sparrow.sh`-t hasznal explicit `SPARROW_BIN` kompatibilitassal | PASS | `scripts/check.sh` | A regi clone/pin/build blokk helyett resolver hivas van, explicit `SPARROW_BIN` tovabbra is felulir. | `./scripts/verify.sh --report ...` |
| `sparrow-smoketest.yml` `ensure_sparrow.sh`-t hasznal + submodule recursive | PASS | `.github/workflows/sparrow-smoketest.yml` | A workflow mar nem duplikalja a build logikat, hanem resolverrel allitja be az env valtozot. | Workflow definicio review |
| `repo-gate.yml` checkout `submodules: recursive` | PASS | `.github/workflows/repo-gate.yml` | Checkout submodule opcio felveve jövobiztos vendor tamogatas miatt. | Workflow definicio review |
| `docs/qa/testing_guidelines.md` es `AGENTS.md` frissitve | PASS | `docs/qa/testing_guidelines.md`, `AGENTS.md`, `vendor/README.md` | Dokumentalva lett az uj resolver sorrend, env opciok es vendor/submodule gyakorlat. | Dokumentacio review |
| Verify PASS + report/log frissites | PASS | `codex/reports/egyedi_solver/p1_3_sparrow_dependency_risk_reduction_vendor_fallback.verify.log` | A verify wrapper futasa frissiti az AUTO blokkot es logot general. | `./scripts/verify.sh --report ...` |

## 8) Advisory notes (nem blokkolo)

- `vendor/sparrow` jelenleg opcionális; fallback `.cache` clone tovabbra is aktiv, ha vendor nincs.
