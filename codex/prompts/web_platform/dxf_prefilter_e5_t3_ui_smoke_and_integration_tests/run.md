Olvasd el az `AGENTS.md` szabalyait, es szigoruan a jelenlegi repo-grounded kodra epits.

Feladat:
Valositsd meg a `canvases/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`
canvasban leirt taskot a hozza tartozo YAML szerint.

Kotelezo elvek:
- Ne vezess be uj frontend tesztframeworkot; a helyes current-code stack a meglovo Playwright harness.
- Ne indits valodi backendet vagy Supabase-t a UI tesztekhez; auth bypass + mock API legyen a truth.
- Ne nyiss uj backend endpointot vagy query parametert csak a UI teszt miatt.
- Ne nyiss review modal, accepted->parts, replace/rerun vagy redesign scope-ot.
- Az E5-T3 nem replacement az E5-T2-höz; a browser spec ne route-level backend E2E legyen, hanem mocked UI integration.
- A "tovabbengedes" current-code truth szerint accepted advisory allapot legyen (`Ready for next step`), ne valodi mutalo gomb.
- Ha a mock API harness bovul, az csak a DxfIntakePage current-code flow deterministic seedelesere es request capture-jere terjedjen ki.

Modellezesi elvek:
- Hasznald a meglovo `frontend/playwright.config.ts` auth bypass + baseURL + mock API mintajat.
- Preferalt belépési pont: `await installMockApi(page, options?)`.
- A mock API supportban kezeld explicit modon:
  - `latest_preflight_summary`
  - `latest_preflight_diagnostics`
  - `rules_profile_snapshot_jsonb` finalize payload capture
  - source_dxf upload finalize utani file-list state frissites
- Javasolt dedikalt spec file: `frontend/e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`.

Minimum scenario-k:
1. settings panel -> upload finalize bridge
   - nyisd meg a DxfIntakePage-et egy seedelt projektre;
   - allits be nem-default settings ertekeket;
   - uploadolj source DXF-et;
   - bizonyitsd, hogy a finalize requestben a `rules_profile_snapshot_jsonb` a vart ertekekkel ment ki;
   - a row megjelenik / a user latja az upload completion allapotot.

2. accepted latest run -> diagnostics drawer
   - seedelj accepted latest summary + diagnostics payloadot;
   - bizonyitsd az accepted badge-et es a `Ready for next step` ajanlast;
   - nyisd meg a diagnostics drawert;
   - bizonyitsd a fo blokkokat: Source inventory, Role mapping, Issues, Repairs, Acceptance, Artifacts.

3. non-accepted latest run vizualis allapot
   - seedelj legalabb egy review_required vagy rejected file-t;
   - bizonyitsd a megfelelo acceptance badge-et es ajanlott kovetkezo lepest;
   - ne legyen teves accepted advisory allapot;
   - ha van diagnostics payload, a drawer maradjon megnyithato.

Kulon figyelj:
- a DxfIntakePage current-code selectoraihoz igazodj; ne talalj ki felesleges UI API-t csak a teszt kenyelmeert;
- ha a mock API vagy a page a11y-hook nelkul is stabilan tesztelheto, ne modositsd a production oldalt;
- a diagnostics drawer read-only maradjon;
- az artifact blokkot local reference truthkent kezeld, ne signed download linkkent.

A feladat vegen kotelezoen fusson:
- `python3 -m py_compile scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `npm --prefix frontend run build`
- `cd frontend && npx playwright test e2e/dxf_prefilter_e5_t3_dxf_intake.spec.ts`
- `python3 scripts/smoke_dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.py`
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`

A reportban kulon terj ki erre:
- miert mocked browser integration a helyes E5-T3 current-code truth, nem backend E2E es nem uj tesztframework;
- hogyan bizonyitja a pack a settings -> finalize payload bridge-et;
- hogyan bizonyitja a diagnostics drawer legfontosabb blokkjait;
- hogyan ertelmezi current-code truth szerint a "tovabbengedest" accepted advisory allapotkent.
