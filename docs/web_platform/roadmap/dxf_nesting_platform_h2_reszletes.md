# DXF Nesting Platform — H2 részletes terv

## Cél

A **H2** a platform második nagy funkcionális mélyítési szintje.  
A H0 a szerkezeti gerincet zárta le, a H1 a teljes DXF → geometry → part/sheet → snapshot → run → eredmény csatornát tette működőképessé.  
A H2 feladata az, hogy a rendszer túllépjen a “csak nesting platform” állapoton, és belépjen a **gyártásközeli technológiai platform** állapotba.

A H2 központi kérdése nem az, hogy “be tudjuk-e tenni az alkatrészeket a táblába”, hanem az, hogy a nesting eredmény hogyan válik:

- technológiához kötött gyártási adattá,
- szerkeszthető manufacturing szabályrendszerrel vezérelt kimenetté,
- és később gépfüggő postprocess/export számára stabil köztes formává.

A H2 tehát azt a réteget építi fel, ahol a platform már nem csak elhelyezést kezel, hanem **gyártási szándékot** is.

---

## H2 fő célképe

A H2 végére a rendszernek az alábbi elveket és képességeket kell teljesítenie:

1. **A nesting geometry és a manufacturing geometry külön világ legyen**
   - külön derivative réteg
   - külön feldolgozási logika
   - külön felhasználási cél

2. **A technológia ne csak nesting paramétereket jelentsen**
   - hanem gyártási szabályokat is
   - contour típusonként eltérő vágási döntéseket
   - anyag / vastagság / gépfüggő manufacturing profile-okat

3. **Megjelenjen a vágási szabályrendszer**
   - outer vs inner contour
   - lead-in / lead-out
   - belépési stratégia
   - alap piercing és cut-order policy

4. **A nesting run eredményéből létrejöhessen manufacturing-ready köztes réteg**
   - cut plan
   - contour-level utasításkészlet
   - gépfüggetlen manufacturing artifact

5. **A postprocess irány legyen ténylegesen előkészítve**
   - profile és version kezelés
   - adapterelhető machine-specific export réteg
   - machine-ready artifact helye

6. **A platform továbbra se keverje össze a solver, manufacturing és export felelősségi körét**
   - a solver nem gépfüggő CAM motor
   - a manufacturing layer nem frontend projection
   - a postprocessor nem domain truth

---

## H2 szerepe a roadmapban

A H2 az a szakasz, ahol a platform:

- a nesting eredménytől
- a gyártási logikával bővített
- exportálható köztes reprezentáció irányába mozdul el.

### H1 után mi hiányzik még?
A H1 végére van:
- működő DXF pipeline,
- geometry revision és derivative kezelés,
- működő part/sheet/run platform,
- worker és projection réteg,
- alap artifactok.

De hiányzik még:
- a gyártási geometriával való tudatos bánásmód,
- a contour-specifikus technológiai szabályok,
- a lead-in/lead-out authoring modell,
- a postprocess-kompatibilis köztes adatszint.

### H2-ben mi történik?
A H2-ben a platform már nem csak “solver outputot mutat”, hanem:
- technológiához rendelt manufacturing profile-ból dolgozik,
- a run eredményt manufacturing szintre emeli,
- és előállítja azt a köztes világot, amelyből később gépfüggő programok generálhatók.

---

## H2 scope

## H2-be tartozik

- manufacturing_profiles domain tényleges aktiválása
- manufacturing_profile_versions részletes mezői
- cut_rule_sets modell
- cut_contour_rules modell
- contour classification alaplogika
- manufacturing_canonical derivative tényleges használata
- project_manufacturing_selection működő bekötése
- run snapshot manufacturing részének bővítése
- cut plan köztes artifact és/vagy projection réteg
- postprocessor profile/version aktiválás alap szinten
- machine-neutral manufacturing export contract
- belső vs külső kontúr elkülönített kezelése
- lead-in / lead-out szabályrendszer minimális első működő változata
- manufacturing oldali metrikák alapjai

## H2-be nem tartozik teljes mélységben

- teljes CAM rendszer
- bonyolult mikrokötés / tab / bridge authoring
- hőtorzulás- és sorrendoptimalizálás mély ipari logika
- gépspecifikus összes exportformátum teljes körű támogatása
- nesting és cut order közös felsőoptimalizálása
- operátori kézi kontúrszintű szerkesztő teljes funkcionalitása
- MES/ERP integráció teljes üzleti mélysége

A H2 célja a **manufacturing domain megalapozása és első működő integrálása**, nem a teljes CAM világ lezárása.

---

## H2 architekturális döntések

## 1. Két külön canonical geometry-világ kell

A H2-ben ezt ki kell mondani egyértelműen:

- **nesting_canonical** = solver-barát, determinisztikus, placementre optimalizált geometria
- **manufacturing_canonical** = gyártási felhasználásra alkalmasabb, contour-szintű technológiai kezelésre előkészített geometria

Miért fontos ez?

Mert ami jó a solvernek, az nem biztos, hogy elég jó:
- lead-in pontokhoz,
- contour típusfelismeréshez,
- gyártási sorrendhez,
- gépexporthoz.

A H2-ben tehát a `geometry_derivatives` nem opcionális többlet, hanem kötelező kettős szereplő lesz.

---

## 2. A manufacturing technológia ne legyen a nesting profile-ba zsúfolva

A H1/H0 technológiai profil jól működik a nestinghez:
- spacing
- margin
- rotation
- time limit
- kerf source

De a H2-ben a gyártási világ már túl sok és túl más típusú adatot hoz be:
- contour policy
- entry/exit szabály
- cut order
- piercing stratégia
- manufacturing export döntések

Ezért a H2-ben **külön manufacturing domain** kell, nem a `technology_profile_versions.config_jsonb` túlterhelése.

---

## 3. A cut rule rendszer legyen szerkeszthető és auditálható

A H2-ben a lead-in / lead-out és contour policy ne puszta egy darab nagy JSON legyen.

A szabályrendszernek:
- verziózhatónak,
- query-zhetőnek,
- diffelhetőnek,
- UI-ból szerkeszthetőnek,
- auditálhatónak kell lennie.

Ezért kell külön:
- rule set
- rule sorok / contour rules
- classification mezők

---

## 4. A solver output és a cut plan külön szint legyen

A H2-ben bevezetendő egy új köztes réteg:

- **solver result**: mit hová helyeztünk
- **manufacturing cut plan**: milyen contourt milyen technológiai szabály szerint fogunk gyártani

Ez kritikus szétválasztás.

A solver azt mondja meg:
- melyik part melyik sheetre került
- milyen transzformmal

A manufacturing layer azt mondja meg:
- melyik contour outer vagy inner
- melyik szabály vonatkozik rá
- honnan indul a vágás
- milyen ráfutás/kifutás tartozik hozzá
- milyen sorrendi és belépési meta társul hozzá

---

## 5. A postprocessor továbbra is külön modul maradjon

A H2-ben a postprocessor már aktívabb szerepet kap, de még mindig külön kell maradnia:

- manufacturing layer adja a gépfüggetlen cut plan-t
- postprocessor alakítja ezt gépfüggő formátumra

A H2 egyik lényegi döntése:
**a machine-ready output nem válhat a platform “truth” adatává**.  
Az csak artifact.

A truth marad:
- revisionök,
- snapshot,
- run projection,
- manufacturing plan.

---

## H2 részletes domainbővítés

## 1. Manufacturing profile domain aktiválása

A H0-ban ez csak helyfoglaló volt.  
A H2-ben valódi szerkezetté kell válnia.

### `manufacturing_profiles`
Továbbra is logikai profilcsoport.

### `manufacturing_profile_versions`
Itt már részletes mezőkellenek.

Javasolt bővítés:

```sql
alter table app.manufacturing_profile_versions
  add column if not exists default_cut_rule_set_id uuid,
  add column if not exists outer_cut_rule_set_id uuid,
  add column if not exists inner_cut_rule_set_id uuid,
  add column if not exists pierce_strategy_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists cut_order_policy_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists entry_point_policy_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists active_postprocessor_profile_version_id uuid,
  add column if not exists is_active boolean not null default true;
```

A konkrét FK-kat célszerű a rule set táblák létrejötte után hozzáadni.

---

## 2. Cut rule sets

Új táblák kellenek.

```sql
create table if not exists app.cut_rule_sets (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  machine_id uuid references app.machine_catalog(id) on delete set null,
  material_id uuid references app.material_catalog(id) on delete set null,
  thickness_mm numeric(10,3),
  version_no integer not null default 1,
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now()
);
```

Ez a logikai szabályhalmaz.

---

## 3. Cut contour rules

Ez a H2 egyik központi táblája.

```sql
create table if not exists app.cut_contour_rules (
  id uuid primary key default gen_random_uuid(),
  cut_rule_set_id uuid not null references app.cut_rule_sets(id) on delete cascade,
  contour_kind text not null,
  feature_class text not null default 'default',
  lead_in_type text not null default 'none',
  lead_in_length_mm numeric(10,3),
  lead_in_radius_mm numeric(10,3),
  lead_out_type text not null default 'none',
  lead_out_length_mm numeric(10,3),
  lead_out_radius_mm numeric(10,3),
  entry_side_policy text,
  min_contour_length_mm numeric(10,3),
  max_contour_length_mm numeric(10,3),
  pierce_count integer,
  cut_direction text,
  sort_order integer not null default 100,
  enabled boolean not null default true,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

A `contour_kind` kezdetben lehet:
- `outer`
- `inner`

Később jöhet:
- `hole`
- `slot`
- `micro_inner`
- `narrow_channel`

A `feature_class` azért kell, hogy később ugyanazon contour_kindon belül is differenciálni lehessen.

---

## 4. Contour classification eredmények külön táblába

A H2-ben célszerű külön tárolni a contour-szintű osztályozott eredményt is, különösen manufacturing célra.

```sql
create table if not exists app.geometry_contour_classes (
  id uuid primary key default gen_random_uuid(),
  geometry_derivative_id uuid not null references app.geometry_derivatives(id) on delete cascade,
  contour_index integer not null,
  contour_kind text not null,
  feature_class text not null default 'default',
  is_closed boolean,
  area_mm2 numeric(18,4),
  perimeter_mm numeric(18,4),
  bbox_jsonb jsonb not null default '{}'::jsonb,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (geometry_derivative_id, contour_index)
);
```

Miért kell?
- nem kell minden alkalommal újra osztályozni
- auditálható, hogy mit minek ismert fel a pipeline
- későbbi manuális review is épülhet rá

---

## 5. Manufacturing run snapshot kiterjesztése

A H2-ben a `nesting_run_snapshots.snapshot_jsonb` tartalmát bővíteni kell, és ezt érdemes metaadatban is jelezni.

Javasolt plusz oszlopok:

```sql
alter table app.nesting_run_snapshots
  add column if not exists includes_manufacturing boolean not null default false,
  add column if not exists includes_postprocess boolean not null default false;
```

A snapshot JSON-ban pedig meg kell jelenjen:
- selected manufacturing profile version
- selected cut rule setek
- selected postprocessor version
- manufacturing derivative hivatkozások
- contour classification inputok vagy hivatkozások

---

## 6. Manufacturing plan mint külön run-eredmény szint

Új táblák javasoltak.

```sql
create table if not exists app.run_manufacturing_plans (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade,
  manufacturing_profile_version_id uuid references app.manufacturing_profile_versions(id) on delete set null,
  status text not null default 'generated',
  summary_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (run_id, sheet_id)
);

create table if not exists app.run_manufacturing_contours (
  id uuid primary key default gen_random_uuid(),
  manufacturing_plan_id uuid not null references app.run_manufacturing_plans(id) on delete cascade,
  placement_id uuid references app.run_layout_placements(id) on delete cascade,
  contour_index integer not null,
  contour_kind text not null,
  feature_class text not null default 'default',
  rule_id uuid references app.cut_contour_rules(id) on delete set null,
  entry_point_jsonb jsonb,
  lead_in_jsonb jsonb,
  lead_out_jsonb jsonb,
  cut_order_index integer,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Ez lesz a H2 “gyártási truth-közeli” rétege.

---

## 7. Postprocessor domain aktiválása

A H0/H1-ben már megvolt a helye. H2-ben bekötjük.

Javasolt bővítések:

```sql
alter table app.postprocessor_profiles
  add column if not exists machine_id uuid references app.machine_catalog(id) on delete set null,
  add column if not exists is_active boolean not null default true;

alter table app.postprocessor_profile_versions
  add column if not exists schema_version text not null default 'v1',
  add column if not exists is_active boolean not null default true;
```

A manufacturing profilnak pedig erre kell tudnia mutatni.

---

## 8. Új artifact típusok

A H2-ben a meglévő `artifact_kind` enumot bővíteni kell.

Javasolt új értékek:
- `manufacturing_plan_json`
- `manufacturing_preview_svg`
- `machine_ready_bundle`
- `machine_log`

SQL-váz:

```sql
alter type app.artifact_kind add value if not exists 'manufacturing_plan_json';
alter type app.artifact_kind add value if not exists 'manufacturing_preview_svg';
alter type app.artifact_kind add value if not exists 'machine_ready_bundle';
alter type app.artifact_kind add value if not exists 'machine_log';
```

---

## 9. Manufacturing metrikák

A H2-ben a `run_metrics` önmagában kevés lehet, ezért vagy JSON-bővítés, vagy külön tábla kell.

Egyszerű induló javaslat:

```sql
create table if not exists app.run_manufacturing_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  pierce_count integer,
  outer_contour_count integer,
  inner_contour_count integer,
  estimated_cut_length_mm numeric(18,4),
  estimated_rapid_length_mm numeric(18,4),
  estimated_process_time_s numeric(18,4),
  metrics_jsonb jsonb not null default '{}'::jsonb
);
```

Ez még nem végleges ipari időmodell, de már megfelelő alap.

---

## H2 Supabase SQL — részletes bővítési váz

```sql
alter table app.manufacturing_profile_versions
  add column if not exists default_cut_rule_set_id uuid,
  add column if not exists outer_cut_rule_set_id uuid,
  add column if not exists inner_cut_rule_set_id uuid,
  add column if not exists pierce_strategy_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists cut_order_policy_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists entry_point_policy_jsonb jsonb not null default '{}'::jsonb,
  add column if not exists active_postprocessor_profile_version_id uuid,
  add column if not exists is_active boolean not null default true;

create table if not exists app.cut_rule_sets (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  machine_id uuid references app.machine_catalog(id) on delete set null,
  material_id uuid references app.material_catalog(id) on delete set null,
  thickness_mm numeric(10,3),
  version_no integer not null default 1,
  is_active boolean not null default true,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists app.cut_contour_rules (
  id uuid primary key default gen_random_uuid(),
  cut_rule_set_id uuid not null references app.cut_rule_sets(id) on delete cascade,
  contour_kind text not null,
  feature_class text not null default 'default',
  lead_in_type text not null default 'none',
  lead_in_length_mm numeric(10,3),
  lead_in_radius_mm numeric(10,3),
  lead_out_type text not null default 'none',
  lead_out_length_mm numeric(10,3),
  lead_out_radius_mm numeric(10,3),
  entry_side_policy text,
  min_contour_length_mm numeric(10,3),
  max_contour_length_mm numeric(10,3),
  pierce_count integer,
  cut_direction text,
  sort_order integer not null default 100,
  enabled boolean not null default true,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists app.geometry_contour_classes (
  id uuid primary key default gen_random_uuid(),
  geometry_derivative_id uuid not null references app.geometry_derivatives(id) on delete cascade,
  contour_index integer not null,
  contour_kind text not null,
  feature_class text not null default 'default',
  is_closed boolean,
  area_mm2 numeric(18,4),
  perimeter_mm numeric(18,4),
  bbox_jsonb jsonb not null default '{}'::jsonb,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (geometry_derivative_id, contour_index)
);

alter table app.nesting_run_snapshots
  add column if not exists includes_manufacturing boolean not null default false,
  add column if not exists includes_postprocess boolean not null default false;

create table if not exists app.run_manufacturing_plans (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  sheet_id uuid not null references app.run_layout_sheets(id) on delete cascade,
  manufacturing_profile_version_id uuid references app.manufacturing_profile_versions(id) on delete set null,
  status text not null default 'generated',
  summary_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (run_id, sheet_id)
);

create table if not exists app.run_manufacturing_contours (
  id uuid primary key default gen_random_uuid(),
  manufacturing_plan_id uuid not null references app.run_manufacturing_plans(id) on delete cascade,
  placement_id uuid references app.run_layout_placements(id) on delete cascade,
  contour_index integer not null,
  contour_kind text not null,
  feature_class text not null default 'default',
  rule_id uuid references app.cut_contour_rules(id) on delete set null,
  entry_point_jsonb jsonb,
  lead_in_jsonb jsonb,
  lead_out_jsonb jsonb,
  cut_order_index integer,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table app.postprocessor_profiles
  add column if not exists machine_id uuid references app.machine_catalog(id) on delete set null,
  add column if not exists is_active boolean not null default true;

alter table app.postprocessor_profile_versions
  add column if not exists schema_version text not null default 'v1',
  add column if not exists is_active boolean not null default true;

create table if not exists app.run_manufacturing_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  pierce_count integer,
  outer_contour_count integer,
  inner_contour_count integer,
  estimated_cut_length_mm numeric(18,4),
  estimated_rapid_length_mm numeric(18,4),
  estimated_process_time_s numeric(18,4),
  metrics_jsonb jsonb not null default '{}'::jsonb
);
```

---

## H2 szükséges szolgáltatásrétegek

## 1. Manufacturing profile resolver

Feladata:
- project manufacturing selection összeolvasása
- machine/material/thickness illesztés ellenőrzése
- a megfelelő manufacturing profile version kiválasztása
- cut rule set hivatkozások feloldása

Bemenet:
- project_id
- technology selection
- sheet/part technológiai meta

Kimenet:
- active manufacturing profile version
- active cut rule setek
- active postprocessor selection

---

## 2. Contour classification service

Feladata:
- manufacturing_canonical derivative contourjainak osztályozása
- outer / inner / feature class meghatározása
- classification tárolása `geometry_contour_classes` táblába

A H2-ben ez lehet egyszerű szabályalapú:
- topológiai relációk
- bounding és area alapú heuristikák
- contour nesting depth

Később ezt lehet finomítani.

---

## 3. Manufacturing plan builder

A H2 egyik központi szolgáltatása.

Feladata:
- egy run placement eredményeit összefűzni a manufacturing derivative-kel
- contour szintű szabályhozzárendelést végezni
- entry/lead/cut-order alapadatot generálni
- manufacturing plan és contour rekordokat létrehozni

Bemenet:
- run projection
- manufacturing profile version
- contour classes
- cut rule set

Kimenet:
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- manufacturing_plan_json artifact

---

## 4. Manufacturing preview generator

Feladata:
- a contour és lead-in/lead-out információból vizuális preview készítése
- sheet szintű manufacturing preview SVG generálása

Ez fontos:
- review-hoz
- backoffice validációhoz
- későbbi operátori ellenőrzéshez

---

## 5. Postprocessor adapter service

Feladata:
- manufacturing plan → machine-specific export
- postprocessor profile version beállításainak alkalmazása
- machine-ready artifact generálása

A H2-ben ez lehet még nagyon szűk körű:
- egy generic exporter
- vagy 1 célgép családra prototípus

De az interfész legyen véglegesedett.

---

## H2 alfeladatok részletes bontásban

## H2-1 — Manufacturing domain aktiválása

### Cél
A manufacturing profile világ kilépjen a placeholder státuszból.

### Deliverable
- manufacturing profile CRUD
- version kezelés
- project_manufacturing_selection bekötése
- technology és manufacturing profil közötti alapkonzisztencia

### DoD
- projekt szinten választható manufacturing profile version
- a kiválasztás visszakereshető
- snapshotba beépíthető

---

## H2-2 — Manufacturing canonical derivative pipeline

### Cél
A geometry pipeline már ne csak nesting/viewer derivative-et gyártson.

### Deliverable
- manufacturing_canonical derivative generálás
- derivative metadata
- part revisionhöz manufacturing derivative bekötése

### DoD
- part revisionhöz explicit manufacturing derivative kapcsolható
- manufacturing pipeline nem a nesting polygonokra támaszkodik vakon
- a derivative auditálható és verziózott

---

## H2-3 — Contour classification

### Cél
A manufacturing derivative contourjai technológiailag értelmezhető osztályozást kapjanak.

### Deliverable
- classification service
- `geometry_contour_classes`
- outer/inner minimum felismerés
- feature_class kezdeti logika

### DoD
- contouronként tárolt osztályozás van
- review és debug lehetséges
- rule-hozzárendelés alapja megvan

---

## H2-4 — Cut rule set és contour rule rendszer

### Cél
A gyártási szabályok szerkeszthető, verziózható struktúrában jelenjenek meg.

### Deliverable
- `cut_rule_sets`
- `cut_contour_rules`
- rule matching logika
- outer/inner külön szabályok
- lead-in/lead-out első modell

### DoD
- rule set kiválasztható manufacturing profilból
- contourokra szabály hozzárendelhető
- a szabályok diffelhetők, query-zhetők

---

## H2-5 — Manufacturing snapshot bővítés

### Cél
A run snapshot gyártási oldala is lezáródjon.

### Deliverable
- manufacturing selection snapshotolása
- rule set hivatkozások snapshotolása
- postprocessor hivatkozások snapshotolása
- includes_manufacturing / includes_postprocess meta

### DoD
- a manufacturing plan reprodukálható ugyanazon snapshotból
- a worker/process nem élő manufacturing profilból dolgozik
- későbbi audit megmondja, mely szabályok voltak érvényben

---

## H2-6 — Manufacturing plan builder

### Cél
A run placement eredményből gépfüggetlen gyártási terv képződjön.

### Deliverable
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- manufacturing_plan_json artifact
- contour-level rule binding

### DoD
- minden placementhez gyártható contour mapping készülhet
- outer/inner szabályok alkalmazódnak
- entry/lead/cut-order alapinformáció létrejön

---

## H2-7 — Manufacturing preview és review

### Cél
A gyártási terv vizuálisan is visszanézhető legyen.

### Deliverable
- manufacturing preview SVG
- contour coloring / jelölések
- entry/lead marker vizualizáció

### DoD
- backoffice vagy frontend oldalról ellenőrizhető a gyártási terv
- a preview nem csak solver-layout, hanem gyártási meta-információt is hordoz

---

## H2-8 — Postprocessor adapter alap

### Cél
A machine-specific export réteg első működő alapja jöjjön létre.

### Deliverable
- postprocessor profile/version használat
- 1 generic machine-neutral exporter
- opcionálisan 1 célgép-család prototípus export

### DoD
- a manufacturing planből adapter útvonalon artifact készíthető
- a postprocessor külön modul marad
- a machine-ready output artifactként kezelődik

---

## H2-9 — Manufacturing metrics

### Cél
A gyártási oldal metrikázható legyen.

### Deliverable
- `run_manufacturing_metrics`
- pierce count
- contour count
- becsült vágáshossz
- alap időbecslés

### DoD
- a run már nem csak nesting metrikákkal rendelkezik
- gyártási összehasonlításra is alkalmas alap adatok vannak

---

## H2-10 — End-to-end manufacturing pilot

### Cél
A teljes H2 lánc fusson végig mintaprojekten.

### Deliverable
- nesting run + manufacturing selection
- manufacturing plan
- preview artifact
- machine-neutral export artifact
- alap postprocessor output

### DoD
- a nesting eredményből gyártási terv lesz
- a gyártási tervből export jellegű artifact keletkezik
- a teljes út auditálható

---

## H2 ajánlott megvalósítási sorrend

1. manufacturing profile domain aktiválása
2. manufacturing derivative generation
3. contour classification
4. cut rule set és contour rule modell
5. manufacturing snapshot bővítés
6. manufacturing plan builder
7. preview generator
8. postprocessor adapter alap
9. manufacturing metrics
10. end-to-end pilot

Ez a sorrend azért jó, mert előbb a gyártási “truth” világot zárja le, és csak utána építi rá az exportot.

---

## H2 első teljes smoke-flow

A H2 végén minimum ezt kell tudni:

1. egy projektben kiválasztott technology profile mellé kiválasztunk manufacturing profile versiont
2. a part revision rendelkezik approved manufacturing derivative-tel
3. a manufacturing derivative contourjai osztályozásra kerülnek
4. a manufacturing profil a megfelelő cut rule setekre mutat
5. létrejön egy nesting run
6. a snapshot már tartalmazza a manufacturing és postprocess kiválasztásokat
7. a solver run lefut
8. létrejön a run placement projection
9. a manufacturing plan builder a placement + derivative + contour class + rule set alapján gyártási tervet készít
10. létrejön `run_manufacturing_plans`
11. létrejönnek `run_manufacturing_contours`
12. generálódik `manufacturing_plan_json`
13. generálódik `manufacturing_preview_svg`
14. opcionálisan generálódik machine-ready artifact
15. kitöltődik `run_manufacturing_metrics`
16. a frontend/backoffice vissza tudja nézni a gyártási tervet

Ha ez megbízhatóan működik, a H2 késznek tekinthető.

---

## H2 siker kritériumai

A H2 akkor tekinthető sikeresnek, ha:

- a platform külön kezeli a nesting és manufacturing geometriát
- a manufacturing profilok ténylegesen működnek
- a contourok technológiai osztályozást kapnak
- a rule set alapú lead-in/lead-out logika működőképes
- a run snapshot gyártási oldala is reprodukálható
- a runból manufacturing plan jön létre
- a manufacturing preview és a machine-neutral export elkészül
- a postprocessor integráció külön modulként működik
- a gyártási metrikák legalább alap szinten mérhetők

---

## H2 technikai adósságok, amiket nem szabad bent hagyni

A H2 végére nem maradhat bent:

- manufacturing szabályok egy nagy átláthatatlan JSON-ban
- nesting derivative használata manufacturing truthként mindenhol
- machine-ready output mint egyetlen igazságforrás
- postprocessor közvetlenül solver raw outputból dolgozik
- contour classification nem mentődik el és nem auditálható
- manufacturing selection nincs snapshotolva
- outer és inner contour technológia nincs külön kezelve
- preview csak solver layoutot mutat gyártási meta nélkül

Ezek később nagyon drága architekturális hibák lennének.

---

## H2 kimeneti dokumentumcsomag

A H2 lezárásához ideális esetben legyen:

- `docs/platform/h2_manufacturing_architecture.md`
- `docs/platform/h2_cut_rule_model.md`
- `docs/platform/h2_contour_classification.md`
- `docs/platform/h2_manufacturing_plan_contract.md`
- `docs/platform/h2_postprocessor_adapter.md`
- `docs/platform/h2_manufacturing_metrics.md`
- `supabase/migrations/...`
- pilot manufacturing tesztdokumentum

---

## H2 tesztstratégia minimum

### Adatmodell tesztek
- manufacturing profile és project selection konzisztencia
- cut rule set és contour rule relációk
- manufacturing plan FK lánc
- postprocessor version hivatkozások

### Pipeline tesztek
- manufacturing derivative létrejön
- contour classification mentődik
- rule matching működik
- manufacturing plan épül run után
- preview artifact generálódik

### Hibatesztek
- hiányzó manufacturing profile
- hiányzó manufacturing derivative
- rule set mismatch
- contour classification failure
- postprocessor adapter failure

### Jogosultsági tesztek
- manufacturing profilok csak jogosult projektekből használhatók
- machine-ready artifact hozzáférés védett
- postprocessor config nem szivárog nem jogosult usernek

---

## H2 utáni logikus következő szakasz

A H2 után lehet igazán mély ipari irányba menni:

- fejlettebb cut order optimalizálás
- termikus és gyártásminőségi szabályok
- mikrokötések / tabs
- komolyabb piercing modellek
- több célgép-család export
- inventory/remnant üzleti integráció
- gyártási költség és idő alapú rangsorolás
- operátori review/szerkesztő workflow
- batch és multi-run manufacturing összehasonlítás

A H2 tehát az a pont, ahol a platform már **gyártásközeli intelligenciát** hordoz, nem csak elhelyezési logikát.

---

## Egyenes összefoglalás

A H1 végére a platform képes egy DXF-ből nesting eredményt csinálni.  
A H2 végére a platform képes ebből **gyártási tervet** is csinálni.

A H2 lényege, hogy a rendszerben külön réteggé váljon a manufacturing világ: külön geometriával, külön szabályrendszerrel, külön snapshotolt kiválasztással, külön tervszinttel és külön postprocess előkészítéssel. Ettől lesz a platform valóban ipari irányba bővíthető, anélkül hogy a solver vagy a frontend köré káoszosan ráépülne a teljes CAM-logika.

---

## H2 lezarasi allapot (2026-03-24)

A H2 mainline closure audit (H2-E6-T2) eredmenye: **PASS WITH ADVISORIES**.

- 14 kotelezo H2 mainline task: 12 PASS + 2 PASS_WITH_NOTES, 0 FAIL.
- End-to-end manufacturing pilot (H2-E6-T1): 60/60 teszt PASS.
- H2-E5-T4 machine-specific adapter: optionalis, nem PASS feltetel.
- H2-E5-T5 masodik machine-specific adapter (QtPlasmaC): optionalis ag, `linuxcnc_qtplasmac` / `basic_manual_material_rs274ngc` target. Nem H2 blocker.
- Reszletes gate dokumentum: `docs/web_platform/roadmap/h2_lezarasi_kriteriumok_es_h3_entry_gate.md`.
