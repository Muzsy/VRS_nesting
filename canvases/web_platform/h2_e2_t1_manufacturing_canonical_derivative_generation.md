# H2-E2-T1 manufacturing_canonical derivative generation

## Funkcio
A feladat a H2 manufacturing geometry pipeline elso tenyleges implementacios lepese.
A cel, hogy a meglevo `app.geometry_derivatives` retegben a `manufacturing_canonical`
derivative is tenylegesen generalodjon a validalt canonical geometry truth-bol, es a
`part_revisions` explicit modon ugyanahhoz a source geometry revisionhoz tartozo
manufacturing derivative-re is tudjon hivatkozni.

A jelenlegi repoban a manufacturing profile domain es a project manufacturing selection
mar kapott H2-E1 alapot, viszont a geometry pipeline meg mindig csak
`nesting_canonical` + `viewer_outline` derivativet general. Ez a task ezt a hianyt zarja le.

Ez a task szandekosan nem manufacturing profile CRUD, nem project manufacturing selection,
nem contour classification, nem cut rule rendszer, nem snapshot manufacturing bovites,
nem worker/postprocess/export feladat. A scope kifejezetten az, hogy a H1-ben mar
mukodo geometry + part gerincre egy keskeny, auditálhato H2 nyito reteget tegyen.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a validalt `app.geometry_revisions` truth fole a `manufacturing_canonical`
    derivative tenyleges eloallitasa a meglevo `app.geometry_derivatives` tablaba;
  - az `api/services/geometry_derivative_generator.py` bovitese ugy, hogy a
    `manufacturing_canonical` payload ne aliasa legyen a `nesting_canonical`-nak,
    hanem kulon, manufacturing-felhasznalasra elokeszitett derivative legyen;
  - az `api/services/dxf_geometry_import.py` pipeline kiegeszitese ugy, hogy valid
    geometry eseten a manufacturing derivative is generalodjon;
  - a `part_revisions` minimal binding-bovitese ugy, hogy a part revision ugyanahhoz
    a `source_geometry_revision_id`-hez tartozo manufacturing derivative-re is tudjon
    hivatkozni;
  - az aktiv `app.create_part_revision_atomic(...)` fuggveny frissitese ugy, hogy
    opcionális manufacturing derivative id-t is tudjon fogadni es menteni;
  - az `api/services/part_creation.py` frissitese, hogy a part creation flow a
    `selected_nesting_derivative_id` mellett opcionálisan
    `selected_manufacturing_derivative_id`-t is rogzitse;
  - task-specifikus smoke script, amely bizonyitja a harom-derivative flow-t es a
    part bindinget.
- Nincs benne:
  - `app.manufacturing_profiles`, `app.manufacturing_profile_versions`,
    `app.project_manufacturing_selection` tovabbi bovitese vagy CRUD-ja;
  - `app.cut_rule_sets`, `app.cut_contour_rules` vagy barmilyen contour rule domain;
  - contour classification, cut rule matching, lead-in/out authoring;
  - snapshot builder vagy `manufacturing_manifest_jsonb` aktiv bekotese;
  - worker, manufacturing plan builder, preview, postprocessor vagy machine-ready export;
  - uj manufacturing route vagy frontend flow.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 celkep source-of-truth dokumentuma; kimondja, hogy a
    `manufacturing_canonical` kulon derivative-vilag legyen.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E2-T1 konkret task es a DoD.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - rogziti, hogy a geometry pipeline eloallitja a `nesting_canonical` es
    `manufacturing_canonical` derivative-eket, es hogy a manufacturing nem azonos
    a projectionnel vagy az exporttal.
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
  - rogziti a truth / derivative / projection / artifact szeparaciot.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - fontos boundary: a manufacturing kesobbi snapshot-vilag, nem elozheti meg a
    geometry derivative truth rendezett bevezeteset.
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
  - itt mar letezik a `geometry_derivative_kind` enum es benne a
    `manufacturing_canonical`.
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
  - a meglevo `app.geometry_derivatives` tabla; ezt kell tovabb hasznalni,
    nem uj legacy tablakat kitalalni.
- `api/services/geometry_derivative_generator.py`
  - a jelenlegi generator; most csak `nesting_canonical` es `viewer_outline`
    derivativet general.
- `api/services/dxf_geometry_import.py`
  - a valid geometry import pipeline aktualis bekotesi pontja.
- `supabase/migrations/20260317110000_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.sql`
  - a H1 minta arra, hogyan kot a `part_revisions` explicit derivative-re.
- `supabase/migrations/20260321120000_h1_e7_closure_lifecycle_and_storage_bucket_policies.sql`
  - a jelenleg aktiv `app.create_part_revision_atomic(...)` definicio.
- `api/services/part_creation.py`
  - a jelenlegi H1 part creation service, amely csak a `nesting_canonical`
    derivative-re epit.
- `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`
  - jo kiindulasi minta a derivative smoke-hoz.
- `scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`
  - jo kiindulasi minta a part binding smoke-hoz.

### Konkret elvarasok

#### 1. A manufacturing derivative maradjon geometry derivative, ne legyen se plan, se export
A `manufacturing_canonical`:
- a validalt canonical geometry truth-bol keszuljon;
- tovabbra is `app.geometry_derivatives` rekord legyen;
- ne tartalmazzon gepfuggo postprocess vagy machine-ready export logikat;
- ne valjon `run_artifact` vagy projection adattá.

#### 2. A manufacturing payload legyen kulon a nesting payloadtol
A `manufacturing_canonical` ne ugyanaz a payload legyen mas `derivative_kind` cimkevel.
A minimum elvart kulonbseg:
- legyen contour-orientaltabb, manufacturing-felhasznalasra elokeszitett szerkezet;
- a konturok stabil sorrenddel es determinisztikus JSON-al jelenjenek meg;
- az outer es hole vilag legalabb egyertelmuen szet legyen valasztva;
- ne legyen benne cut rule, lead-in/out vagy gepfuggo emit.

#### 3. A generator maradjon determinisztikus es idempotens
A `manufacturing_canonical` rekordban ugyanugy korrektul toltodjon:
- `producer_version`
- `format_version`
- `derivative_jsonb`
- `derivative_hash_sha256`
- `source_geometry_hash_sha256`

Ujrageneralas vagy retry eseten a `(geometry_revision_id, derivative_kind)` uniqueness
nem torhet el.

#### 4. A part revision binding ugyanarra a geometry truth-ra maradjon felfuzve
Ha a part revision manufacturing derivative-re hivatkozik, akkor:
- az ugyanahhoz a `source_geometry_revision_id`-hez tartozzon;
- ne lehessen idegen geometry revisionhoz tartozo manufacturing derivative-et bekotni;
- a H1-ben mar letezo nesting derivative binding logika ne seruljon.

#### 5. Ne nyisd ki idovel elott a manufacturing profile vagy cut rule scope-ot
Ebben a taskban nem szabad:
- manufacturing profile domain tablakat potolni vagy tovabb boviteni;
- project manufacturing selectiont modositani;
- snapshot manufacturing manifestet aktiv flow-va tenni;
- worker/postprocessor logikat hozzakeverni.

#### 6. A smoke bizonyitsa a ket kritikus H2-nyito invariansat
A task-specifikus smoke legalabb ezt bizonyitsa:
- valid geometry eseten letrejon a `nesting_canonical`, `viewer_outline` es
  `manufacturing_canonical`;
- a manufacturing derivative nem ures alias, hanem kulon payload;
- ujrageneralas nem hoz letre duplikalt manufacturing rekordot;
- part creation utan a revision ugyanahhoz a source geometry revisionhoz tartozo
  nesting es manufacturing derivative-re is tud hivatkozni;
- rejected geometry eseten manufacturing derivative sem jon letre.

### DoD
- [ ] A `manufacturing_canonical` derivative tenylegesen generalodik a meglevo `app.geometry_derivatives` tablaba.
- [ ] A task nem hoz letre uj legacy derivative tablakat.
- [ ] A `manufacturing_canonical` payload kulon marad a `nesting_canonical` payloadtol.
- [ ] A manufacturing derivative rekordok `producer_version`, `format_version`,
      `derivative_jsonb`, `derivative_hash_sha256` es
      `source_geometry_hash_sha256` mezoit korrektul toltjuk.
- [ ] A generator tovabbra is determinisztikus es idempotens.
- [ ] A `part_revisions` minimal binding-bovitest kap a manufacturing derivative-re,
      same-geometry integritassal.
- [ ] A H1 nesting derivative binding es a part creation jelenlegi mukodese nem romlik el.
- [ ] Valid geometry import eseten a manufacturing derivative automatikusan is generalodik.
- [ ] Rejected geometry eseten manufacturing derivative nem jon letre.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t1_manufacturing_canonical_derivative_generation.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a `manufacturing_canonical` valojaban ugyanaz marad, mint a `nesting_canonical`;
  - a task belenyit a manufacturing profile / cut rule / snapshot scope-ba;
  - a part revision binding integritasa fellazul;
  - a H1 part creation flow regressziot kap.
- Mitigacio:
  - explicit out-of-scope lista;
  - same-geometry FK/check mintakovetes a H1 derivative binding alapjan;
  - task-specifikus smoke a harom-derivative + part binding bizonyitasara;
  - selection/snapshot/export retegek erintetlenul hagyasa.
- Rollback:
  - a migration + service + smoke valtozasok egy task-commitban visszavonhatok;
  - ha a manufacturing derivative payload irany rossznak bizonyul, a H1 mukodes
    tovabbra is megtarthato, mert a nesting/viewer derivative vilag kulon marad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t1_manufacturing_canonical_derivative_generation.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/geometry_derivative_generator.py api/services/dxf_geometry_import.py api/services/part_creation.py scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
  - `python3 scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- `supabase/migrations/20260317110000_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.sql`
- `supabase/migrations/20260321120000_h1_e7_closure_lifecycle_and_storage_bucket_policies.sql`
- `api/services/geometry_derivative_generator.py`
- `api/services/dxf_geometry_import.py`
- `api/services/part_creation.py`
- `scripts/smoke_h1_e2_t4_geometry_derivative_generator_h1_minimum.py`
- `scripts/smoke_h1_e3_t1_part_creation_service_es_derivative_binding_h1_minimum.py`
