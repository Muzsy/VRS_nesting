# DXF Prefilter E1-T1 Product scope and contract freeze

## Funkcio
Ez a task a tervezett DXF eloszuro / normalizalo / acceptance gate lane **elso, szerzodesfagyaszto lepese**.
A cel most **nem implementacio**, hanem annak szigoru rogzitese, hogy a jelenlegi repoban mihez lehet biztonsagosan hozzanyulni, mi a V1 scope, mi nem scope, es hol kell a modult a mar meglevo upload -> geometry import -> part -> run lancba bekotni.

A task kifejezetten a **meglevo kodra** es a mar letezo web_platform boundary-kra kell, hogy rauljon:
- a repo mar tartalmaz egy valos DXF import/normalizalo magot (`vrs_nesting/dxf/importer.py`);
- mar van geometry import service es geometry validation report generator;
- a jelenlegi upload/geometry pipeline mar letezik, de nincs kulon deterministic DXF preflight/repair gate;
- a frontend jelenleg meg mindig a regi file-upload + new run wizard logikara tamaszkodik.

Ez a task azert kell elore, hogy a kesobbi DXF preflight backend es UI taskok ne kezdjenek szetesni kulonbozo, egymassal ellentmondo ertelmezesekre.

## Scope
- Benne van:
  - a DXF prefilter V1 celjanak es hatarainak rogzitese;
  - a kanonikus belso role-vilag rogzitese (`CUT_OUTER`, `CUT_INNER`, `MARKING`);
  - a szin mint input-hint, a layer mint belso truth elvenek rogzitese;
  - a jelenlegi backend bekotesi pontok azonositasanak es a jovobeli integracios helynek a rogzitese;
  - a jelenlegi frontend UX torz allapot es az uj `DXF Intake / Project Preparation` irany rogzitese;
  - egy dedikalt, repo-grounded scope/boundary dokumentum letrehozasa.
- Nincs benne:
  - Python backend implementacio;
  - uj API endpoint implementacio;
  - adatbazis migration;
  - preflight inspect / repair algoritmus kod;
  - frontend komponens implementacio;
  - review modal vagy popup megvalositasa;
  - geometry import pipeline tenyleges atkotese;
  - checklist/report verify tartalmi PASS bizonyitas a kodra (ez csak docs task).

## Talalt relevans fajlok (meglevo kodhelyzet)
- `vrs_nesting/dxf/importer.py`
  - a jelenlegi valos DXF importer, amely `CUT_OUTER` / `CUT_INNER` layer-vilaggal dolgozik;
  - mar most tud open path, multiple outer, invalid ring es hasonlo hibakkal fail-fast modon megallni;
  - erre kell majd a prefilter acceptance gate-nek visszatesztelnie, nem uj parhuzamos parserre.
- `api/services/dxf_geometry_import.py`
  - a jelenlegi source_dxf -> geometry revision pipeline belso belepesi pontja;
  - jelenleg importer + normalizer + validation report + derivative/classification lancot epit;
  - a prefilter modulnak **elegre**, nem helyette kell majd beallnia.
- `api/services/geometry_validation_report.py`
  - a kanonikus geometry payload validaciojat vegzi;
  - bizonyitja, hogy a rendszerben mar van egy kulon validacios retege, amire a prefilter gate tamaszkodhat.
- `api/services/dxf_validation.py`
  - jelenleg csak basic readability/log helper;
  - ezt nem szabad osszekeverni a tervezett teljes preflight/repair/acceptance gate-tel.
- `api/routes/files.py`
  - a jelenlegi file upload utani feldolgozasi lanchoz tartozik;
  - itt kell majd vilagosan eldonteni, hogy a preflight automatikus vagy explicit user-inditott legyen.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - a jelenlegi upload felulet;
  - most csak signed upload + metadata finalize vilagot kezel, preflight status vagy diagnostics nincs benne.
- `frontend/src/pages/NewRunPage.tsx`
  - a regi, file-id + stock/parts wizard szemleletu run indito felulet;
  - jelen allapotban nem jo hely egy DXF intake / diagnostics / review-flow betakolashoz.
- `canvases/web_platform/h1_e2_t1_dxf_parser_integracio.md`
  - jo referencia arra, hogyan kell egy web_platform taskot konkret kodhelyzetre ultetni.
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
  - referencia a mar letezo web_platform domain es schema szerzodesekhez.

## Jelenlegi repo-grounded helyzetkep
A repoban mar van:
- low-level DXF importer;
- geometry import service;
- geometry validation report;
- upload route;
- basic project file upload UI;
- legacy new-run wizard.

Ami **nincs**:
- kulon DXF preflight inspect engine;
- explicit repair/normalize reteg a file upload utan;
- rules profile schema es persistence;
- UI-s diagnostics/review flow;
- olyan acceptance gate, amely csak a tenylegesen importer+validator szerint futtathato DXF-et engedi tovabb.

Ezert a V1-nek nem szabad ugy indulnia, mintha nullarol kellene DXF motort epiteni; a helyes irany az, hogy a prefilter a meglevo importer/validator vilagra uljon ra.

## Konkret elvarasok

### 1. A belso truth layer-alapu maradjon
A V1 scope dokumentumban rogzitve legyen:
- a belso kanonikus role-vilag layer-alapu (`CUT_OUTER`, `CUT_INNER`, `MARKING`);
- a szin elso rangú input hint lehet;
- a normalizalt DXF kimenet mindig kanonikus layer-strukturat hasznal.

### 2. A V1 fail-fast legyen, ne okoskodo
Rogzitve legyen, hogy a V1:
- csak egyertelmu gap-fixet vegezhet `max_gap_close_mm` alatt;
- csak egyertelmu duplikalt zart konturt deduplikalhat;
- nyitott vagokonturt rejectel;
- nem valaszt automatikusan tobb outer jelolt kozul;
- nem talalgat bizonytalan topologianal.

### 3. A prefilter az importer + validator gate ele epuljon
Rogzitve legyen a jovobeli bekotesi pont:
- upload / finalize utan;
- geometry import elott;
- rejectelt vagy review-required file nem mehet geometry importba;
- accepted file mehet tovabb a meglevo geometry import service fele.

### 4. Az UI irany kulon intake/preparation oldal legyen
Rogzitve legyen, hogy:
- a jelenlegi `NewRunPage.tsx` legacy wizardot nem erdemes tovabb foltozni;
- a helyes irany egy uj `DXF Intake / Project Preparation` oldal;
- ezen legyen upload, rules profile / gyors beallitasok, preflight status, diagnostics, replace flow;
- es csak az accepted file-okbol lehessen geometry/part/run iranyba tovabblepni.

### 5. A task explicit kimenete egy stabil scope+boundary dokumentum legyen
A task ne probaljon meg allapotgepet, adatmodellt, API contractot es UI reszleteket teljessegukben egybefujni.
A kimenet most egy olyan stabil scope/boundary dokumentum legyen, amelyre a kovetkezo E1 taskok (glossary, policy matrix, state machine, data model, API contract) tisztan ra tudnak ulni.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t1_product_scope_and_contract_freeze.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze/run.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`

## DoD
- [ ] Letrejon egy dedikalt DXF prefilter V1 scope+boundary dokumentum a `docs/web_platform/architecture/` alatt.
- [ ] A dokumentum a meglevo kodhelyzetre epul, es explicit hivatkozik az importer, geometry import, validation es jelenlegi UI belepesi pontokra.
- [ ] Vilagosan rogziti a V1 in-scope es out-of-scope hatarokat.
- [ ] Kimondja, hogy a prefilter a meglevo importer+validator vilagra ul ra, nem uj parhuzamos DXF motor.
- [ ] Kimondja, hogy a belso truth layer-alapu, a szin input-hint.
- [ ] Kimondja, hogy a V1 fail-fast es csak egyertelmu javitasokat vegez.
- [ ] Kimondja, hogy a helyes UI irany kulon DXF Intake / Project Preparation oldal, nem a legacy NewRunPage tovabbi foltozasa.
- [ ] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz.
- [ ] A runner prompt egyertelmuen tiltja az idonkivuli implementacios scope creep-et.

## Kockazat + mitigacio + rollback
- Kockazat:
  - a task tul sok jovobeli dontest akar egyszerre befagyasztani;
  - a dokumentum elszakad a tenylegesen meglevo import/validation kodtol;
  - a UI tervet a jelenlegi legacy wizard logikajara probalja eroszakolni.
- Mitigacio:
  - csak scope+boundary freeze legyen, implementacio nelkul;
  - kotelezoen a meglevo importer / geometry import / validation / UI entrypoint fajlokra epuljon;
  - az uj intake oldal csak irany legyen, ne teljes UI-spec.
- Rollback:
  - docs-only task; a letrehozott dokumentumok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t1_product_scope_and_contract_freeze.md`
- Feladat-specifikus:
  - nincs uj kod-smoke; ez docs-only contract freeze task.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `canvases/web_platform/h1_e2_t1_dxf_parser_integracio.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `api/routes/files.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `api/services/dxf_validation.py`
- `vrs_nesting/dxf/importer.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
