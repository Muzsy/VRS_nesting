# DXF Prefilter E4-T6 — Accepted files -> parts flow

## Cel
Az E4-T5 vege ota a `DxfIntakePage` mar tudja:
- a source DXF feltoltest,
- a latest preflight summary + diagnostics megjelenitest,
- review-required file-oknal a conditional review modal + replacement upload flow-t.

A jelenlegi repo-grounded hiany viszont az, hogy az `accepted_for_import` kimenetu file-oknal a UX ma csak
advisory szintig jut el (`Ready for next step`). Nincs tenyleges, kozvetlen kapcsolat a DXF intake felulet es a
meglevo part creation domain kozott.

Pedig a current-code truth szerint a backend oldalon mar letezik:
- a preflight gate utani geometry import (`api/services/dxf_preflight_runtime.py`),
- a geometry revision truth a `source_file_object_id` kapcsolattal,
- a `POST /projects/{project_id}/parts` route a `geometry_revision_id`-ra epitve (`api/routes/parts.py`).

Ezert az E4-T6 helyes current-code scope-ja:
**accepted file-okhoz egy minimalis, de valodi parts-flow bekotese a DxfIntakePage-en**, a mar meglevo
geometry import + parts route hasznalataval.

## Miert most?
A jelenlegi kodbazisban mar megvan minden elozo lepcso:
- E3-T3 gate miatt csak accepted file-bol indul geometry import,
- E3-T4 replacement flow miatt a hibas file javithato,
- E4-T3 tabla mutatja az accepted allapotot,
- E4-T4/T5 ad diagnostics/review UX-et.

A kovetkezo logikus, repo-grounded tovabblepes ezert nem uj review-domain vagy uj intake oldal,
hanem az accepted file-okbol **kozvetlen tovabblepes part letrehozasra**.

## Scope boundary

### In-scope
- A `GET /projects/{project_id}/files` route minimalis, optional projection bovitese egy olyan file-level
  `latest_part_creation_projection` mezovel, amely current-code truth szerint eleg a parts-flowhoz.
- A projection a file + latest acceptance allapot + geometry import truth alapjan adjon UI-barat readiness informaciot.
- Frontend type/API boundary ehhez az optional projectionhoz.
- `DxfIntakePage`-en kulon `Accepted files -> parts` szekcio.
- Accepted file-ok csoportositasa es csak accepted file-ok felajanlasa parts-flowra.
- Ready file-oknal editable, page-local `code` es `name` draft mezok.
- Minimalis frontend helper a meglevo `POST /projects/{project_id}/parts` route-hoz.
- Egyedi `Create part` akcio es/vagy csoportszintu `Create ready parts` akcio ugyanarra a backend route-ra epitve.
- A flow tiltsa vagy disable-je:
  - rejected file-okat,
  - review-required file-okat,
  - accepted, de meg geometry-import-pending file-okat,
  - es (ha projectionbol bizonyithato) azokat a file-okat, amelyekhez mar van letrehozott part.
- Task-specifikus smoke.

### Out-of-scope
- Uj backend `parts/bulk` endpoint.
- Uj historical geometry list endpoint.
- Uj parts list/detail page.
- Project part requirements flow.
- Sheet creation flow.
- Accepted -> parts utan automatikus project bindings.
- Review modal, diagnostics drawer vagy replacement flow redesign.
- NewRunPage bovites.
- Uj persisted UI draft domain a code/name draftoknak.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `frontend/src/pages/DxfIntakePage.tsx`
  - mar van latest preflight tabla, diagnostics drawer, review modal, replacement upload.
- `frontend/src/lib/api.ts`
  - van file upload/replace/list helper, de nincs parts-flow helper.
- `frontend/src/lib/types.ts`
  - van latest summary/diagnostics type boundary, de nincs part-creation projection.
- `api/routes/files.py`
  - mar tud optional summary/diagnostics projectiont, de nincs accepted->parts projection.
- `api/routes/parts.py`
  - mar letezik a valodi part creation route `geometry_revision_id` alapon.
- `api/services/dxf_preflight_runtime.py`
  - accepted outcome utan mar triggere-li a geometry importot a normalized DXF artifactrol.
- `api/services/dxf_geometry_import.py`
  - a geometry revision `source_file_object_id` szerint kapcsolodik a file-hoz.
- `canvases/web_platform/dxf_prefilter_e3_t3_geometry_import_gate_integration.md`
- `canvases/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md`
- `canvases/web_platform/dxf_prefilter_e4_t5_conditional_review_modal.md`

## Jelenlegi repo-grounded helyzetkep

### 1. Accepted advisory mar van, de mutalo flow meg nincs
Az E4-T3 ota a tabla accepted file-ra ezt mutatja:
- acceptance badge: `accepted`
- recommended action: `Ready for next step`

Ez azonban ma meg csak advisory szoveg, nem tenyleges tovabblepesi UX.

### 2. A backend parts route mar current-code truth
A `POST /projects/{project_id}/parts` route mar meglevo domain entrypoint. A route a kovetkezot ker:
- `code`
- `name`
- `geometry_revision_id`
- opcionális `description`, `notes`, `source_label`

Ez azt jelenti, hogy az intake felulet jelenlegi legkisebb helyes T6 scope-ja:
- szerezzuk meg a file-hoz tartozo megfelelo `geometry_revision_id` truthot,
- majd hivjuk a mar letezo parts route-ot.

### 3. A jelenlegi file list projection nem eleg a parts-flowhoz
A `list_project_files(... include_preflight_summary/include_preflight_diagnostics)` ma csak preflight truthot ad.
A frontend nem latja belole:
- hogy a gate utan geometry import tenylegesen kesz-e,
- hogy melyik `geometry_revision_id` hasznalhato,
- hogy mar keszult-e part ugyanebbol a geometry revisionbol.

Ezert a T6 helyes backend oldali minimuma egy **uj optional file-level projection**, nem uj endpoint.

### 4. A geometry import allapotot current-code szerint gracefully kell kezelni
Mivel az accepted outcome utan indul a geometry import, a T6 UX-nek kulon kezelnie kell:
- `accepted` + `geometry ready`
- `accepted` + `geometry import pending`

Nem jo irany egy olyan UX, ami accepted allapot eseten automatikusan feltetelezi,
hogy a geometry revision mar elerheto.

## Konkret elvarasok

### 1. Minimalis optional part-creation projection a files route-on
A `GET /projects/{project_id}/files` kapjon egy uj optional query flaget, peldaul:
- `include_part_creation_projection=true`

Ennek hatasara file-onkent jojjon egy **optional** projection, peldaul:
- `latest_part_creation_projection`

Minimum current-code mezok:
- `geometry_revision_id: string | null`
- `geometry_revision_status: string | null`
- `part_creation_ready: boolean`
- `readiness_reason: string`
- `suggested_code: string`
- `suggested_name: string`
- `source_label: string`
- opcionálisan, ha bizonyithato es minimalisan kinyerheto:
  - `existing_part_definition_id`
  - `existing_part_revision_id`
  - `existing_part_code`

A projection szabalyai:
- non-accepted file-nal ne legyen hamis ready state;
- accepted, de geometry nelkul -> `part_creation_ready=false`, `readiness_reason=geometry_import_pending`;
- accepted + validated geometry + nesting derivative rendelkezésre áll -> `part_creation_ready=true`;
- ha mar van ugyanebbol a geometry revisionbol part, akkor a projection ezt kulon jelezze.

### 2. A projection ne hozzon uj endpointot vagy uj persistence domaint
Nem jo irany:
- uj `/projects/{project_id}/accepted-files` endpoint,
- uj parts wizard endpoint,
- uj persisted page-level part-draft domain.

A helyes T6 current-code megoldas:
- a meglvo files list projection minimalis bovitese,
- a meglvo parts POST route hasznalata.

### 3. Frontend API/type boundary
A frontend kapja meg az uj optional projection tipusait, es egy minimalis helper-t a parts route-hoz,
peldaul:
- `createProjectPart(...)`

A helper a jelenlegi backend request contractra epit:
- `code`
- `name`
- `geometry_revision_id`
- opcionálisan `source_label`

### 4. A DxfIntakePage-en legyen kulon Accepted files -> parts blokk
A page-en legyen egy kulon szekcio, amely:
- csak accepted file-okat csoportositja,
- kulon megmutatja a `ready` vs `pending` vs `already created` allapotot,
- es valodi parts-flow akciot ad.

A minimum UX lehet:
- lista vagy tabla accepted file-okra,
- file-onkent prefillelt `code` es `name` draft,
- per-row `Create part` gomb,
- opcionálisan egy `Create ready parts` bulk CTA, ami a ready sorokon vegigmegy.

### 5. A code/name draft current-code szerint page-local legyen
A T6 ne hozzon be uj persisted draft domaint.
A prefill current-code szerint jo lehet:
- `suggested_code` a file nev stemjebol,
- `suggested_name` ugyanennek emberibb valtozata,
- `source_label` az eredeti file nev.

A draft page-local state maradjon.

### 6. Tiltas rejectelt/review-required allapotban
A T6 explicit tiltsa vagy rejtse el a part creation akciot olyan file-oknal, amelyek:
- `preflight_rejected`
- `preflight_review_required`
- vagy nincs `accepted_for_import`

Ez kozertheto legyen a UI-ban is, ne csak csendben maradjon nincs-gomb allapot.

### 7. Geometry import pending allapot kezelese
Accepted file-nal, ha a geometry revision meg nem all rendelkezésre,
a UX mutasson egyertelmu allapotot, peldaul:
- `Geometry import pending`
- `Refresh after import`

Ne igerjen reszben mukodo `Create part` akciot ilyen esetben.

### 8. Optional duplicate/already-created vedelem
Ha minimalis projectionnel kinyerheto, hogy ugyanebbol a geometry revisionbol mar keszult part,
a UX ezt mutassa es ne ajanlja fel ujra alaptelmezetten a create akciot.

Ha ez current-code mellett nem bizonyithato kis scope-ban, akkor a canvas ezt nevezze meg optional/deferrable pontkent,
de ne talaljon ki nem letezo uniqueness garanciat.

### 9. Bizonyitas
Minimum deterministic evidence:
- task-specifikus smoke, amely bizonyitja:
  - bent van az optional part-creation projection token a files route-on;
  - bent van az uj frontend API/type boundary;
  - a DxfIntakePage accepted files blokkot renderelo tokenek bent vannak;
  - a create-part flow csak accepted/ready allapotra epit;
  - a review/rejected/pending allapotokhoz nincs hamis aktiv create CTA.
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report ...` PASS

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow/run.md`
- `api/routes/files.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/DxfIntakePage.tsx`
- `scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`
- `codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`

## DoD
- [ ] A files route kap egy optional, minimalis part-creation projectiont uj endpoint nelkul.
- [ ] A projection eleg informaciot ad ahhoz, hogy a frontend eldontse: accepted + ready / accepted + pending / not eligible.
- [ ] A frontend kap uj types/API helper boundaryt a parts-flowhoz.
- [ ] A DxfIntakePage-en megjelenik egy kulon `Accepted files -> parts` blokk.
- [ ] Rejected/review-required file-okra nincs hamis aktiv create-part flow.
- [ ] Accepted, de geometry-import-pending file-ra a UX egyertelmuen pending allapotot mutat.
- [ ] Ready file-ra tenylegesen hivhato a meglvo `POST /projects/{project_id}/parts` route.
- [ ] A code/name draft page-local, current-code prefill alapra epul; nincs uj persisted draft domain.
- [ ] A T4 diagnostics drawer es a T5 review modal nem regresszal.
- [ ] Keszul task-specifikus smoke.
- [ ] `npm --prefix frontend run build` PASS.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md` PASS.
