# Cavity v2 T09 — Report és observability bővítés
TASK_SLUG: cavity_v2_t09_report_observability

## Szerep
Senior full-stack (Python + TypeScript) coding agent vagy. A result report és a frontend UI cavity prepack observability bővítését végzed.

## Cél
`metrics_jsonb.cavity_plan` v2 specifikus mezőkkel bővül. TypeScript `cavity_prepack_summary` típus frissítve. Frontend UI cavity prepack összefoglaló panel megjelenik ha `cavity_plan.enabled`.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t09_report_observability.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t09_report_observability.yaml`
- `worker/result_normalizer.py` (metrics_jsonb cavity_plan blokk ~sor 978-983, _normalize_solver_output_projection_v2 teljes)
- `frontend/src/lib/types.ts` (cavity_prepack_summary ~sor 355, QualityProfileName ~sor 372)
- `frontend/src/pages/NewRunPage.tsx` (result megjelenítési rész)
- T07 artefaktumok (normalizer v2 flatten implementálva)
- T02 artefaktumok (QualityProfileName kibővítve)

## Engedélyezett módosítás
- `worker/result_normalizer.py`
- `frontend/src/lib/types.ts`
- `frontend/src/pages/NewRunPage.tsx`
- `tests/worker/test_result_normalizer_cavity_plan.py`

## Szigorú tiltások
- **Tilos a v1 cavity_plan metrics formátumát megváltoztatni.**
- Tilos új API endpoint-ot létrehozni.
- Tilos a cavity prepack algoritmust módosítani.
- A frontend panel **csak** `{cavity_plan.enabled && ...}` guard mögé kerülhet.
- Tilos a meglévő metrics_row struktúrát törni.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Olvasd el a `metrics_jsonb["cavity_plan"]` blokk pontos helyét a result_normalizer.py-ban (`grep -n "cavity_plan" worker/result_normalizer.py`).

### Step 2: worker/result_normalizer.py bővítése
- `_count_diagnostics_by_code()` helper implementálása (ha T07-ben nem készült)
- v2 ág bővítése a canvas spec 13 v2 mezőjével
- V1 ág: csak az egyszerű formátum marad

### Step 3: frontend/src/lib/types.ts bővítése
`cavity_prepack_summary` típus kiegészítése: `quantity_delta_summary`, `diagnostics_by_code`, `max_cavity_depth` mezők.

### Step 4: frontend/src/pages/NewRunPage.tsx panel
Guard mögé:
```tsx
{result?.metrics_jsonb?.cavity_plan?.enabled && (
  <div className="cavity-prepack-summary">...
```
A canvas spec szerinti 6 adatsor.

### Step 5: TypeScript build + tesztek
```bash
cd frontend && npx tsc --noEmit
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
```
Két új teszt: `test_v2_metrics_contain_cavity_plan_summary`, `test_v1_metrics_unchanged`.

### Step 6: Checklist és report
### Step 7: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t09_report_observability.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py
cd frontend && npx tsc --noEmit
```

## Ellenőrzési pontok
- [ ] metrics_jsonb.cavity_plan v2 esetén tartalmazza az összes új mezőt
- [ ] V1 cavity_plan metrics formátum változatlan
- [ ] TypeScript types frissítve
- [ ] Frontend panel guard mögé van téve
- [ ] TypeScript build hibátlan
- [ ] test_v2_metrics_contain_cavity_plan_summary zöld
- [ ] test_v1_metrics_unchanged zöld

## Elvárt végső jelentés
Magyar nyelvű report. DoD→Evidence. metrics_jsonb.cavity_plan v2 mező lista (fájl:sor).

## Hiba esetén
Ha a `metrics_jsonb["cavity_plan"]` blokk nem ott van ahol vártad, grep-pel keresd: `grep -n "cavity_plan" worker/result_normalizer.py`. Ha TypeScript típus konfliktus van, ellenőrizd a meglévő `cavity_prepack_summary` típus struktúráját.
