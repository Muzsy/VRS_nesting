# DXF Prefilter E1-T2 Domain glossary and role model

## Funkcio
Ez a task a DXF prefilter lane masodik, **docs-only fogalomfagyaszto** lepese.
A cel most nem uj algoritmus vagy uj adatmodell implementacio, hanem annak
rogzitese, hogy a repoban mar letezo fogalmak es role-ok hogyan viszonyulnak
egymashoz, es a jovobeli DXF prefilter V1 milyen **egyseges szohasznalatot**
hasznalhat a tovabbi taskokban.

A task kozvetlenul a
`docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
dokumentum utan kovetkezik. A T1 mar rogzitette, hogy a modul acceptance gate lesz
az upload -> geometry import lanc ele epitve. A T2 feladata most az, hogy
megakadalyozza a fogalmi szetszalasztast a kovetkezo taskokban.

Kulonosen fontos a jelenlegi repoban mar most is letezo, de egymastol eltero
szintek tiszta szetvalasztasa:
- DXF layer-szintu szerepek az importerben (`CUT_OUTER`, `CUT_INNER`);
- geometry revision szintu szerep az adatmodellben (`app.geometry_role`: `part`, `sheet`);
- manufacturing derivative szintu kontur-szerep (`outer`, `hole`);
- jelenlegi frontend upload / wizard terminologia (`part_dxf`, `stock_dxf`, `source_dxf`).

Ha ez nincs lefagyasztva, a kesobbi policy matrix, state machine, data model,
API contract es UI taskok egymassal ellentmondo role-neveket kezdenek hasznalni.

## Scope
- Benne van:
  - a jelenlegi kodban mar letezo fogalmak es role-ok katalogusba rendezese;
  - a kulonbozo absztrakcios szintek (file, geometry revision, contour, UI) szetvalasztasa;
  - a jovobeli DXF prefilter V1 szamara hasznalando kanonikus terminologia rogzitese;
  - explicit mapping a jelenlegi kodhelyek es a jovobeli prefilter-szohasznalat kozott;
  - dedikalt glossary + role model dokumentum letrehozasa.
- Nincs benne:
  - SQL migration vagy enum modositas;
  - Python/TypeScript implementacio;
  - uj API endpoint;
  - UI komponens implementacio;
  - policy matrix reszletes szabalyhalmaz;
  - state machine vagy workflow allapotok teljes kidolgozasa;
  - review UX vagy popup szerzodes.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `vrs_nesting/dxf/importer.py`
  - a low-level importer jelenleg strict layer-konvencioval dolgozik;
  - `OUTER_LAYER_DEFAULT = "CUT_OUTER"`, `INNER_LAYER_DEFAULT = "CUT_INNER"`;
  - a role itt a DXF-layer szintjen jelenik meg.
- `api/services/dxf_geometry_import.py`
  - a geometry revision letrehozasanal a `geometry_role` jelenleg `"part"`;
  - ez nem ugyanaz, mint a kontur-szerep vagy a DXF layer-role.
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
  - `app.geometry_role` enum: `part`, `sheet`;
  - ez definition-side geometry szint, nem contour vagy layer-role.
- `api/services/geometry_derivative_generator.py`
  - a manufacturing canonical derivative a konturokra `contour_role` mezot hasznal;
  - jelenlegi ertekek: `outer`, `hole`.
- `api/services/geometry_contour_classification.py`
  - `contour_role` -> `contour_kind` atforditas mar most is kulon reteg;
  - bizonyitja, hogy a repoban a contour-level role kulon fogalmi szint.
- `api/routes/files.py`
  - a file finalize/upload oldal jelenleg `source_dxf` file-kindhoz kotott async geometry importot indit.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - a jelenlegi upload UI sajat `UploadKind = "stock_dxf" | "part_dxf"` lokal tipust hasznal;
  - ez legacy UI terminologia, nem vegleges domain truth.
- `frontend/src/pages/NewRunPage.tsx`
  - a legacy wizard `stock_file_id` / `parts_config` szohasznalattal dolgozik;
  - ez kulonosen fontos, mert nem szabad osszemosni a DXF prefilter role modellel.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - a T1 mar kimondja a layer-alapu belso truth + szin input-hint elvet;
  - a T2-nek ezt kell fogalmi katalogussa formalnia.

## Jelenlegi repo-grounded fogalmi problema
A repoban mar most tobb "role" szo letezik, de mas-mas absztrakcios szinten:
- geometry revision role = `part` / `sheet`;
- contour role = `outer` / `hole`;
- DXF layer role = `CUT_OUTER` / `CUT_INNER`;
- jovobeli prefilter role = `CUT_OUTER` / `CUT_INNER` / `MARKING`;
- frontend upload kind = `part_dxf` / `stock_dxf`;
- file-kind = `source_dxf`.

A T2-ben ezt expliciten szet kell valasztani, kulonben a kovetkezo taskokban a
`role`, `kind`, `layer`, `geometry_role`, `contour_role`, `file_kind`,
`upload_kind` terminusok osszemosodnak.

## Konkret elvarasok

### 1. Kesz legyen egy dedikalt glossary + role model dokumentum
Az uj dokumentum ne altalanos szoveg legyen, hanem hasznalhato referencia a
kovetkezo taskokhoz.

Minimum kotelezo szekciok:
- fogalomcel es miert van szukseg ra;
- absztrakcios szintek;
- terminology table / glossary;
- role taxonomy;
- tiltott osszemosasok / anti-pattern lista;
- ajanlott szohasznalat a tovabbi DXF prefilter taskokhoz.

### 2. A dokumentum kulonitse el a kulonbozo role-szinteket
Kotelezoen legyen explicit kulonvalasztva legalabb ez a 4 szint:
- file/object-level terminologia;
- geometry revision-level terminologia (`part`, `sheet`);
- contour-level terminologia (`outer`, `hole`);
- DXF prefilter canonical layer-role vilag (`CUT_OUTER`, `CUT_INNER`, `MARKING`).

### 3. A `MARKING` szerep csak prefilter V1 glossary-szintjen legyen rogzitve
A dokumentumnak ki kell mondania, hogy:
- `MARKING` a jovobeli prefilter canonical role-vilag resze;
- ez jelenleg meg nincs bekotve a geometry import / derivative / UI stackbe;
- ettol fuggetlenul a glossary-ban rogziteni kell, hogy a kovetkezo taskok
  egysegesen hasznaljak.

### 4. A frontend legacy terminologia ne valjon source-of-truth-za
Rogzitve legyen, hogy:
- `stock_dxf` / `part_dxf` jelenleg UI-level, legacy upload megnevezes;
- `source_dxf` a jelenlegi file-kind/domain oldali terminus;
- ezek nem ugyanazok, mint a contour- vagy layer-role-ok.

### 5. Legyen explicit tiltott osszemosas lista
A dokumentumban kulon szerepeljen, hogy mit nem szabad egynek tekinteni:
- `geometry_role` != `contour_role`
- `contour_role` != `DXF layer role`
- `file_kind` != `upload_kind`
- `stock_file` != `sheet geometry revision`
- `part_dxf` != `CUT_OUTER`

### 6. A dokumentum legyen hasznalhato input a kovetkezo taskokhoz
A T2 kimenete a T3/T4/T5 taskok inputja kell legyen:
- policy matrix
- state machine
- data model
- API contract
- UI labels/esetek

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t2_domain_glossary_and_role_model.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model/run.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md`

## DoD
- [ ] Letrejon a `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md` dokumentum.
- [ ] A dokumentum explicit kulonvalasztja a file/object, geometry revision, contour es DXF prefilter layer-role szinteket.
- [ ] A dokumentum konkrétan a jelenlegi kodra hivatkozik (`importer.py`, `dxf_geometry_import.py`, migration enum, `geometry_derivative_generator.py`, `ProjectDetailPage.tsx`, `NewRunPage.tsx`).
- [ ] Rogziti, hogy a jovobeli canonical prefilter role-vilag: `CUT_OUTER`, `CUT_INNER`, `MARKING`.
- [ ] Rogziti, hogy a `MARKING` jelenleg glossary-szintu future canonical role, nem mar implementalt geometry import truth.
- [ ] Rogziti, hogy a frontend legacy upload terminologia nem source-of-truth.
- [ ] Tartalmaz egy tiltott osszemosas / anti-pattern listat.
- [ ] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz.
- [ ] A runner prompt egyertelmuen tiltja a scope creep-et (nincs implementacio, nincs enum- vagy schema-modositas ebben a taskban).

## Kockazat + mitigacio + rollback
- Kockazat:
  - a glossary tul absztrakt lesz, es nem a konkret kodhoz kotodik;
  - a dokumentum mar most uj enumokat vagy allapotokat talal ki implementacios fedezet nelkul;
  - a legacy UI/fajl terminusok tevesen domain truth-kent lesznek rogzitve.
- Mitigacio:
  - kotelezoen a jelenlegi kodfajlokra kell hivatkozni;
  - kulon jelolni kell, mi current-code truth es mi future canonical prefilter term;
  - docs-only boundary maradjon, nincs semmilyen kod- vagy schema-valtoztatas.
- Rollback:
  - docs-only task; a letrehozott dokumentumok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md`
- Feladat-specifikus:
  - nincs uj kod-smoke; ez docs-only glossary task.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/geometry_contour_classification.py`
- `api/routes/files.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
