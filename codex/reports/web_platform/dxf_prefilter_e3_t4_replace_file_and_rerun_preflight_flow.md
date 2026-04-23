# Report — dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow

## Összefoglaló

Az E3-T4 bevezeti az explicit `POST /projects/{project_id}/files/{file_id}/replace` replace action route-ot,
minimális persisted replacement lineage truth-ot (`replaces_file_object_id` nullable self-FK az `app.file_objects`
táblában), és bizonyítja, hogy replacement finalize után a meglévő E3-T2 auto-preflight runtime implicit
módon újraindul — külön manuális rerun endpoint nélkül.

## Miért a replace action route a helyes current-code irány

Az API contract docs (`dxf_prefilter_api_contract_specification.md`) már korábban rögzítette a canonical
replace action endpointot: `POST /projects/{project_id}/files/{file_id}/replace`. A meglévő upload flow
kétlépéses (`upload-url` → signed upload → `complete_upload`); a replace action ehhez igazodik úgy, hogy
csak egy új upload slotot nyit — a finalize-t nem végzi el maga. Ez biztosítja, hogy:
- a replace action és a normális upload finalize flow azonos `complete_upload` kódútvonalat használ;
- nem duplikálódik a validációs logika;
- a replace action router-szinten validálja, hogy a target file létezik, a projekthez tartozik és `source_dxf` jellegű.

## Miért implicit a rerun és miért nincs külön rerun endpoint

Az E3-T2 óta a source DXF `complete_upload` finalize automatikusan regisztrálja a két background taskot:
1. `validate_dxf_file_async` — legacy DXF readability check;
2. `run_preflight_for_upload` — a teljes T1→T7 + E3-T1 pipeline.

A replacement finalize ugyanezt a `complete_upload` kódútvonalat járja be, az új replacement file_id-vel.
Ezért a "rerun" nem más, mint egy új upload finalize — külön endpoint nélkül. A canvas és a state machine
docs szerint ez a current-code truth; egy manuális rerun endpoint felesleges komplexitást és divergenciát
vinne be.

## Hogyan maradnak meg auditként a korábbi preflight runok

Az `app.preflight_runs` tábla `source_file_object_id`-hoz köti a futásokat. A replacement nem írja felül
a régi `file_objects` sort — helyette egy új sort hoz létre az új file_id-vel, és a régi file_objects row
érintetlen marad. Ezért a régi file-hoz tartozó preflight runok (`source_file_object_id = <régi file_id>`)
auditként megmaradnak, és a listázás során is elérhetők maradnak.

## Miért kell minimális persisted lineage truth

Az API contract docs replace action route-ot specifikál — nem puszta UI szöveget. Ezért az E3-T4-ben
nem elég response payloadban jelezni, hogy "ez replacement": szükség van persisted truth-ra is.
A helyes V1 megoldás egy nullable self-FK (`replaces_file_object_id uuid null references app.file_objects(id)
on delete restrict`) az `app.file_objects` táblán. Ez:
- explicit lineage kapcsolatot teremt az új és a régi file között;
- nem igényel külön replacement táblát;
- nem írja felül in-place a régi sort;
- kompatibilis a meglévő insert_row flow-val.

## Mit bizonyítanak a unit tesztek és a smoke-ok

**Unit tesztek** (`tests/test_dxf_preflight_replace_flow.py`):
- `test_replace_route_returns_signed_upload_slot`: replace route source_dxf targetra signed URL-t és új file_id-t ad vissza;
- `test_replace_route_rejects_non_source_dxf_target`: artifact/svg target → 400 hiba;
- `test_replace_route_rejects_wrong_project_target`: más projekthez tartozó file → 404 hiba;
- `test_complete_upload_replacement_finalize_persists_lineage`: replacement finalize esetén az új file_objects row `replaces_file_object_id`-t kap;
- `test_complete_upload_replacement_registers_two_background_tasks`: replacement finalize után pontosan 2 background task regisztrálódik (validate + preflight);
- `test_no_manual_rerun_endpoint_exists`: nincs `rerun` nevű route az app routerein.

**Smoke** (`scripts/smoke_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.py`):
- replace route → signed upload URL + új file_id + replacement target evidence;
- finalize replacement → új file row + lineage truth (`replaces_file_object_id` persisted);
- background task az új replacement file_id-re indul;
- az eredeti file_objects row érintetlen marad.

## Mi marad E3-T5 / későbbi UI scope-ban

- **E3-T5**: feature flag / rollout gate a replacement flow kapuzásához.
- **E4**: UI button a `DxfIntakePage`-en a replace flow elindításához.
- Superseded file hiding/grouping UX és historical lineage table.
- Artifact download/detail API a replacement lineage mentén.
- Review decision workflow.
- Régi storage object automatikus törlése.
- Geometry revision cleanup.

## DoD → Evidence Matrix

| DoD feltétel | Evidence |
|---|---|
| `POST /projects/{project_id}/files/{file_id}/replace` route létrejött | `api/routes/files.py`: `replace_file` route |
| Route csak létező, projekthez tartozó source_dxf targetra működik | `test_replace_route_rejects_*` unit tesztek |
| Replacement upload flow a meglévő signed-upload + `complete_upload` mintára épül | `FileReplaceResponse` mezői megegyeznek az `UploadUrlResponse`-zal; `test_replace_route_returns_signed_upload_slot` |
| `FileCompleteRequest` kap optional replacement bridge mezőt | `FileCompleteRequest.replaces_file_object_id` |
| `file_objects` domainben persisted replacement lineage truth jön létre | Migration SQL + `test_complete_upload_replacement_finalize_persists_lineage` |
| Replacement finalize után meglévő auto-preflight runtime az új file-ra indul | `test_complete_upload_replacement_registers_two_background_tasks` |
| Nem jön létre külön manuális rerun endpoint | `test_no_manual_rerun_endpoint_exists` |
| Nem történik régi file in-place felülírása | `complete_upload` mindig INSERT, soha UPDATE; smoke bizonyítja |
| Task-specifikus unit teszt és smoke elkészült | `tests/test_dxf_preflight_replace_flow.py`, `scripts/smoke_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.py` |
| `./scripts/verify.sh` PASS | AUTO_VERIFY_START blokk: **PASS**, check.sh exit 0, git `main@571c08f` |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-23T21:20:47+02:00 → 2026-04-23T21:23:37+02:00 (170s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.verify.log`
- git: `main@571c08f`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 api/routes/files.py | 96 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 96 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
?? canvases/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.yaml
?? codex/prompts/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow/
?? codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.md
?? codex/reports/web_platform/dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.verify.log
?? scripts/smoke_dxf_prefilter_e3_t4_replace_file_and_rerun_preflight_flow.py
?? supabase/migrations/20260424100000_dxf_e3_t4_replace_file_and_rerun_preflight_flow.sql
?? tests/test_dxf_preflight_replace_flow.py
```

<!-- AUTO_VERIFY_END -->
