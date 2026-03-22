# H2-E3-T1 cut rule set model

## Funkcio
A feladat a H2 cut rule rendszer elso, tenylegesen implementalhato lepese.
A cel, hogy a gyartasi szabalyoknak legyen kulon, szerkesztheto, auditálhato,
verziozhato truth-retege az `app.cut_rule_sets` tablaban, es ehhez minimalis
backend CRUD is keszuljon.

A jelenlegi repoban mar megvan:
- manufacturing profile domain es project manufacturing selection alap;
- `manufacturing_canonical` derivative generation;
- contour classification truth a `geometry_contour_classes` tablaban.

Ami hianyzik, az a szabalyhalmazok kulon domainje. Ez a task ezt a reteget
szallitja le.

Ez a task szandekosan nem contour rule sorok, nem rule matching, nem snapshot
manufacturing bovites, nem manufacturing plan builder, nem preview vagy export.
A scope kifejezetten az, hogy a kesobbi H2-E3-T2/H2-E3-T3 retegekhez legyen
kulon cut rule set truth es minimalis owner-scoped CRUD.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - az `app.cut_rule_sets` tabla bevezetese a H2 docs szerinti minimalis,
    de a jelenlegi repohoz igazított mezoivel;
  - owner-scoped CRUD backend a cut rule set rekordokhoz;
  - verziozhatosag ugyanazon logikai rule set nev alatt;
  - machine/material/thickness meta kezelese a jelenlegi repo truth-hoz igazítva;
  - aktiv/inaktiv allapot kezelese;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - `app.cut_contour_rules` tabla;
  - contour-level lead-in/lead-out mezok vagy entry policy;
  - contour classification -> rule matching engine;
  - manufacturing profile versionek rule set FK-bovitese;
  - snapshot manufacturing bovites, plan builder, preview, postprocess vagy export.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a H2-E3-T1 source-of-truth task definicioja; output: `cut_rule_sets` tabla es CRUD.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - H2 reszletes terv; kimondja, hogy a gyartasi szabalyok szerkesztheto,
    query-zheto, auditálhato rule set domainbe keruljenek.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - rogziti a manufacturing truth es a manufacturing plan / export vilag szeparaciojat.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - jelenlegi manufacturing profile version truth; fontos, hogy a repo jelenleg
    `machine_code`, `material_code`, `thickness_mm` mezoket hasznal, nem katalogus FK-kat.
- `api/routes/project_manufacturing_selection.py`
  - owner-scoped, repo-szeru FastAPI route minta.
- `api/services/project_manufacturing_selection.py`
  - owner-scoped service es validacios minta.

### Konkret elvarasok

#### 1. A cut rule set truth kulon tabla legyen, ne manufacturing profile JSON
A `cut_rule_sets` domain ne a `manufacturing_profile_versions.config_jsonb`
tovabbterhelese legyen, hanem kulon tabla.

Minimum elvart tabla:
- `id`
- `owner_user_id`
- `name`
- `machine_code`
- `material_code`
- `thickness_mm`
- `version_no`
- `is_active`
- `notes`
- `metadata_jsonb`
- `created_at`
- `updated_at`

#### 2. A task a jelenlegi repo truth-hoz igazodjon
A H2 docs tobb helyen `machine_catalog` / `material_catalog` tablakat emlit,
de ezek a jelenlegi migraciokban nem leteznek.
Ezert ebben a taskban:
- `machine_code` text maradjon;
- `material_code` text maradjon;
- `thickness_mm` numeric maradjon;
- ne talalj ki nem letezo catalog FK-kat.

#### 3. A verziozhatosag tenylegesen mukodjon
A DoD szerint a rule setek verziozhatok.
Ezert a taskban:
- ugyanazon owner alatt ugyanazon `name` tobb `version_no` ertekkel letezhessen;
- az uj rekord alapertelmezetten a kovetkezo verzioszamra alljon ugyanazon
  owner + name csoportban;
- a service ne lazitsa el a uniqueness integritast.

#### 4. A CRUD maradjon minimalis, owner-scoped backend contract
Keszits legalabb ezt a minimum backend contractot:
- `POST /cut-rule-sets`
- `GET /cut-rule-sets`
- `GET /cut-rule-sets/{cut_rule_set_id}`
- `PATCH /cut-rule-sets/{cut_rule_set_id}`
- `DELETE /cut-rule-sets/{cut_rule_set_id}`

A CRUD:
- csak a sajat owner scope-ban mukodjon;
- ne nyisson meg project-szintu vagy manufacturing profile-szintu bekotest;
- ne vallaljon contour rule vagy matching logikat.

#### 5. Az aktiv/inaktiv allapot legyen kezelheto, de ne legyen lifecycle tulbonyolitas
Ebben a taskban elegendo:
- `is_active` kezeles;
- egyszeru update / delete owner-scope-ban.

Ne vezess be kulon revision_lifecycle vagy publication workflow-t, ha arra a
cut rule set tasknak nincs tenyleges szuksege.

#### 6. A task ne nyissa ki a H2-E3-T2/H2-E3-T3 scope-ot
Ebben a taskban nem szabad:
- `cut_contour_rules` tablakat letrehozni;
- outer/inner/feature_class szabalysorokat bevezetni;
- contour class -> rule matching logikat irni;
- manufacturing profile versionhoz default/outer/inner rule set FK-t bekotni.

#### 7. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- rule set letrehozhato owner scope-ban;
- ugyanazon nev alatt uj verzio letrehozhato;
- listazas owner scope-ra szukul;
- GET csak sajat rekordot ad vissza;
- PATCH modositas mukodik;
- DELETE torol;
- idegen owner rekordja nem olvashato vagy modosithato;
- `machine_code`, `material_code`, `thickness_mm` meta stabilan tarolodik.

### DoD
- [ ] Letrejon az `app.cut_rule_sets` tabla a minimalis H2 schema szerint.
- [ ] A tabla a jelenlegi repo truth-hoz igazodva `machine_code` / `material_code` / `thickness_mm` mezoket hasznal.
- [ ] A rule setek owner-scope-ban CRUD-olhatok.
- [ ] A rule setek tenylegesen verziozhatok ugyanazon logical name alatt.
- [ ] Az `is_active` allapot kezelheto.
- [ ] A task nem nyitja ki a contour rule, matching, snapshot vagy plan scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task katalogus FK-kat talal ki, amelyek nincsenek a repoban;
  - a CRUD tul hamar manufacturing profile vagy contour rule scope-ba csuszik;
  - a verziozas nem lesz determinisztikus ugyanazon name alatt;
  - owner-scope fellazul.
- Mitigacio:
  - explicit repo-hu mezokeszlet (`machine_code`, `material_code`, `thickness_mm`);
  - explicit out-of-scope lista;
  - owner-scoped select/update/delete mintakovetes a meglevo H2-E1-T2 service alapjan;
  - egyedi kulcs owner + name + version_no kombinacion.
- Rollback:
  - migration + service + route + smoke valtozasok egy task-commitban visszavonhatok;
  - a cut rule set domain rollback utan sem erinti a H2-E1/H2-E2 truth retegeket.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/cut_rule_sets.py api/routes/cut_rule_sets.py api/main.py scripts/smoke_h2_e3_t1_cut_rule_set_model.py`
  - `python3 scripts/smoke_h2_e3_t1_cut_rule_set_model.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `api/routes/project_manufacturing_selection.py`
- `api/services/project_manufacturing_selection.py`
