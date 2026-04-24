Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne talalj ki uj accepted-files, geometry-list vagy parts bulk endpointot.
- A helyes T6 current-code modell most: **files route optional projection + DxfIntakePage parts-flow + meglvo POST /projects/{project_id}/parts route**.
- A file list projectionbol kell kiderulnie, hogy egy accepted file:
  - tenylegesen part-creation ready,
  - geometry import pending,
  - vagy nem eligible.
- Ne hozz letre uj persisted page-level draft domaint a code/name inputokhoz.
- A code/name draft page-local state legyen a DxfIntakePage-ben.
- A T4 diagnostics drawer es a T5 conditional review modal nem regresszalhat.
- Ne bovitsd a NewRunPage.tsx legacy wizardot.

Modellezesi elvek:
- A projection current-code truth szerint a file -> geometry -> part readiness bridge.
- Accepted allapot **nem** jelent automatikusan geometry-ready allapotot; ezt kulon kezelni kell.
- A frontend ne igerjen create akciot geometry-import-pending file-ra.
- A ready state csak akkor legyen igaz, ha a parts route-hoz szukseges geometry truth rendelkezesre all.
- Ha kis scope-ban minimalisan bizonyithato, hogy a geometry revisionbol mar keszult part,
  akkor ezt a projection jelezze es a UI kezelje. Ha ez nem fer bele determinisztikusan,
  ezt a reportban nevezd meg explicit deferred pontkent.
- A `suggested_code` / `suggested_name` lehet deterministic current-code prefill a file nevbol,
  de ne hozz letre kulon backend naming domaint.
- A frontend parts helper a jelenlegi backend request contractot kovesse (`code`, `name`, `geometry_revision_id`, opcionális `source_label`).
- A T6 ne nyisson meg project part requirements vagy accepted->sheet flow-t.

Kulon figyelj:
- a files route optional projectionje ne torje el a meglevo summary/diagnostics projectiont;
- a DxfIntakePage accepted blokkja kulonuljon el a latest preflight runs tablazattol;
- a create-part akcio utan legyen egyertelmu refresh / result state;
- a UX jelezze a pending es not-eligible allapotokat, ne csak hallgasson.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile api/routes/files.py scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`
- `python3 scripts/smoke_dxf_prefilter_e4_t6_accepted_files_to_parts_flow.py`
- `npm --prefix frontend run build`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t6_accepted_files_to_parts_flow.md`

A reportban kulon terj ki erre:
- miert optional files projection a helyes current-code backend oldal T6-hoz;
- hogyan kulonbozteti meg a T6 az accepted+ready vs accepted+pending vs not-eligible allapotot;
- pontosan hogyan epul a create-part flow a mar meglevo `POST /projects/{project_id}/parts` route-ra;
- hogyan marad regresszio nelkul a T4 diagnostics drawer es a T5 review modal.
