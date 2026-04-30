PASS

## 1) Meta
- Task slug: `cavity_t7_ui_observability`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_t7_ui_observability.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t7_ui_observability.yaml`
- Futas datuma: `2026-04-29`
- Branch / commit: `main` (dirty working tree)
- Fokusz terulet: `DXF Intake + Run Detail cavity observability`

## 2) Scope

### 2.1 Cel
- DXF Intake diagnostics drawerben cavity observability blokk megjelenitese, ha az API ad adatot.
- Run Detail strategy/audit szekcioban cavity prepack summary megjelenitese, ha `viewer-data` ad cavity summaryt.
- Additiv backend+frontend valtoztatassal backward kompatibilitas fenntartasa.

### 2.2 Nem-cel (explicit)
- Nem cavity algoritmus fejlesztes.
- Nem New Run Wizard rejected/review/pending filtering valtoztatas.
- Nem exporter vagy cut-order tema.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `api/routes/files.py`
- `api/routes/runs.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/dxfIntakePresentation.ts`
- `frontend/src/pages/DxfIntakePage.tsx`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/e2e/cavity_prepack_observability.spec.ts`
- `scripts/smoke_cavity_t7_ui_observability.py`
- `codex/codex_checklist/nesting_engine/cavity_t7_ui_observability.md`
- `codex/reports/nesting_engine/cavity_t7_ui_observability.md`

### 3.2 Mi valtozott es miert
- Preflight oldalon additiv `cavity_observability` mezot vezettem be summary/diagnostics payloadba, a mar elerheto `acceptance_summary.importer_probe.hole_count` tenyadat alapjan.
- Run `viewer-data` valaszba additiv `cavity_prepack_summary` kerult az `engine_meta.cavity_prepack` blokkal.
- Frontenden:
  - DXF Intake diagnostics drawer uj "Cavity observability" szekciot kapott.
  - Run Detail audit kartya uj "Cavity prepack summary" blokkot kapott.
  - A Run Detail cavity blokk csak akkor jelenik meg, ha a summary erdemi adatot hordoz.
- New Run Wizard filtering logikahoz nem nyultam.

## 4) Verifikacio

### 4.1 Feladatfuggo ellenorzes
- `cd frontend && npm run build` -> PASS
- `python3 scripts/smoke_cavity_t7_ui_observability.py` -> PASS
- `cd frontend && npx playwright test e2e/cavity_prepack_observability.spec.ts` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t7_ui_observability.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| DXF Intake cavity diagnostics adat elerheto | PASS | `api/routes/files.py` (`_build_cavity_observability_from_acceptance_summary`) | Additiv `cavity_observability` summary + diagnostics payloadban. | smoke_t7 |
| Run Detail cavity prepack summary API szinten elerheto | PASS | `api/routes/runs.py` (`ViewerDataResponse.cavity_prepack_summary`) | `engine_meta.cavity_prepack` tovabbitva viewer-data valaszba. | smoke_t7 + e2e |
| DXF Intake UI cavity blokk megjelenik adatokkal | PASS | `frontend/src/pages/DxfIntakePage.tsx` + `frontend/e2e/cavity_prepack_observability.spec.ts` (1. teszt) | Diagnosztika drawerben `section_cavity` blokk renderelve. | playwright |
| Run Detail UI cavity blokk csak adatokkal jelenik meg | PASS | `frontend/src/pages/RunDetailPage.tsx` + `frontend/e2e/cavity_prepack_observability.spec.ts` (2. teszt) | `showCavityPrepackSummary` feltetel gatingeli a renderelest. | playwright |
| Copy presentation modulon keresztul | PASS | `frontend/src/lib/dxfIntakePresentation.ts` | Uj `section_cavity` es `cavity_not_computed` copy kulcsok. | build + smoke |
| New Run Wizard filtering valtozatlan | PASS | nincs wizard file diff; `scripts/smoke_cavity_t7_ui_observability.py` git-diff check | T7 scope-ban nincs wizard filtering diff. | smoke_t7 |

## 6) Advisory notes
- A preflight oldali `cavity_observability` jelenleg csak importer-hole alapu diagnosztika; usable/invalid cavity split itt nincs kiszamolva.
- Ez szandekosan nem allit full hole-aware kepesseget; observability szintet ad.

## 7) Follow-up
- Kovetkezo lepes: `cavity_t8_production_regression_benchmark`.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-29T22:56:29+02:00 → 2026-04-29T22:59:08+02:00 (159s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_t7_ui_observability.verify.log`
- git: `main@88a8760`
- módosított fájlok (git status): 22

**git diff --stat**

```text
 api/routes/files.py                       |  17 ++
 api/routes/runs.py                        |   4 +
 frontend/src/lib/api.ts                   |  28 +++
 frontend/src/lib/dxfIntakePresentation.ts |   2 +
 frontend/src/lib/types.ts                 |  19 ++
 frontend/src/pages/DxfIntakePage.tsx      |  21 ++
 frontend/src/pages/RunDetailPage.tsx      |  26 +++
 worker/result_normalizer.py               | 323 ++++++++++++++++++++++++++----
 8 files changed, 405 insertions(+), 35 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M api/routes/runs.py
 M frontend/src/lib/api.ts
 M frontend/src/lib/dxfIntakePresentation.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/DxfIntakePage.tsx
 M frontend/src/pages/RunDetailPage.tsx
 M worker/result_normalizer.py
?? codex/codex_checklist/nesting_engine/cavity_t5_result_normalizer_expansion.md
?? codex/codex_checklist/nesting_engine/cavity_t6_svg_dxf_export_validation.md
?? codex/codex_checklist/nesting_engine/cavity_t7_ui_observability.md
?? codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.md
?? codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.verify.log
?? codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.md
?? codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.verify.log
?? codex/reports/nesting_engine/cavity_t7_ui_observability.md
?? codex/reports/nesting_engine/cavity_t7_ui_observability.verify.log
?? frontend/e2e/cavity_prepack_observability.spec.ts
?? scripts/smoke_cavity_t5_result_normalizer_expansion.py
?? scripts/smoke_cavity_t6_svg_dxf_export_validation.py
?? scripts/smoke_cavity_t7_ui_observability.py
?? tests/worker/test_result_normalizer_cavity_plan.py
```

<!-- AUTO_VERIFY_END -->
