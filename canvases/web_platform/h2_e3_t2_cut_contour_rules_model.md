# H2-E3-T2 cut contour rules model

## Funkcio
A feladat a H2 cut rule rendszer masodik, kozponti lepese.
A cel, hogy a `cut_rule_sets` logikai szabalyhalmazain belul tenylegesen
lehessen contour-szintu szabalyokat tarolni kulon truth-retegben az
`app.cut_contour_rules` tablaban, es ehhez minimalis, owner-scoped backend CRUD
is keszuljon.

A jelenlegi repoban mar megvan:
- manufacturing profile domain es project manufacturing selection alap;
- `manufacturing_canonical` derivative generation;
- contour classification truth a `geometry_contour_classes` tablaban;
- a `cut_rule_sets` tabla es annak owner-scoped CRUD-ja.

Ami hianyzik, az a rule seten beluli konkret contour-szintu szabalysorok truth-ja.
Ez a task ezt a reteget szallitja le.

Ez a task szandekosan nem rule matching engine, nem manufacturing profile rule-set
binding, nem snapshot manufacturing bovites, nem manufacturing plan builder,
nem preview vagy export. A scope kifejezetten az, hogy a kesobbi H2-E3-T3
matching logikahoz legyen kulon `cut_contour_rules` truth es minimalis
owner-scoped CRUD.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - az `app.cut_contour_rules` tabla bevezetese a H2 docs szerinti minimalis,
    de a jelenlegi repohoz igazitott mezoivel;
  - owner-scoped CRUD backend a contour rule rekordokhoz;
  - `cut_rule_set_id` alapu kapcsolat a meglevo `app.cut_rule_sets` tablaval;
  - outer/inner szabalyok kulon tarolhatosaga;
  - feature_class, lead-in/out, entry-side, direction, hossz/radius/sorrend meta
    tarolasa;
  - enabled allapot kezelese;
  - task-specifikus smoke a sikeres es hibas agakra.
- Nincs benne:
  - contour class -> rule matching engine;
  - `geometry_contour_classes` rekordok konkret szabalyra kotese;
  - manufacturing profile versionek rule set vagy contour rule FK-bovitese;
  - snapshot manufacturing bovites, plan builder, preview, postprocess vagy export;
  - gep-/anyag-katalogus FK-k kitalalasa.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - a H2-E3-T2 source-of-truth task definicioja; output: `cut_contour_rules` CRUD.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - H2 reszletes terv; kimondja a `cut_contour_rules` tabla minimum mezoit es azt,
    hogy outer/inner kulon szabalyok tarolhatok.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - rogziti a manufacturing truth es a manufacturing plan / export vilag szeparaciojat.
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
  - a meglevo `app.cut_rule_sets` truth, amire a contour rules epulnek.
- `api/routes/cut_rule_sets.py`
  - owner-scoped FastAPI route minta.
- `api/services/cut_rule_sets.py`
  - owner-scoped service es validacios minta.
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
  - a `geometry_contour_classes` tabla; fontos boundary, mert a jelen task nem ide ir
    matching eredmenyt.

### Konkret elvarasok

#### 1. A contour rules truth kulon tabla legyen, ne JSON a rule set sorban
A `cut_contour_rules` domain ne a `cut_rule_sets.metadata_jsonb` tovabbterhelese legyen,
hanem kulon tabla.

Minimum elvart tabla:
- `id`
- `cut_rule_set_id`
- `contour_kind`
- `feature_class`
- `lead_in_type`
- `lead_in_length_mm`
- `lead_in_radius_mm`
- `lead_out_type`
- `lead_out_length_mm`
- `lead_out_radius_mm`
- `entry_side_policy`
- `min_contour_length_mm`
- `max_contour_length_mm`
- `pierce_count`
- `cut_direction`
- `sort_order`
- `enabled`
- `metadata_jsonb`
- `created_at`
- `updated_at`

#### 2. A task maradjon a jelenlegi repo truth-hoz igazodva minimalis
A H2 docs tartalmaz javasolt mezo-listat. Ebben a taskban:
- `contour_kind` kezdetben csak `outer` vagy `inner` lehessen;
- `feature_class` default maradjon `default`;
- `lead_in_type` / `lead_out_type` legalabb `none|line|arc` korre szukuljon;
- `entry_side_policy` es `cut_direction` validalt text enum-jellegu mezok legyenek,
  de ne talalj ki kulon adatbazis enumot, ha arra nincs eros repo-minta;
- hosszak/radiusok, ha jelen vannak, pozitivak legyenek;
- `min_contour_length_mm <= max_contour_length_mm`, ha mindketto jelen van.

#### 3. A relation owner-scope-ja a rule set owneren keresztul ervenyesuljon
A contour rule nem kap kulon `owner_user_id` mezot, ha a meglevo repohoz tisztabban
illeszkedik a `cut_rule_set_id` alapu owner-scope.
Ezert:
- csak olyan `cut_rule_set_id` ala lehessen szabalyt letrehozni, amely a jelenlegi
  ownerhez tartozik;
- listazas/GET/PATCH/DELETE owner-scope-ja a kapcsolt `cut_rule_sets.owner_user_id`
  alapjan ervenyesuljon;
- idegen owner rule setjere ne lehessen szabalyt letrehozni vagy modositani.

#### 4. A CRUD maradjon minimalis, owner-scoped backend contract
Keszits legalabb ezt a minimum backend contractot:
- `POST /cut-rule-sets/{cut_rule_set_id}/rules`
- `GET /cut-rule-sets/{cut_rule_set_id}/rules`
- `GET /cut-rule-sets/{cut_rule_set_id}/rules/{rule_id}`
- `PATCH /cut-rule-sets/{cut_rule_set_id}/rules/{rule_id}`
- `DELETE /cut-rule-sets/{cut_rule_set_id}/rules/{rule_id}`

A CRUD:
- csak a sajat owner scope-ban mukodjon;
- ne vallaljon matching logikat;
- ne vallaljon `geometry_contour_classes` update-et;
- ne vallaljon manufacturing profile vagy snapshot bekotest.

#### 5. Outer/inner kulon szabalyok tenylegesen tarolhatok legyenek
A task tree DoD szerint outer/inner kulon szabalyok tarolhatok.
Ezert a smoke bizonyitsa legalabb:
- ugyanazon rule set alatt hozhato letre `outer` szabaly;
- ugyanazon rule set alatt hozhato letre `inner` szabaly;
- ugyanazon rule set alatt tobb szabaly is lehet kulon `sort_order` ertekkel;
- `feature_class` kesobbi differencialashoz tarolodik.

#### 6. A task ne nyissa ki a H2-E3-T3 scope-ot
Ebben a taskban nem szabad:
- contour class -> rule matching logikat irni;
- `geometry_contour_classes` rekordokhoz `rule_id`-t bekotni;
- manufacturing plan buildert, lead point generationt vagy pierce-utvonal tervezest irni;
- manufacturing profile versionhez default/outer/inner rule set vagy rule FK-t bekotni.

#### 7. A smoke bizonyitsa a fo invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- contour rule letrehozhato owner scope-ban sajat rule set alatt;
- `outer` es `inner` kulon szabalyok tarolhatok;
- listazas cut_rule_set-re szukul;
- GET csak sajat rekordot ad vissza;
- PATCH modositas mukodik;
- DELETE torol;
- idegen owner rule setjere nem hozhato letre szabaly;
- invalid `contour_kind`, invalid lead type, negativ hosszak/radiusok,
  hibas min/max tartomany elutasitasra kerulnek.

### DoD
- [ ] Letrejon az `app.cut_contour_rules` tabla a minimalis H2 schema szerint.
- [ ] A tabla a meglevo `app.cut_rule_sets` truth-ra epul `cut_rule_set_id` FK-val.
- [ ] A contour rule-ok owner-scope-ban CRUD-olhatok a kapcsolt rule set owneren keresztul.
- [ ] Outer es inner kulon szabalyok tenylegesen tarolhatok.
- [ ] A task validalja a kritikus mezo-invariansokat (`contour_kind`, lead type, pozitiv numeric, min/max tartomany).
- [ ] A task nem nyitja ki a rule matching, snapshot, plan vagy manufacturing profile binding scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task tul koran matching logikaba csuszik;
  - a contour rule owner-scope fellazul;
  - a validation tul gyenge lesz es szemet lead-in/out adatok kerulnek be;
  - a task FK-kat vagy catalog truth-ot talal ki, ami nincs a repoban.
- Mitigacio:
  - explicit out-of-scope lista;
  - owner-scope a `cut_rule_sets` kapcsolaton keresztul;
  - szuk mezo-validacio;
  - `geometry_contour_classes` es manufacturing profile retegek erintetlenul hagyasa.
- Rollback:
  - migration + service + route + smoke valtozasok egy task-commitban visszavonhatok;
  - a rollback nem erinti a H2-E1/H2-E2 truth retegeket es a H2-E3-T1 rule set domaint.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/cut_contour_rules.py api/routes/cut_contour_rules.py api/main.py scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
  - `python3 scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- `api/routes/cut_rule_sets.py`
- `api/services/cut_rule_sets.py`
