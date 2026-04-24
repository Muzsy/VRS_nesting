# Report — dxf_prefilter_e4_t6_accepted_files_to_parts_flow

## Összefoglaló

Az E4-T6 a `DxfIntakePage`-en külön `Accepted files -> parts` blokkot vezet be, amely a meglévő
files list route optional projectionjére és a már létező `POST /projects/{project_id}/parts` végpontra épül.
Nem jött létre új accepted-files endpoint, geometry list endpoint vagy parts bulk route.

## Miért optional files projection a helyes current-code backend megoldás T6-hoz

A current-code útvonalban a file-list már létező read entrypoint (`GET /projects/{project_id}/files`) köré épül az intake UX.
A T6-hoz szükséges readiness truth (`accepted` állapot + geometry revision + nesting derivative + existing part jelzés)
nem igényel külön workflow endpointot: a meglévő list route optional projectiongel bővíthető regresszió nélkül.

Ezért a backend oldalon a megoldás:
- `include_part_creation_projection` query flag,
- file-onként `latest_part_creation_projection` mező,
- és ugyanazon response-ben továbbra is működő summary/diagnostics projection.

## Állapotmodell: accepted+ready vs accepted+pending vs not-eligible

A T6 explicit readiness reason modellel különbözteti meg az állapotokat:
- accepted + ready: `accepted_ready`
- accepted + pending: pl. `accepted_geometry_import_pending`, `accepted_geometry_not_validated`, `accepted_missing_nesting_derivative`
- accepted + already created: `accepted_existing_part`
- not eligible: `not_eligible_review_required`, `not_eligible_rejected`, `not_eligible_preflight_pending`, `not_eligible_no_preflight_run`, `not_eligible_file_kind`

A frontend ezeket badge + magyarázó szöveg formában jeleníti meg, és csak accepted+ready esetben engedi a create akciót.

## A create-part flow pontos bekötése a meglévő parts route-ra

A page flow nem hoz létre új create endpointot. A művelet:
1. `api.createProjectPart(...)` hívás a `POST /projects/{project_id}/parts` route-ra
2. request payload: `code`, `name`, `geometry_revision_id`, opcionális `source_label`
3. create után `loadData()` refresh fut, és a result state UI-ban visszajelzett

Ez pontosan a meglévő backend request contractot követi.

## T4/T5 regressziómentesség

A `DxfIntakePage` korábbi T4/T5 funkciói érintetlenül megmaradtak:
- T4 diagnostics drawer (`View diagnostics`, `Diagnostics` blokkok)
- T5 conditional review modal (`Open review`, `Conditional review modal`, replacement flow)

A T6 accepted-files blokk külön szekcióban van, nem olvasztja össze és nem írja felül a latest preflight tábla,
diagnostics drawer vagy review modal viselkedését.

## Érintett fájlok

- `api/routes/files.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/DxfIntakePage.tsx`
- `scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`

## Verifikáció

- `python3 -m py_compile api/routes/files.py scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py` -> PASS
- `python3 scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py` -> PASS
- `npm --prefix frontend run build` -> PASS
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md` -> PASS
- Megjegyzés: a build által módosított `frontend/tsconfig.tsbuildinfo` visszaállítva, így a végső diff csak task-output fájlokat tartalmaz.

## DoD -> Evidence Matrix

| DoD pont | Státusz | Evidence |
| --- | --- | --- |
| A files route kap optional part-creation projectiont új endpoint nélkül. | PASS | `api/routes/files.py:843`; `api/routes/files.py:940` |
| A projection külön kezeli az accepted+ready / accepted+pending / not-eligible állapotokat. | PASS | `api/routes/files.py:529`; `api/routes/files.py:563`; `api/routes/files.py:572`; `api/routes/files.py:526` |
| A frontend type/API boundary elkészült a parts-flowhoz. | PASS | `frontend/src/lib/types.ts:140`; `frontend/src/lib/types.ts:155`; `frontend/src/lib/api.ts:227`; `frontend/src/lib/api.ts:385` |
| A DxfIntakePage külön `Accepted files -> parts` blokkot mutat. | PASS | `frontend/src/pages/DxfIntakePage.tsx:1087`; `frontend/src/pages/DxfIntakePage.tsx:1115` |
| Rejected/review-required/pending állapotoknál nincs hamis aktív create flow. | PASS | `frontend/src/pages/DxfIntakePage.tsx:324`; `frontend/src/pages/DxfIntakePage.tsx:330`; `frontend/src/pages/DxfIntakePage.tsx:336`; `frontend/src/pages/DxfIntakePage.tsx:1178` |
| Accepted+pending esetben explicit pending UX jelzés látszik. | PASS | `frontend/src/pages/DxfIntakePage.tsx:300`; `frontend/src/pages/DxfIntakePage.tsx:1193` |
| Ready file ténylegesen a meglévő `POST /projects/{project_id}/parts` route-ot hívja. | PASS | `frontend/src/lib/api.ts:390`; `frontend/src/pages/DxfIntakePage.tsx:690` |
| A code/name draft page-local marad, nincs új persisted draft domain. | PASS | `frontend/src/pages/DxfIntakePage.tsx:380`; `frontend/src/pages/DxfIntakePage.tsx:438`; `frontend/src/pages/DxfIntakePage.tsx:646` |
| A T4 diagnostics drawer és T5 review modal nem regresszál. | PASS | `frontend/src/pages/DxfIntakePage.tsx:1071`; `frontend/src/pages/DxfIntakePage.tsx:1213`; `frontend/src/pages/DxfIntakePage.tsx:1335` |
| Elkészült task-specifikus smoke. | PASS | `scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py:1` |
| `npm --prefix frontend run build` PASS. | PASS | build output: `tsc -b && vite build` sikeres |
| `./scripts/verify.sh --report ...` PASS. | PASS | AUTO_VERIFY blokk (`eredmény: PASS`, `check.sh exit 0`) |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-24T00:35:50+02:00 → 2026-04-24T00:38:42+02:00 (172s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.verify.log`
- git: `main@b63dde0`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 api/routes/files.py                  | 295 +++++++++++++++++++++++++++-
 frontend/src/lib/api.ts              |  45 ++++-
 frontend/src/lib/types.ts            |  36 ++++
 frontend/src/pages/DxfIntakePage.tsx | 366 ++++++++++++++++++++++++++++++++++-
 frontend/tsconfig.tsbuildinfo        |   2 +-
 5 files changed, 738 insertions(+), 6 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M frontend/src/lib/api.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/DxfIntakePage.tsx
 M frontend/tsconfig.tsbuildinfo
?? canvases/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.yaml
?? codex/prompts/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow/
?? codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md
?? codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.verify.log
?? scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py
```

<!-- AUTO_VERIFY_END -->
