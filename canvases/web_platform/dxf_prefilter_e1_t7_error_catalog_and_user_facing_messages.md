# DXF Prefilter E1-T7 Error catalog es user-facing uzenetek

## Funkcio
Ez a task a DXF prefilter lane hetedik, **docs-only error-catalog es user-facing message freeze** lepese.
A cel most nem backend exception forditor implementacio, nem API response model, nem frontend i18n/lokalizacio,
nem toast/banner komponens es nem route-level hibakezeles ujradratozasa, hanem annak rogzitese,
hogy a jovobeli DXF prefilter V1 milyen **stabil hibakatalogust** es milyen **felhasznaloi uzenet-rendszert**
hasznaljon a meglvo file ingest -> preflight -> geometry import -> validation -> run flow menten.

A tasknak a jelenlegi repora kell raulnie:
- ma a `vrs_nesting/dxf/importer.py` stabil, strukturalt `DxfImportError(code, message)` kodokat dob `DXF_*` prefixszel;
- ma a `api/services/geometry_validation_report.py` issue objektumokat general `code`, `severity`, `path`, `message`, `details` mezokkel;
- ma a `docs/error_code_catalog.md` mar rogzit egy runtime error formatumot es kodprefix-listat;
- ma az API es frontend tobb ponton nyers `err.message` vagy `run.error_message` szoveget jelenit meg (`ProjectDetailPage`, `NewRunPage`, `ViewerPage`, `RunDetailPage`);
- ma nincs kulon DXF prefilter error catalog dokumentum, nincs user-facing message contract, nincs support/debug evidence matrix a preflight domainre.

Ez a task azert kell, hogy a kesobbi E2/E3/E4 implementacios taskok ne ad hoc modon talaljak ki:
- mely kodok stabil, user-visible kataloguselemmek,
- mely nyers importer/validator hibak maradhatnak debug evidence szinten,
- milyen user-facing cim / magyarazo uzenet / javasolt kovetkezo lepes tartozik egy-egy hibacsaladhoz,
- mit kell a UI-n mutatni, es mit kell csak report/debug reszben megtartani.

## Scope
- Benne van:
  - a current-code error truth felterkepezese a DXF/import/validation/UI retegekben;
  - a future canonical DXF prefilter error catalog docs-level rogzitese;
  - stabil kodcsoportok es severity szintek rogzitese;
  - user-facing cim / magyarazo uzenet / suggested action / debug evidence elvek docs-szintu rogzitese;
  - kulonvalasztas a technical detail es a user-facing szoveg kozott;
  - anti-scope lista, hogy mi nem tartozik ebbe a taskba.
- Nincs benne:
  - Python/FastAPI exception translator implementacio;
  - frontend komponens, toast, banner vagy modal implementacio;
  - localization/i18n infrastruktura;
  - `api/routes/*.py`, `api/services/*.py` vagy `frontend/src/*` modositas;
  - OpenAPI hibaresponse schema kidolgozas;
  - support tooling implementacio.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `vrs_nesting/dxf/importer.py`
  - current-code truth: stabil `DXF_*` hibakodok es nyers technikai uzenetek.
- `api/services/dxf_geometry_import.py`
  - current-code truth: a geometry import hibakat logolja (`geometry_import_failed ... error=%s`), de nem forditja kulon user-facing katalogusra.
- `api/services/dxf_validation.py`
  - current-code truth: file-level readability/parse jellegu hibak logolasa.
- `api/services/geometry_validation_report.py`
  - current-code truth: strukturalt issue lista `code`, `severity`, `path`, `message`, `details` mezokkel.
- `docs/error_code_catalog.md`
  - current-code truth: global runtime error code formatum es prefix policy.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - current-code truth: upload/delete hibaknal nyers `err.message` vagy fallback string megy a UI-ra.
- `frontend/src/pages/NewRunPage.tsx`
  - current-code truth: run wizard hibaknal nyers `err.message` vagy fallback string.
- `frontend/src/pages/RunDetailPage.tsx`
  - current-code truth: failed run eseten nyers `run.error_message` jelenik meg.
- `frontend/src/pages/ViewerPage.tsx`
  - current-code truth: viewer adatbetoltes hibaja nyers `err.message` vagy fallback string.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - T1 output; rogziti, hogy a prefilter acceptance gate a file ingest utan, geometry import elott lep be.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - T2 output; role es terminology truth.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - T3 output; policy es rules profile fogalmi alap.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - T4 output; lifecycle retegek es statusz-szeleteles.
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
  - T5 output; future diagnostics/adatok persistence irany.
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
  - T6 output; future canonical HTTP API surface.

## Jelenlegi repo-grounded helyzetkep
A repoban ma mar vannak stabil technikai hibaforrasok, de nincs kulon DXF prefilter user-facing message rendszer.
A jelenlegi truth-kep:
- importer oldalon stabil `DXF_*` kodok vannak, de a szoveg technikai es sokszor tul nyers user-facing celra;
- geometry validator oldalon strukturalt issue-k vannak, de ezek nyelvezete tovabbra is technical-detail kozeli;
- frontend oldalon tobb helyen a nyers backend/exception message megy ki piros dobozba;
- run oldalon a `run.error_message` gyakorlatilag nyers backend string;
- nincs kulon szabaly arra, hogy mely hibak jelenjenek meg user-facing cimmel, melyekkel kell suggested action, es mely technical detail maradjon csak debug evidence.

Ezert a T7-ben nem szabad ugy tenni, mintha ma mar lenne pl.
- `api/services/dxf_prefilter_error_messages.py`,
- frontend translation registry,
- vagy UI-ready structured error response contract.
A helyes output most egy **architecture-level error catalog and user-facing message specification**,
amelyet a kesobbi E2/E3/E4 taskok implementalnak backend translatorba es frontend megjelenitesbe.

## Konkret elvarasok

### 1. Current-code error truth es future canonical catalog legyen explicit kulonvalasztva
A dokumentumnak kulon kell kezelnie:
- mely hibakodok, message formak es severity mechanizmusok leteznek ma mar a repoban;
- melyik ezek kozul tekintheto stabil catalog-forrasnak;
- mi lesz a future canonical DXF prefilter user-facing error catalog, es mi marad nyers debug evidence.

### 2. A dokumentum grounded inventoryt adjon a jelenlegi hibaforrasokrol
Minimum kulon blokkok kellenek:
- importer `DXF_*` kodok (`vrs_nesting/dxf/importer.py`);
- geometry validation issue kodok (`api/services/geometry_validation_report.py`);
- global runtime error kodformatum (`docs/error_code_catalog.md`);
- jelenlegi frontend nyers hibamegjelenitesi pontok.

A dokumentum ne teljes kodlista masolat legyen, hanem grounded kategoriak + reprezentativ kodok + forrashelyek.

### 3. A future canonical catalog kategoriak legyenek a meglvo kodra ultetve
A dokumentumnak legalabb a kovetkezo csaladokat kell lefagyasztania:
- file ingest / upload boundary hibak;
- DXF parse / readability / unsupported input hibak;
- contour / topology / layer contract hibak;
- repair-policy hibak (gap, duplicate, ambiguity);
- acceptance-gate hibak;
- geometry validation hibak;
- review-required allapotok;
- replace/rerun user-flowhoz tartozo informacios es warning allapotok.

Kulon legyen kimondva, hogy melyik csalad current-code truth-ra epul, es melyik future canonical extension.

### 4. Minden canonical katalogus elemhez legyen user-facing contract
A dokumentum rogzitse, hogy egy canonical catalog elem minimum mezoi:
- `code`
- `severity`
- `title`
- `user_message`
- `suggested_action`
- `debug_evidence_source`
- opcionisan `support_notes`

Kulon legyen kimondva, hogy a `user_message` nem azonos a nyers technical exceptionnel.

### 5. Severity es presentation elvek legyenek docs-szinten rogzitve
Legalabb ezek legyenek megkulonboztetve:
- `error`
- `warning`
- `info`
- `review_required`

A dokumentum mondja ki, melyik milyen UI viselkedest indokol a jovoben
(pl. blokkol, tovabbenged figyelmeztetessel, vagy review actiont ker).
De ez maradjon docs-szintu UX contract, ne komponens implementacio.

### 6. A dokumentum kulon valassza szet a user-facing uzenetet es a debug evidence-t
Rogzitse, hogy a jovobeli rendszerben:
- a UI-ban rovid, ertelmezheto cim+uzenet+kovetkezo lepes jelenik meg;
- a nyers importer/validator detail kulon debug/diagnostics feluleten vagy reportban marad;
- a support/debug oldalon meg kell maradnia a nyers code/path/details evidence-nek.

### 7. A dokumentum mutasson canonical mapping mintakat a jelenlegi kodokbol
Minimum grounded mapping peldak:
- `DXF_NO_OUTER_LAYER`
- `DXF_OPEN_OUTER_PATH`
- `DXF_OPEN_INNER_PATH`
- `DXF_MULTIPLE_OUTERS`
- `DXF_UNSUPPORTED_ENTITY_TYPE`
- `DXF_UNSUPPORTED_UNITS`
- legalabb nehany `GEO_*` validator kod

A cel nem a teljes kodlista hard freeze, hanem a mapping-elv dokumentalasa valos kodokkal.

### 8. Legyen explicit anti-scope lista
Kulon legyen kimondva, hogy ebben a taskban nem szabad:
- backend translator/service kodot irni;
- frontend page vagy component fajlt modositani;
- API response modelt vagy OpenAPI hibaformatumot definialni implementacios reszletesseggel;
- localization rendszert kitalalni;
- support workflow-t implementalni.

### 9. A dokumentum mondja ki a kapcsolodast a T4/T5/T6 outputokhoz
Kulon rogzitse, hogy:
- a T4 lifecycle miatt kell kulon error vs review_required allapot;
- a T5 future diagnostics persistence miatt kell structured code/severity/message contract;
- a T6 API contract miatt a canonical catalog majd a preflight run/read modelben jelenik meg,
  de annak HTTP szerzodese nem T7-ben keszul.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages/run.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t7_error_catalog_and_user_facing_messages.md`

## DoD
- [ ] Letrejon a `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md` dokumentum.
- [ ] A dokumentum explicit kulonvalasztja a current-code error truthot es a future canonical DXF prefilter error catalogot.
- [ ] A dokumentum grounded inventoryt ad a relevans jelenlegi hibaforrasokrol (importer, validator, global error catalog, frontend nyers hibapontok).
- [ ] A dokumentum rogziti a canonical catalog kategoriakat es a minimum catalog-item mezoket.
- [ ] A dokumentum kulon kezeli a severity/presentation elveket es a user-facing vs debug evidence szetvalasztast.
- [ ] A dokumentum valos, jelenlegi kodokra epulo mapping peldakat tartalmaz.
- [ ] A dokumentum explicit anti-scope listat tartalmaz.
- [ ] Nem jon letre vagy modosul implementacios backend/frontend/API/OpenAPI fajl.
