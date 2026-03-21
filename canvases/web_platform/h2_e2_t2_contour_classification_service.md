# H2-E2-T2 contour classification service

## Funkcio
A feladat a H2 manufacturing geometry pipeline masodik lepese.
A cel, hogy a H2-E2-T1-ben bevezetett `manufacturing_canonical` derivative
contourjai kulon, auditálhato classification truth-ot kapjanak az
`app.geometry_contour_classes` tablaban.

A jelenlegi repoban mar van:
- `manufacturing_canonical` derivative payload `contours` listaval,
- project manufacturing selection alap,
- H1/H2 geometry pipeline gerinc.

Ami hianyzik, az a contour-szintu osztalyozas es annak tartos tarolasa. Ez a
feladat ezt a reteget szallitja le.

Ez a task szandekosan nem cut rule rendszer, nem rule matching, nem snapshot
manufacturing bovites, nem manufacturing plan builder, nem preview vagy export.
A scope kifejezetten az, hogy a manufacturing derivative contourjaihoz egy
minimalis, kesobbi H2 retekre epitheto classification pipeline keszuljon.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - az `app.geometry_contour_classes` tabla bevezetese a H2 docs szerinti minimalis
    mezoivel;
  - egy explicit contour classification service, amely a
    `manufacturing_canonical` derivative `contours` payloadjat olvassa;
  - outer/inner alapklasszifikacio a valos derivative payload alapjan;
  - `feature_class` kezdeti, minimalis logika (`default`), auditálhato mentessel;
  - alap geometriametrikak tarolasa contouronkent (`area_mm2`, `perimeter_mm`,
    `bbox_jsonb`, `is_closed`);
  - idempotens upsert logika ugyanarra a derivative-re es contour_indexre;
  - a meglevo DXF import pipeline bekotese ugy, hogy validated geometry esetén a
    manufacturing derivative generalasa utan a contour classification is lefusson;
  - task-specifikus smoke script a sikeres es hibas agakra.
- Nincs benne:
  - `cut_rule_sets`, `cut_contour_rules`, rule matching;
  - contour-level lead-in/lead-out vagy entry side policy;
  - snapshot manufacturing manifest, run_manufacturing_plans vagy
    run_manufacturing_contours;
  - worker / preview / postprocess / export;
  - manufacturing profile vagy project manufacturing selection ujabb bovítese.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a H2-E2-T2 source-of-truth task definicioja; DoD: `geometry_contour_classes`
    feltoltheto.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 reszletes terv; kimondja, hogy a manufacturing derivative contourjait
    outer / inner / feature class logikaval kell osztalyozni, es ezt kulon
    tablaba erdemes menteni.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - rogziti a derivative truth es a manufacturing plan / export vilag szetvalasztasat.
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
  - fontos ownership / truth / derivative / artifact boundary-k.
- `supabase/migrations/20260322001000_h2_e2_t1_manufacturing_canonical_derivative_generation.sql`
  - a kozelmultbeli H2-E2-T1 alap, amelyre ez a task kozvetlenul epul.
- `api/services/geometry_derivative_generator.py`
  - a `manufacturing_canonical` payload jelenlegi szerkezete (`contours`,
    `contour_summary`, `bbox`, `source_geometry_ref`).
- `api/services/dxf_geometry_import.py`
  - a valid geometry import pipeline aktualis bekotesi pontja.
- `scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
  - jo kiindulasi minta a manufacturing derivative smoke-hoz.

### Konkret elvarasok

#### 1. A classification truth kulon tabla legyen, ne derivative payload mutacio
A contour classification eredmeny ne a `manufacturing_canonical` JSON payload
bovitesekent keruljon tarolasra, hanem kulon `app.geometry_contour_classes`
rekordokban.

Minimum elvart tabla:
- `id`
- `geometry_derivative_id`
- `contour_index`
- `contour_kind`
- `feature_class`
- `is_closed`
- `area_mm2`
- `perimeter_mm`
- `bbox_jsonb`
- `metadata_jsonb`
- `created_at`
- `unique (geometry_derivative_id, contour_index)`

#### 2. A service csak manufacturing derivative-re epithet
A classification service:
- csak `manufacturing_canonical` derivative-bol dolgozhat;
- ne olvasson `viewer_outline` vagy `nesting_canonical` payloadot contour truth-kent;
- hiba vagy skip legyen, ha a derivative kind nem `manufacturing_canonical`;
- ne talaljon ki olyan contour-adatot, ami nincs a derivative payloadban.

#### 3. A kezdeti contour_kind vilag maradjon minimalis es repo-hu
A H2 docs szerint a kezdeti `contour_kind` minimum vilag:
- `outer`
- `inner`

Ezert ebben a taskban:
- a derivative payload `contour_role=outer` -> `contour_kind=outer`
- a derivative payload `contour_role=hole` -> `contour_kind=inner`
- ne nyiss `slot`, `micro_inner`, `mark` vagy egyeb kesobbi kategoriakat.

A `feature_class` kezdetben legyen `default`, vagy a metadata-ban indokolt,
minimalis heurisztikabol szarmazo ertek, de ne csusszon at rule-matching scope-ba.

#### 4. A service legyen idempotens es auditálhato
Ujrafuttatas ugyanarra a manufacturing derivative-re:
- ne hozzon letre duplikalt contour class rekordokat;
- ugyanazokra a `contour_index` ertekekre update-eljen vagy upserteljen;
- a `metadata_jsonb` hordozza legalabb a source contour_role / winding adatokat,
  hogy az osztalyozas visszakeresheto legyen.

#### 5. A basic geometric metrics a task reszei
A classification rekord tartalmazza contouronkent legalabb:
- `is_closed`
- `area_mm2`
- `perimeter_mm`
- `bbox_jsonb`

Ezek a kesobbi cut rule es manufacturing plan retegekhez elokeszito truth-ok,
nem opcionális mellékatributumok.

#### 6. A pipeline bekotes legyen minimalis, de valodi
A task ne maradjon csak manualisan hivhato service.
A meglevo `api/services/dxf_geometry_import.py` pipeline-ban, a validated geometry
import utan es a derivative generalasa utan fusson le a contour classification is.

Ez a task nem routeszintű API, hanem backend pipeline alap.

#### 7. A task ne nyissa ki a H2-E3/H2-E4 scope-ot
Ebben a taskban nem szabad:
- `cut_rule_sets` vagy `cut_contour_rules` tablakat letrehozni;
- contour class -> rule matching logikat bevezetni;
- manufacturing snapshot vagy plan builder vilagot erinteni.

#### 8. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- manufacturing derivative contourjaihoz rekordok jonnek letre a
  `geometry_contour_classes` tablaban;
- outer / inner mapping helyes a derivative payload alapjan;
- `feature_class` stabilan kitoltott;
- `area_mm2`, `perimeter_mm`, `bbox_jsonb`, `is_closed` kitoltodik;
- ujrafuttatas nem hoz letre duplikalt contour class rekordot;
- nem manufacturing derivative-re a service nem osztalyoz;
- rejected geometry eseten a pipeline nem gyart classification truth-ot.

### DoD
- [ ] Letrejön az `app.geometry_contour_classes` tabla a minimalis H2 schema szerint.
- [ ] A classification service a `manufacturing_canonical` derivative `contours` payloadjara epit.
- [ ] A kezdeti `contour_kind` vilag repo-huen `outer` / `inner` marad.
- [ ] A `feature_class` kitoltodik es auditálhato.
- [ ] A contouronkenti `area_mm2`, `perimeter_mm`, `bbox_jsonb`, `is_closed` tarolodik.
- [ ] A service idempotens ugyanarra a derivative-re.
- [ ] A DXF import pipeline validated geometry eseten a classificationt is lefuttatja.
- [ ] A task nem nyitja ki a cut rule, matching, snapshot vagy plan scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t2_contour_classification_service.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a classification logika tul koran rule-szeru lesz es atcsuszik H2-E3 scope-ba;
  - a service nem idempotens, duplikalt contour class rekordokat gyart;
  - a contour metrics szamitas instabil vagy nem determinisztikus lesz;
  - a pipeline nem csak manufacturing derivative-re fog epulni.
- Mitigacio:
  - explicit out-of-scope lista;
  - unique `(geometry_derivative_id, contour_index)` + upsert minta;
  - csak a `manufacturing_canonical.contours` payloadot hasznald source-kent;
  - a metrics szamitas legyen tisztan a points lista alapjan.
- Rollback:
  - a migration + service + import pipeline + smoke valtozasok egy task-commitban
    visszavonhatok;
  - a manufacturing derivative truth a H2-E2-T1 miatt rollback utan is megmarad.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e2_t2_contour_classification_service.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/geometry_contour_classification.py api/services/dxf_geometry_import.py scripts/smoke_h2_e2_t2_contour_classification_service.py`
  - `python3 scripts/smoke_h2_e2_t2_contour_classification_service.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `supabase/migrations/20260322001000_h2_e2_t1_manufacturing_canonical_derivative_generation.sql`
- `api/services/geometry_derivative_generator.py`
- `api/services/dxf_geometry_import.py`
- `scripts/smoke_h2_e2_t1_manufacturing_canonical_derivative_generation.py`
