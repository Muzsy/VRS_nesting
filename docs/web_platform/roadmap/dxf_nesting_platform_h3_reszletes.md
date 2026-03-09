# DXF Nesting Platform — H3 részletes terv

## Cél

A **H3** a platform ipari optimalizációs és döntéstámogató mélyítési szintje.  
A H0 lezárta a szerkezeti alapot, a H1 működőképessé tette a teljes DXF → geometry → run → eredmény csatornát, a H2 pedig beemelte a manufacturing és postprocess világot.  
A H3 feladata az, hogy a rendszer túllépjen az egyetlen futásból származó “egy eredmény” modellen, és belépjen a **stratégiai optimalizálás, összehasonlítás és operatív döntéstámogatás** szintjére.

A H3 központi kérdése már nem az, hogy:

- be tudjuk-e tenni az alkatrészeket,
- tudunk-e gyártási tervet képezni,

hanem az, hogy:

- **melyik futás a jobb**, és miért,
- **melyik táblafelhasználási stratégia** a jobb,
- **milyen kompromisszumot** érdemes választani kihasználtság, gyártási idő, selejt, maradékérték és prioritások között,
- hogyan kezeljük a **remnant/inventory** világot,
- és hogyan adunk a felhasználónak nem csak egy eredményt, hanem **döntési teret és összehasonlítható opciókat**.

A H3 tehát a platformot a “futtató rendszerből” **optimalizáló és választást támogató rendszerré** emeli.

---

## H3 fő célképe

A H3 végére a rendszernek az alábbi képességeket kell tudnia:

1. **Egy projekthez több run-stratégia és több eredmény kezelése**
   - nem csak egy futás
   - hanem variánsok, batch-ek, candidate-ek
   - összehasonlítható outputokkal

2. **Többdimenziós ranking és scoring**
   - kihasználtság
   - unplaced mennyiség
   - sheet count
   - remnant value
   - estimated manufacturing cost/time
   - priority fulfilment
   - opcionálisan kockázati/quality score

3. **Run-összehasonlítás és döntéstámogatás**
   - “legjobb anyagkihasználás”
   - “leggyorsabb gyártás”
   - “legjobb prioritásteljesítés”
   - “legértékesebb maradék”
   - multi-objective összehasonlítás

4. **Remnant és inventory világ első komoly integrálása**
   - remnant mint projektből keletkező jövőbeni input
   - stock és remnant elkülönítése
   - remnant minősítés és újrahasznosítás

5. **Review-loopok és emberi döntési pontok beépítése**
   - run jelölés
   - preferált eredmény kiválasztása
   - manuális review státuszok
   - operatív elfogadás/eldobás

6. **A H2 manufacturing réteg és a H3 optimalizáció ne keveredjen össze**
   - a H3 nem CAM motor
   - a H3 nem UI-only dashboard
   - a H3 az értékelési és választási réteg

---

## H3 szerepe a roadmapban

A H3 az a szint, ahol a platform nem csak “képes futni”, hanem **képes értelmesen választani is**.

### H2 után mi hiányzik még?
A H2 végére a rendszer tud:
- DXF-ből elhelyezési eredményt előállítani,
- ebből manufacturing tervet képezni,
- preview-t és exportot generálni.

De még hiányzik:
- a többfutásos gondolkodás,
- a döntési szempontok kezelése,
- a maradékanyag mint üzleti erőforrás kezelése,
- az összehasonlító és review folyamat.

### H3-ben mi történik?
A H3-ban a rendszer:
- candidate runokat kezel,
- ezeket rangsorolja,
- a maradékanyagot értékeli,
- készlet- és remnant-inputokat képes figyelembe venni,
- és a felhasználó számára döntéstámogató nézeteket ad.

Ez az a pont, ahol a platform már valóban **ipari üzleti értéket** kezd termelni, nem csak technikai eredményt.

---

## H3 scope

## H3-be tartozik

- multi-run / batch-run modell
- run strategy profilok és variánsok
- candidate scoring és ranking
- objective profile vagy scoring profile modell
- remnant / stock domain első működő integrációja
- remnant képzés run eredményből
- remnant újrafelhasználási logika alapjai
- priority fulfilment scoring
- cost/time/remnant kombinált metrikák
- run comparison nézetek
- preferred run / approved run kiválasztás
- review workflow alapjai
- scenario/preset alapú futtatás
- “best of” összehasonlító lekérdezések
- döntéstámogató projection réteg
- batch eredmények aggregált megjelenítése

## H3-be nem tartozik teljes mélységben

- teljes ERP/MES készlettervezés
- részletes gyártásütemezés
- teljes pénzügyi kontrolling modul
- machine park szintű allokációoptimalizálás
- gyártósori scheduling
- AI-alapú autonóm döntéshozatal emberi jóváhagyás nélkül
- teljes manuális grafikus nesting szerkesztő
- összes lehetséges multi-objective tudományos optimalizációs stratégia

A H3 célja a **platformszintű összehasonlítás, értékelés és remnant-integráció első ipari szintje**, nem a teljes gyárirányítás.

---

## H3 architekturális döntések

## 1. Egy run már nem elég: candidate-világ kell

A H3-ban el kell engedni azt a modellt, hogy egy projekthez egyetlen “helyes” nesting run tartozik.

A valóságban ugyanarra az inputra több értelmes megoldás létezhet:
- más sheet-felhasználással,
- más kihasználtsággal,
- más gyártási idővel,
- más remnant-értékkel,
- más priority fulfilmenttel.

Ezért a H3-ban a platformnak kezelnie kell:
- több run ugyanarra a projektre,
- több stratégiai variánsot,
- és ezek közti összehasonlítást.

---

## 2. A ranking külön domain legyen, ne szétszórt logika

A H3-ban tilos, hogy a runok “értékelése” csak a frontendben vagy ad-hoc SQL-ben éljen.

A scoringnak és rankingnek:
- verziózhatónak,
- reprodukálhatónak,
- visszakereshetőnek,
- snapshotolhatónak,
- és indokolhatónak kell lennie.

Ezért kell külön:
- scoring profile / objective profile
- run evaluation táblák
- ranking outcome

---

## 3. A remnant ne csak artifact legyen, hanem domain entitás

A H2-ig a maradék alapvetően következmény.  
A H3-ban a remnant már **jövőbeni input** is.

Ezért a maradékanyagot nem elég képként vagy DXF-ként elmenteni.  
A remnantnak saját entitásnak kell lennie:
- azonosítható legyen,
- geometriailag leírható legyen,
- minősíthető legyen,
- állapota legyen,
- és felhasználható legyen későbbi futásokban.

---

## 4. A stock és a remnant külön világ maradjon

Fontos döntés:

- **stock sheet** = alap készlet vagy szabványos tábla
- **remnant sheet** = egy korábbi runból keletkezett, geometriailag és üzletileg külön kezelt maradék

A H3-ban ezeket nem szabad összemosni.  
A felhasználó másképp viszonyul hozzájuk:
- más az értékük,
- más a bizonytalanságuk,
- más az elérhetőségük,
- és más a jövőbeli kezelési logikájuk.

---

## 5. A review és approval workflow különüljön el a run létezésétől

A run attól még létezik, hogy nem azt választják ki.  
A H3-ban ezért külön kell kezelni:

- run technical completion
- run business review
- run operational selection
- run manufacturing approval

Magyarul:
egy futás lehet sikeres technikailag, de nem biztos, hogy azt akarjuk gyártásra vinni.

---

## H3 részletes domainbővítés

## 1. Run strategy profilok

A H3-ban érdemes külön kezelni, hogy milyen stratégiával futtatunk.

Új táblák javasoltak:

```sql
create table if not exists app.run_strategy_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists app.run_strategy_profile_versions (
  id uuid primary key default gen_random_uuid(),
  run_strategy_profile_id uuid not null references app.run_strategy_profiles(id) on delete cascade,
  version_no integer not null,
  solver_config_jsonb jsonb not null default '{}'::jsonb,
  placement_config_jsonb jsonb not null default '{}'::jsonb,
  manufacturing_bias_jsonb jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (run_strategy_profile_id, version_no)
);
```

Ez nem azonos a technology profile-lal.  
A technology az anyag/gép/spacing világ.  
A run strategy a futtatási döntésvilág:
- agresszív kitöltés
- gyors megoldás
- priority-first
- remnant-aware
- manufacturing-biased stb.

---

## 2. Objective / scoring profile

Új táblák:

```sql
create table if not exists app.scoring_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists app.scoring_profile_versions (
  id uuid primary key default gen_random_uuid(),
  scoring_profile_id uuid not null references app.scoring_profiles(id) on delete cascade,
  version_no integer not null,
  weights_jsonb jsonb not null default '{}'::jsonb,
  tie_breaker_jsonb jsonb not null default '{}'::jsonb,
  threshold_jsonb jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (scoring_profile_id, version_no)
);
```

A `weights_jsonb` tartalmazhat például:
- utilization_weight
- unplaced_penalty
- sheet_count_penalty
- remnant_value_weight
- process_time_penalty
- priority_fulfilment_weight
- inventory_consumption_penalty

Ez a H3 egyik kulcsa: a scoring explicit és verziózott.

---

## 3. Project-level strategy és scoring selection

```sql
create table if not exists app.project_run_strategy_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_run_strategy_profile_version_id uuid not null references app.run_strategy_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now()
);

create table if not exists app.project_scoring_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_scoring_profile_version_id uuid not null references app.scoring_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now()
);
```

Ez azért kell, mert egy projektben nem csak a technológia, hanem a döntési preferencia is különbözhet.

---

## 4. Run batch és candidate domain

A H3-ban javasolt külön batch fogalom.

```sql
create table if not exists app.run_batches (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  created_by uuid references app.profiles(id) on delete set null,
  batch_kind text not null default 'comparison',
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists app.run_batch_items (
  batch_id uuid not null references app.run_batches(id) on delete cascade,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  candidate_label text,
  strategy_profile_version_id uuid references app.run_strategy_profile_versions(id) on delete set null,
  scoring_profile_version_id uuid references app.scoring_profile_versions(id) on delete set null,
  primary key (batch_id, run_id)
);
```

Ez adja a több-run összehasonlítás szerkezetét.

---

## 5. Run evaluation és ranking

A H3 egyik legfontosabb táblacsoportja.

```sql
create table if not exists app.run_evaluations (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  scoring_profile_version_id uuid references app.scoring_profile_versions(id) on delete set null,
  total_score numeric(18,6),
  evaluation_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists app.run_ranking_results (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references app.run_batches(id) on delete cascade,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  rank_no integer not null,
  ranking_reason_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (batch_id, run_id),
  unique (batch_id, rank_no)
);
```

A `evaluation_jsonb` tartalmazza az összetevőket:
- utilization score
- priority fulfilment score
- remnant score
- process time penalty
- sheet count penalty stb.

---

## 6. Preferred / approved run kiválasztás

A H3-ban külön táblába kell vinni az emberi döntést.

```sql
create table if not exists app.project_selected_runs (
  project_id uuid primary key references app.projects(id) on delete cascade,
  selected_run_id uuid not null references app.nesting_runs(id) on delete restrict,
  selection_kind text not null default 'preferred',
  selected_by uuid references app.profiles(id) on delete set null,
  selection_notes text,
  selected_at timestamptz not null default now()
);
```

Ez lehetővé teszi:
- preferred run
- approved for manufacturing
- archived choice
- override choice

A pontos státuszkészlet később finomítható.

---

## 7. Review workflow táblák

```sql
create table if not exists app.run_reviews (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  review_stage text not null,
  review_status text not null,
  reviewed_by uuid references app.profiles(id) on delete set null,
  review_notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Lehetséges `review_stage`:
- `technical`
- `production`
- `cost`
- `final_selection`

Lehetséges `review_status`:
- `pending`
- `accepted`
- `rejected`
- `needs_changes`

Ez elválasztja a technikai eredményt az emberi döntéstől.

---

## 8. Remnant inventory domain

A H3 egyik fő újdonsága.

```sql
create table if not exists app.remnant_definitions (
  id uuid primary key default gen_random_uuid(),
  source_run_id uuid references app.nesting_runs(id) on delete set null,
  source_sheet_id uuid references app.run_layout_sheets(id) on delete set null,
  geometry_derivative_id uuid references app.geometry_derivatives(id) on delete set null,
  material_id uuid references app.material_catalog(id) on delete set null,
  thickness_mm numeric(10,3),
  estimated_value numeric(14,2),
  remnant_status text not null default 'available',
  created_at timestamptz not null default now()
);

create table if not exists app.remnant_revisions (
  id uuid primary key default gen_random_uuid(),
  remnant_definition_id uuid not null references app.remnant_definitions(id) on delete cascade,
  revision_no integer not null,
  geometry_jsonb jsonb not null,
  bbox_jsonb jsonb not null default '{}'::jsonb,
  area_mm2 numeric(18,4),
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (remnant_definition_id, revision_no)
);

create table if not exists app.remnant_stock_items (
  id uuid primary key default gen_random_uuid(),
  remnant_revision_id uuid not null references app.remnant_revisions(id) on delete restrict,
  project_id uuid references app.projects(id) on delete set null,
  storage_location text,
  is_reserved boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
```

A cél:
- a remnantnak saját identitása legyen,
- legyen revíziója,
- legyen készletszerű állapota,
- és később sheet inputként újra felhasználható legyen.

---

## 9. Stock sheet domain különválasztása

H3-ban már célszerű külön stock világ is.

```sql
create table if not exists app.stock_sheet_items (
  id uuid primary key default gen_random_uuid(),
  sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict,
  project_id uuid references app.projects(id) on delete set null,
  storage_location text,
  quantity integer not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
```

Ez szándékosan külön marad a remnanttól.

---

## 10. Run input source tracking

A H3-ban már nem elég annyi, hogy “sheet inputok voltak”.  
Nyomon kell követni, hogy a run stockot vagy remnantot fogyasztott.

```sql
create table if not exists app.run_input_sheet_sources (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  source_kind text not null,
  stock_sheet_item_id uuid references app.stock_sheet_items(id) on delete set null,
  remnant_stock_item_id uuid references app.remnant_stock_items(id) on delete set null,
  sheet_revision_id uuid references app.sheet_revisions(id) on delete set null,
  used_qty integer not null default 1,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

`source_kind` lehet például:
- `stock`
- `remnant`
- `ad_hoc_project_sheet`

---

## 11. Priority fulfilment és business metrics

A H3-ban a prioritás már nem csak solver input.  
Mérni is kell, mennyire teljesült.

Új tábla javasolt:

```sql
create table if not exists app.run_business_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  priority_fulfilment_ratio numeric(8,5),
  hard_first_placed_ratio numeric(8,5),
  deferred_part_usage_ratio numeric(8,5),
  estimated_material_cost numeric(14,2),
  estimated_remnant_value numeric(14,2),
  estimated_total_cost numeric(14,2),
  metrics_jsonb jsonb not null default '{}'::jsonb
);
```

Ez a H3 döntéstámogatás egyik alaptáblája.

---

## H3 Supabase SQL — részletes bővítési váz

```sql
create table if not exists app.run_strategy_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists app.run_strategy_profile_versions (
  id uuid primary key default gen_random_uuid(),
  run_strategy_profile_id uuid not null references app.run_strategy_profiles(id) on delete cascade,
  version_no integer not null,
  solver_config_jsonb jsonb not null default '{}'::jsonb,
  placement_config_jsonb jsonb not null default '{}'::jsonb,
  manufacturing_bias_jsonb jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (run_strategy_profile_id, version_no)
);

create table if not exists app.scoring_profiles (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references app.profiles(id) on delete restrict,
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists app.scoring_profile_versions (
  id uuid primary key default gen_random_uuid(),
  scoring_profile_id uuid not null references app.scoring_profiles(id) on delete cascade,
  version_no integer not null,
  weights_jsonb jsonb not null default '{}'::jsonb,
  tie_breaker_jsonb jsonb not null default '{}'::jsonb,
  threshold_jsonb jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (scoring_profile_id, version_no)
);

create table if not exists app.project_run_strategy_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_run_strategy_profile_version_id uuid not null references app.run_strategy_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now()
);

create table if not exists app.project_scoring_selection (
  project_id uuid primary key references app.projects(id) on delete cascade,
  active_scoring_profile_version_id uuid not null references app.scoring_profile_versions(id) on delete restrict,
  selected_at timestamptz not null default now()
);

create table if not exists app.run_batches (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references app.projects(id) on delete cascade,
  created_by uuid references app.profiles(id) on delete set null,
  batch_kind text not null default 'comparison',
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists app.run_batch_items (
  batch_id uuid not null references app.run_batches(id) on delete cascade,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  candidate_label text,
  strategy_profile_version_id uuid references app.run_strategy_profile_versions(id) on delete set null,
  scoring_profile_version_id uuid references app.scoring_profile_versions(id) on delete set null,
  primary key (batch_id, run_id)
);

create table if not exists app.run_evaluations (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  scoring_profile_version_id uuid references app.scoring_profile_versions(id) on delete set null,
  total_score numeric(18,6),
  evaluation_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists app.run_ranking_results (
  id uuid primary key default gen_random_uuid(),
  batch_id uuid not null references app.run_batches(id) on delete cascade,
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  rank_no integer not null,
  ranking_reason_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (batch_id, run_id),
  unique (batch_id, rank_no)
);

create table if not exists app.project_selected_runs (
  project_id uuid primary key references app.projects(id) on delete cascade,
  selected_run_id uuid not null references app.nesting_runs(id) on delete restrict,
  selection_kind text not null default 'preferred',
  selected_by uuid references app.profiles(id) on delete set null,
  selection_notes text,
  selected_at timestamptz not null default now()
);

create table if not exists app.run_reviews (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  review_stage text not null,
  review_status text not null,
  reviewed_by uuid references app.profiles(id) on delete set null,
  review_notes text,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists app.remnant_definitions (
  id uuid primary key default gen_random_uuid(),
  source_run_id uuid references app.nesting_runs(id) on delete set null,
  source_sheet_id uuid references app.run_layout_sheets(id) on delete set null,
  geometry_derivative_id uuid references app.geometry_derivatives(id) on delete set null,
  material_id uuid references app.material_catalog(id) on delete set null,
  thickness_mm numeric(10,3),
  estimated_value numeric(14,2),
  remnant_status text not null default 'available',
  created_at timestamptz not null default now()
);

create table if not exists app.remnant_revisions (
  id uuid primary key default gen_random_uuid(),
  remnant_definition_id uuid not null references app.remnant_definitions(id) on delete cascade,
  revision_no integer not null,
  geometry_jsonb jsonb not null,
  bbox_jsonb jsonb not null default '{}'::jsonb,
  area_mm2 numeric(18,4),
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (remnant_definition_id, revision_no)
);

create table if not exists app.remnant_stock_items (
  id uuid primary key default gen_random_uuid(),
  remnant_revision_id uuid not null references app.remnant_revisions(id) on delete restrict,
  project_id uuid references app.projects(id) on delete set null,
  storage_location text,
  is_reserved boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists app.stock_sheet_items (
  id uuid primary key default gen_random_uuid(),
  sheet_revision_id uuid not null references app.sheet_revisions(id) on delete restrict,
  project_id uuid references app.projects(id) on delete set null,
  storage_location text,
  quantity integer not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists app.run_input_sheet_sources (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references app.nesting_runs(id) on delete cascade,
  source_kind text not null,
  stock_sheet_item_id uuid references app.stock_sheet_items(id) on delete set null,
  remnant_stock_item_id uuid references app.remnant_stock_items(id) on delete set null,
  sheet_revision_id uuid references app.sheet_revisions(id) on delete set null,
  used_qty integer not null default 1,
  metadata_jsonb jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists app.run_business_metrics (
  run_id uuid primary key references app.nesting_runs(id) on delete cascade,
  priority_fulfilment_ratio numeric(8,5),
  hard_first_placed_ratio numeric(8,5),
  deferred_part_usage_ratio numeric(8,5),
  estimated_material_cost numeric(14,2),
  estimated_remnant_value numeric(14,2),
  estimated_total_cost numeric(14,2),
  metrics_jsonb jsonb not null default '{}'::jsonb
);
```

---

## H3 szükséges szolgáltatásrétegek

## 1. Batch run orchestrator

Feladata:
- több run létrehozása ugyanarra a projektre
- különböző strategy/scoring kombinációk alkalmazása
- batch rekord és batch itemek létrehozása
- candidate címkék kezelése

Példák:
- `material_max`
- `fast_turnaround`
- `priority_first`
- `remnant_preserve`
- `balanced`

Ez a H3 egyik fő szolgáltatása.

---

## 2. Run evaluation engine

Feladata:
- a kész run metrikáiból score számítása
- scoring profile verzió alapján értékelés
- `run_evaluations` kitöltése
- komponensszintű scoring bontás tárolása

A H3-ban már nem elég a nyers metrika.  
Értelmezett pontszám kell.

---

## 3. Ranking engine

Feladata:
- batch összes runjának rangsorolása
- tie-breakerek alkalmazása
- `run_ranking_results` kitöltése
- ranking_reason tárolása

Ez biztosítja, hogy a döntés nem fekete doboz legyen.

---

## 4. Remnant extractor

Feladata:
- a run eredményből keletkező maradék geometriák felismerése
- remnant definition/revision létrehozása
- értékbecslés
- remnant stock item létrehozása

Ez a H3 egyik legfontosabb ipari szolgáltatása.

---

## 5. Inventory-aware run input resolver

Feladata:
- sheet input források kiválasztása
- stock vs remnant preferencia kezelése
- run_input_sheet_sources kitöltése
- source-követés biztosítása

Később ez lehet bonyolult optimalizáló modul, H3-ban elég az első működő policy-rendszer.

---

## 6. Business metrics calculator

Feladata:
- priority fulfilment számítása
- költségbecslések
- remnant value becslés
- total cost jellegű aggregálás

Ez a H3 decision layer fontos komponense.

---

## 7. Run comparison projection builder

Feladata:
- több runból összehasonlító nézet építése
- batch summary projection
- top candidate listák
- “best by objective” aggregációk

A H3-ban célszerű ezt nem csak frontendben számolni, hanem strukturált projectionként kezelni.

---

## 8. Review workflow service

Feladata:
- review stage-ek nyitása/zárása
- review státuszváltozások
- selected run beállítása
- review notes és döntési indokok tárolása

Ez összeköti a technikai világot az emberi döntéssel.

---

## H3 alfeladatok részletes bontásban

## H3-1 — Run strategy és scoring profile domain

### Cél
A futtatási stratégia és az értékelési preferencia legyen explicit, verziózott és projektből kiválasztható.

### Deliverable
- run_strategy_profiles
- run_strategy_profile_versions
- scoring_profiles
- scoring_profile_versions
- project-level selection táblák

### DoD
- projekt szinten választható strategy és scoring profil
- ezek hivatkozása snapshotolható
- nem frontend-hardcode a scoring logika

---

## H3-2 — Batch run modell

### Cél
Egy projektből több összehasonlítható run indulhasson.

### Deliverable
- run_batches
- run_batch_items
- batch létrehozó service
- candidate címkék

### DoD
- több run ugyanabba a batch-be szervezhető
- a batchből később ranking építhető
- a runok strategy/scoring kontextusa visszakereshető

---

## H3-3 — Run evaluation engine

### Cél
A run metrikákból számított score jöjjön létre.

### Deliverable
- evaluation logic
- `run_evaluations`
- komponens-szintű score bontás
- threshold/tie-breaker kezelés alapja

### DoD
- egy runhoz reprodukálható score tartozik
- a score indokolható komponensekre bontva
- a scoring profile verziója rögzített

---

## H3-4 — Ranking engine és batch összehasonlítás

### Cél
A batchen belüli runok rendezhetők és magyarázhatók legyenek.

### Deliverable
- ranking service
- `run_ranking_results`
- ranking reason json
- best candidate meghatározás

### DoD
- batchre kiszámolható rangsor
- tie-break szabályok működnek
- visszakereshető, miért lett egy run első

---

## H3-5 — Remnant domain

### Cél
A maradékanyag önálló üzleti/domain entitássá váljon.

### Deliverable
- remnant_definitions
- remnant_revisions
- remnant_stock_items
- remnant státuszok
- értékbecslési mezők

### DoD
- run után remnant entitás létrehozható
- remnant geometria tárolható
- remnant később újra felhasználható input lehet

---

## H3-6 — Stock és remnant input resolver

### Cél
A futtatás tudja, hogy milyen forrásból fogyaszt táblát.

### Deliverable
- stock_sheet_items
- run_input_sheet_sources
- source selection policy
- stock/remnant preferencia alaplogika

### DoD
- a run input forrása visszakereshető
- külön kezeljük a stockot és a remnantot
- a forrás a business metricsben és auditban is látható

---

## H3-7 — Business metrics és decision layer

### Cél
A runok ne csak geometriailag, hanem üzletileg is értékelhetők legyenek.

### Deliverable
- run_business_metrics
- priority fulfilment számítás
- estimated material/remnant/total cost
- decision-support JSON összesítés

### DoD
- a runok üzleti oldalról is összehasonlíthatók
- a prioritások teljesülése mérhető
- a remnant érték explicit része a döntésnek

---

## H3-8 — Review és selected run workflow

### Cél
A rendszer kezelje a humán döntési folyamatot.

### Deliverable
- run_reviews
- project_selected_runs
- review státuszlogika
- preferred / approved run flow

### DoD
- egy futás kijelölhető preferáltként
- review megjegyzések visszakereshetők
- technikai és üzleti döntés külön kezelődik

---

## H3-9 — Comparison projection és UI-ready aggregációk

### Cél
A frontend/backoffice ne nyers run-listákból rakja össze a döntéstámogatást.

### Deliverable
- összehasonlító projection builder
- batch summary adatok
- top candidate listák
- best-by-objective nézetek

### DoD
- egy batchből könnyen lekérdezhető a top run
- objective szerint külön listák kérhetők
- a döntési nézet nem csak frontend számolásból áll

---

## H3-10 — End-to-end comparison + remnant pilot

### Cél
A H3 teljes lánca fusson le valós mintán.

### Deliverable
- legalább egy batch több runnal
- scoring és ranking
- selected run
- remnant extractor
- remnant újrafelhasználási próbafolyamat
- comparison nézet

### DoD
- több run közül választani lehet
- a döntés indokolható
- remnant entitások keletkeznek és nyomon követhetők
- a platform valódi operatív támogatást nyújt

---

## H3 ajánlott megvalósítási sorrend

1. run strategy profile domain
2. scoring profile domain
3. batch run modell
4. evaluation engine
5. ranking engine
6. remnant domain
7. stock/remnant input resolver
8. business metrics
9. review/selected run workflow
10. comparison projection
11. end-to-end pilot

Ez a sorrend azért jó, mert előbb az összehasonlítás logikája áll össze, és utána kapcsolódik rá a remnant és review világ.

---

## H3 első teljes smoke-flow

A H3 végén minimum ezt kell tudni:

1. egy projektben kiválasztunk technology, manufacturing, strategy és scoring profilokat
2. létrehozunk egy run batch-et
3. a batch több candidate runból áll
4. a runok különböző strategy profilokkal lefutnak
5. mindegyikhez létrejön nesting eredmény, manufacturing terv és metrikák
6. a run evaluation engine kiszámolja az összesített score-t
7. a ranking engine batchen belül sorrendet képez
8. a comparison projection megmutatja a különbségeket
9. a felhasználó review-zza a top candidate-eket
10. kijelöl egy preferred vagy approved run-t
11. a remnant extractor a kiválasztott vagy összes runból remnant entitásokat képez
12. a remnant készletbe kerül
13. egy következő projekt/runnál a resolver ezeket potenciális inputként figyelembe tudja venni

Ha ez működik, a H3 sikeres.

---

## H3 siker kritériumai

A H3 akkor tekinthető sikeresnek, ha:

- a platform több runból tud választani
- a scoring explicit és verziózott
- a ranking reprodukálható és indokolható
- a remnant nem csak artifact, hanem újrahasznosítható entitás
- a stock és remnant külön kezelt inputforrás
- a business metrics tényleges döntéstámogatást ad
- a review és selected run workflow működik
- a comparison réteg frontend-barát módon lekérdezhető
- a rendszer operatív szinten már nem csak számol, hanem támogatja a választást is

---

## H3 technikai adósságok, amiket nem szabad bent hagyni

A H3 végére nem maradhat bent:

- scoring logika szétszórva frontendben és ad-hoc query-kben
- remnant csak DXF artifactként létezik domain entitás nélkül
- selected run kijelölés nincs külön nyilvántartva
- batch runok stratégiai kontextusa elveszik
- stock és remnant források nem különülnek el
- ranking nem indokolható vissza
- review státuszok nincsenek elválasztva a technikai run állapottól
- business metrics hiányzik vagy csak manuálisan számolható

Ezek hosszú távon szétvernék a döntéstámogatási réteget.

---

## H3 kimeneti dokumentumcsomag

A H3 lezárásához ideális esetben legyen:

- `docs/platform/h3_strategy_and_scoring.md`
- `docs/platform/h3_batch_runs_and_ranking.md`
- `docs/platform/h3_remnant_inventory_model.md`
- `docs/platform/h3_business_metrics.md`
- `docs/platform/h3_review_and_selection_workflow.md`
- `docs/platform/h3_comparison_projections.md`
- `supabase/migrations/...`
- comparison/remnant pilot dokumentum

---

## H3 tesztstratégia minimum

### Adatmodell tesztek
- strategy/scoring version relációk
- batch és ranking unique szabályok
- selected run project konzisztencia
- remnant revision és stock item relációk

### Pipeline tesztek
- batch run létrejön
- evaluation fut
- ranking eredmény képződik
- remnant extractor létrehozza az entitásokat
- comparison projection épül

### Hibatesztek
- hiányzó scoring profile
- batchben futott, de nem értékelhető run
- ranking tie-break hiba
- remnant extract failure
- invalid selected run

### Jogosultsági tesztek
- user nem lát más projekt batch összehasonlítását
- remnant készlet hozzáférése védett
- selected run módosítás jogosultsághoz kötött
- review flow nem nyitható illetéktelenül

---

## H3 utáni logikus következő szakasz

A H3 után már a nagyon mély ipari és üzleti optimalizációk jöhetnek:

- komplex multi-objective keresés
- gyártósori és gépparki allokáció
- részletes költség- és időmodellek
- mély inventory stratégia
- operátori interaktív finomhangolás
- teljes workflow integráció ERP/MES irányba
- autonóm ajánlórendszer a batch candidate-ekre
- historikus tanulás az elfogadott runokból

A H3 tehát a kapu a “jó nesting platform” és a “döntést támogató ipari optimalizációs platform” között.

---

## Egyenes összefoglalás

A H1 működőképessé teszi a platformot.  
A H2 gyártásközelivé teszi.  
A H3 pedig **választásra és optimalizációra alkalmassá** teszi.

A H3 lényege, hogy a rendszer kezelni tudja a többfutásos világot, a pontozási és rangsorolási logikát, a remnant mint erőforrás világát, és az emberi review/approval döntési pontokat. Ettől lesz a platform nem csak számoló motor, hanem valódi, ipari döntéstámogató rendszer.
