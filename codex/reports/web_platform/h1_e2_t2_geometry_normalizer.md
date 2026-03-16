PASS_WITH_NOTES

## 1) Meta
- Task slug: `h1_e2_t2_geometry_normalizer`
- Kapcsolodo canvas: `canvases/web_platform/h1_e2_t2_geometry_normalizer.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e2_t2_geometry_normalizer.yaml`
- Futas datuma: `2026-03-16`
- Branch / commit: `main @ 73fb8e6 (dirty working tree)`
- Fokusz terulet: `API + Geometry normalizer + Smoke`

## 2) Scope

### 2.1 Cel
- A H1-E2-T1 parse eredmenyebol explicit normalizer reteggel stabil canonical geometry truth eloallitasa.
- A `geometry_revisions` rekordok normalized payload/hash/bbox/format_version kitoltese.
- Determinisztikussag bizonyitasa ismetelt feldolgozas mellett.

### 2.2 Nem-cel
- `geometry_validation_reports` generalas (H1-E2-T3).
- `geometry_derivatives` generalas (H1-E2-T4).
- Uj geometry query endpoint vagy part/sheet workflow.
- Uj domain migracio.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Task artefaktok:**
  - `canvases/web_platform/h1_e2_t2_geometry_normalizer.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h1_e2_t2_geometry_normalizer.yaml`
  - `codex/prompts/web_platform/h1_e2_t2_geometry_normalizer/run.md`
  - `codex/codex_checklist/web_platform/h1_e2_t2_geometry_normalizer.md`
  - `codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md`
- **API / service:**
  - `api/services/dxf_geometry_import.py`
  - `api/routes/files.py`
- **Smoke:**
  - `scripts/smoke_h1_e2_t2_geometry_normalizer.py`

### 3.2 Miert valtoztak?
- A korabbi payload `part_raw.v1` importer-kimenet kozeli forma volt, nem lezart canonical truth.
- A valtozas explicit normalizer reteget ad a parser fole determinisztikus ring policy-val.
- A smoke mar a normalized payload szerkezetet es ismetelheto hash-et ellenorzi.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md` -> PASS

### 4.2 Opcionális, feladatfuggo ellenorzes
- `python3 -m py_compile api/services/dxf_geometry_import.py api/routes/files.py scripts/smoke_h1_e2_t2_geometry_normalizer.py` -> PASS
- `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` -> PASS

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| A geometry import lancban kulon, explicit normalizer lepes jon letre a parser folott. | PASS | `api/services/dxf_geometry_import.py:83`; `api/services/dxf_geometry_import.py:184` | A parse utan kulon `_normalize_part_raw_geometry(...)` lepes fut, amely a canonical payloadot allitja elo. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A normalizer a meglévo `vrs_nesting.dxf.importer.import_part_raw` eredmenyere epul, nem uj parserre. | PASS | `api/services/dxf_geometry_import.py:12`; `api/services/dxf_geometry_import.py:182` | A service tovabbra is a meglévo importer fugvenyt hivja, parhuzamos parser nelkul. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A `geometry_revisions.canonical_geometry_jsonb` mezője determinisztikus normalized payloadot tartalmaz. | PASS | `api/services/dxf_geometry_import.py:89`; `api/services/dxf_geometry_import.py:97`; `api/services/dxf_geometry_import.py:207`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:360` | Ring orientacio, canonical startpoint es hole-rendezes utan a payload stabil; smoke ellenorzi az ismetelt payload egyezest. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A normalized payload explicit outer/hole ring szerkezetet hordoz stabil metaadatokkal. | PASS | `api/services/dxf_geometry_import.py:101`; `api/services/dxf_geometry_import.py:102`; `api/services/dxf_geometry_import.py:104`; `api/services/dxf_geometry_import.py:116`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:305` | A payload explicit `outer_ring`, `hole_rings`, `normalizer_meta`, `source_lineage` mezoket tartalmaz, smoke validalja. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A `canonical_hash_sha256` a normalized payloadbol szerveroldalon kepzodik. | PASS | `api/services/dxf_geometry_import.py:127`; `api/services/dxf_geometry_import.py:189`; `api/services/dxf_geometry_import.py:208`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:343` | A hash canonical JSON dumpbol kepzodik, smoke ujraszamolja es ellenorzi. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A `bbox_jsonb` a normalized geometry-val konzisztensen toltodik. | PASS | `api/services/dxf_geometry_import.py:56`; `api/services/dxf_geometry_import.py:95`; `api/services/dxf_geometry_import.py:103`; `api/services/dxf_geometry_import.py:210`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:333` | A bbox ugyanabbol a normalized ring keszletbol szamolodik es bekerul a payloadba + DB oszlopba, smoke egyezest ellenoriz. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A `canonical_format_version` a normalized truth-ot tukrozi. | PASS | `api/services/dxf_geometry_import.py:17`; `api/services/dxf_geometry_import.py:99`; `api/services/dxf_geometry_import.py:206`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:291` | A format verzio atallt `normalized_geometry.v1` ertekre payloadban es tablaban is. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| Ugyanabbol a source DXF-bol ismetelt feldolgozasnal konzisztens canonical payload/hash keletkezik. | PASS | `scripts/smoke_h1_e2_t2_geometry_normalizer.py:347`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:360`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:362` | A smoke ugyanarra a source file-ra masodik revisiont keszit, es payload/hash egyezest var el. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| Parse hiba eseten nem jon letre felrevezeto normalizalt geometry revision rekord. | PASS | `api/services/dxf_geometry_import.py:240`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:385`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:397`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:417`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:433` | Hibas DXF vagy hianyzo storage objektum eseten nem keletkezik hamis parsed/normalized revision. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| Keszul task-specifikus smoke script a determinisztikus normalizalas bizonyitasara. | PASS | `scripts/smoke_h1_e2_t2_geometry_normalizer.py:1`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:231`; `scripts/smoke_h1_e2_t2_geometry_normalizer.py:439` | Az uj smoke script endpoint flow + normalizer determinisztikussag bizonyitekot ad. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A files ingest flow normalized truth-ra igazodik hash-truth szinten. | PASS | `api/routes/files.py:226`; `api/routes/files.py:228`; `api/routes/files.py:265` | A route explicit `source_hash_sha256` truth ellenorzest vegez es ezt adja at a geometry import tasknak. | `python3 scripts/smoke_h1_e2_t2_geometry_normalizer.py` |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e2_t2_geometry_normalizer.md:1`; `codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md:1` | Task-specifikus checklist/report elkeszult DoD -> Evidence matrixszal. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md` PASS. | PASS | `codex/reports/web_platform/h1_e2_t2_geometry_normalizer.verify.log:1`; `codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md:96` | A kotelezo gate wrapperrel fut, az AUTO_VERIFY blokk tartalmazza az eredmenyt. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A normalizer scope itt szandekosan csak geometry truth stabilizalas; validation report es derivative generalas kulon task marad.
- A route hash-ellenorzese miatt hianyos metadata esetben a flow mar a file_objects insert elott megall.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-16T21:39:15+01:00 → 2026-03-16T21:42:53+01:00 (218s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e2_t2_geometry_normalizer.verify.log`
- git: `main@73fb8e6`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 api/routes/files.py                 |   8 ++-
 api/services/dxf_geometry_import.py | 120 ++++++++++++++++++++++++++++--------
 2 files changed, 99 insertions(+), 29 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M api/services/dxf_geometry_import.py
?? canvases/web_platform/h1_e2_t2_geometry_normalizer.md
?? codex/codex_checklist/web_platform/h1_e2_t2_geometry_normalizer.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e2_t2_geometry_normalizer.yaml
?? codex/prompts/web_platform/h1_e2_t2_geometry_normalizer/
?? codex/reports/web_platform/h1_e2_t2_geometry_normalizer.md
?? codex/reports/web_platform/h1_e2_t2_geometry_normalizer.verify.log
?? scripts/smoke_h1_e2_t2_geometry_normalizer.py
```

<!-- AUTO_VERIFY_END -->
