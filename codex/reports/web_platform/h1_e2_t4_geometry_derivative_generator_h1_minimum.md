PASS_WITH_NOTES

## 1) Meta
- Task slug: `h1_e2_t4_geometry_derivative_generator_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e2_t4_geometry_derivative_generator_h1_minimum.yaml`
- Futas datuma: `2026-03-16`
- Branch / commit: `main @ 0d4fa50 (dirty working tree)`
- Fokusz terulet: `API + Geometry derivatives + Smoke`

## 2) Scope

### 2.1 Cel
- Validalt geometry truth fole explicit derivative generator service bevezetese.
- `app.geometry_derivatives` tabla aktiv hasznalata ket H1 minimum kinddal: `nesting_canonical`, `viewer_outline`.
- Determinisztikus derivative payload/hash es kontrollalt ujrageneralas biztosítása.

### 2.2 Nem-cel
- `manufacturing_canonical` generalas.
- Part/sheet binding workflow.
- Run snapshot / orchestration.
- Uj domain migracio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Task artefaktok:**
  - `canvases/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h1_e2_t4_geometry_derivative_generator_h1_minimum.yaml`
  - `codex/prompts/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum/run.md`
  - `codex/codex_checklist/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md`
  - `codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md`
- **API / service:**
  - `api/services/geometry_derivative_generator.py`
  - `api/services/dxf_geometry_import.py`
- **Smoke:**
  - `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`

### 3.2 Miert valtoztak?
- A H1-E2-T3 utan mar rendelkezésre allt validated canonical geometry truth, de H1 minimum derivative reteg hianyzott.
- A valtozas ket cel-specifikus, query-zheto derivative-et general ugyanarra a geometry revisionre.
- Az import pipeline mar a validation utan automatikusan generalja a derivative-eket valid statusz mellett.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md` -> PASS

### 4.2 Opcionális, feladatfuggo ellenorzes
- `python3 -m py_compile api/services/geometry_derivative_generator.py api/services/dxf_geometry_import.py scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` -> PASS

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit geometry derivative generator service a validalt geometry truth fole. | PASS | `api/services/geometry_derivative_generator.py:217` | Kulon service kezeli a H1 minimum derivative generalast. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| A task a meglévo `app.geometry_derivatives` tablat hasznalja, nem uj legacy tablakat. | PASS | `api/services/geometry_derivative_generator.py:162`; `api/services/geometry_derivative_generator.py:185` | Select/insert/update a meglévo `app.geometry_derivatives` tablara történik. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| Letrejon legalabb a `nesting_canonical` es a `viewer_outline` derivative. | PASS | `api/services/geometry_derivative_generator.py:255`; `api/services/geometry_derivative_generator.py:265`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:327` | A service mindket kindot generalja; smoke ellenorzi a pontos kind-keszletet. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| A derivative rekordok `producer_version`, `format_version`, `derivative_jsonb`, `derivative_hash_sha256`, `source_geometry_hash_sha256` mezoi korrektul toltodnek. | PASS | `api/services/geometry_derivative_generator.py:146`; `api/services/geometry_derivative_generator.py:149`; `api/services/geometry_derivative_generator.py:152`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:335` | A payload minden required mezot kitolt, smoke ellenorzi a mezoket es hash-egyezest. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| A derivative payloadok determinisztikusak. | PASS | `api/services/geometry_derivative_generator.py:17`; `api/services/geometry_derivative_generator.py:76`; `api/services/geometry_derivative_generator.py:113`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:343` | Canonical JSON hash deterministic; smoke ujraszamolja es egyezest var. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| Ujrafuttatas eseten a `(geometry_revision_id, derivative_kind)` uniqueness nem torik el. | PASS | `api/services/geometry_derivative_generator.py:156`; `api/services/geometry_derivative_generator.py:164`; `api/services/geometry_derivative_generator.py:184`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:363`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:372` | Upsert logika existing rekordot update-el; smoke ellenorzi, hogy nem keletkezik duplikalt sor. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| A geometry import/validation lanc valid geometry eseten automatikusan general derivative-eket. | PASS | `api/services/dxf_geometry_import.py:216`; `api/services/dxf_geometry_import.py:226`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:323` | Validation utan az import flow automatikusan hivja a derivative generatort. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| Rejected geometry eseten nem jon letre derivative rekord. | PASS | `api/services/geometry_derivative_generator.py:227`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:390`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:427` | Service status-gate miatt `rejected` revisionnel skipel, smoke ellenorzi a nulla derivative sort. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| Parse/import failure eseten tovabbra sem jon letre hamis geometry revision vagy derivative. | PASS | `api/services/dxf_geometry_import.py:258`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:450`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:462` | Hibas DXF es hianyzo object agban nincs hamis revision/derivative. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| Keszul task-specifikus smoke script a derivative flow bizonyitasara. | PASS | `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:1`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:270`; `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py:506` | Uj smoke lefedi valid + regenerate + rejected + parse-failure agakat. | `python3 scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py` |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md:1`; `codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md:1` | Task-specifikus checklist/report kesz, DoD -> Evidence matrix kitoltve. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md` PASS. | PASS | `codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.verify.log:1`; `codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md:96` | Kotelezo gate wrapperrel futott, AUTO_VERIFY blokkban rogzitve. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A `viewer_outline` payload jelenleg geometriai outline adatot ad render hint-ekkel; export-artifact kepzes tovabbra sem ennek a tasknak a scope-ja.
- `manufacturing_canonical` es part/sheet workflow tovabbra is kulon (kesobbi) taskban marad.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-16T23:20:22+01:00 → 2026-03-16T23:23:47+01:00 (205s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.verify.log`
- git: `main@0d4fa50`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 api/services/dxf_geometry_import.py | 12 ++++++++++--
 1 file changed, 10 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/services/dxf_geometry_import.py
?? api/services/geometry_derivative_generator.py
?? canvases/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e2_t4_geometry_derivative_generator_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum/
?? codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.md
?? codex/reports/web_platform/h1_e2_t4_geometry_derivative_generator_h1_minimum.verify.log
?? scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py
```

<!-- AUTO_VERIFY_END -->
