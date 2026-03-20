# H1-E6-T1 Result normalizer (H1 minimum)

## Funkcio
A feladat a H1-E6 elso, szukitett lepese: a H1-E5-T3-ban mar visszakereshetoen
eltarolt raw solver output platformnyelvre forditasa ugy, hogy a H0 canonical
projection tablavilag (`app.run_layout_*`, `app.run_metrics`) tenylegesen
feltoltodjon, es a run eredmenye ne csak raw `solver_output.json` artifactkent
letezzen.

Ez a task tudatosan **nem** viewer SVG/DXF generalas, **nem** export pipeline,
**nem** raw artifact storage redesign es **nem** nagy runs API ujratervezes. A
cel kizarolag az, hogy a workernek legyen explicit, tesztelheto
result-normalizer boundaryja, amely a raw solver outputbol stabil, query-zhato
projection reteget kepez.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - explicit worker-oldali result normalizer helper/service boundary bevezetese;
  - `solver_output.json` v1 -> `app.run_layout_sheets` mapping;
  - `solver_output.json` v1 -> `app.run_layout_placements` mapping;
  - `solver_output.json` v1 -> `app.run_layout_unplaced` mapping;
  - run-level `app.run_metrics` szamitas es frissites;
  - idempotens, run-szintu projection replace/upsert viselkedes;
  - a worker `done` zarasanak atallitasa ugy, hogy a canonical counts mar a
    normalizer osszegzesebol jojjenek;
  - task-specifikus smoke a sikeres es hibas normalizer agak bizonyitasara.
- Nincs benne:
  - `sheet_svg`, `sheet_dxf`, `bundle_zip` vagy egyeb viewer/export artifact
    generalas;
  - raw `run-artifacts` bucket/path policy ujranyitasa;
  - nagy `api/routes/runs.py` redesign vagy uj eredmenyendpoint;
  - uj schema/enum/tabla bevezetese, ha a H0 projection tablavilag eleg;
  - manufacturing/postprocess vagy H2/H3 metrikak.

### Talalt relevans fajlok
- `worker/main.py`
  - jelenleg a raw artifact mentes utan csak `_read_run_metrics(run_dir)` alapu
    countsot olvas, es nem tolti a H0 projection tablakat.
- `worker/engine_adapter_input.py`
  - ebbol latszik, hogyan lett a snapshotbol a solver input felteve; a
    normalizernek ehhez a mappinghoz kompatibilis visszafejtessel kell
    dolgoznia.
- `worker/raw_output_artifacts.py`
  - a raw artifact truth mar itt kulon boundaryban el; a projection normalizer
    ehhez kepest kulon, explicit reteg legyen.
- `api/services/run_snapshot_builder.py`
  - a snapshot manifestek (`parts_manifest_jsonb`, `sheets_manifest_jsonb`,
    `geometry_manifest_jsonb`) source-of-truth jelentik a part/sheet/geometry
    feloldashoz szukseges adatokat.
- `api/routes/runs.py`
  - jelenleg a viewer-data ag raw artifactokbol es raw solver outputbol epit;
    ez jo kontraszt arra, hogy a T1 projection-truth task, nem route-redesign.
- `docs/solver_io_contract.md`
  - a `solver_output.json` v1 contract source-of-truth-ja.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - a canonical run outcome/projection modell es a projection vs artifact
    szetvalasztas forrasa.
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - a `run_layout_*` es `run_metrics` fizikai truth tablavilag.
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - H1-E6-T1 source-of-truth.

### Konkret elvarasok

#### 1. Legyen explicit result normalizer boundary
A projection feltoltes ne maradjon szetszorva a workerben.

Hasznalj explicit worker-oldali helper/modult, peldaul:
- `worker/result_normalizer.py`
- vagy ezzel egyenerteku, jol tesztelheto boundary.

A helper minimum felelossege:
- a raw `solver_output.json` betoltese es valid top-level szerkezet ellenorzese;
- a snapshot manifestekbol a part/sheet truth indexek felallitasa;
- a projection sorok elokeszitese (`run_layout_sheets`, `run_layout_placements`,
  `run_layout_unplaced`, `run_metrics`);
- a run-szintu idempotens write/replace meghivasa;
- a worker szamara visszaadhato summary (`placed_count`, `unplaced_count`,
  `used_sheet_count`, opcionális sheet statok).

#### 2. A mapping a snapshot truth-ra uljon, ne ad hoc heuristikara
A result normalizer ne csak a raw solver outputot nezze, hanem a H1-E4-T1/H1-E5-T1
snapshot truth-bol oldja fel a platformentitasokat.

Minimum elvart mapping:
- `placement.part_id` -> `part_revision_id` a snapshot `parts_manifest_jsonb`
  alapjan;
- `placement.sheet_index` -> `sheet_revision_id`, `width_mm`, `height_mm` a
  snapshot `sheets_manifest_jsonb` mennyiseg szerint kiteritett sorrendje
  alapjan;
- a partgeometria/bbox truth a snapshot `geometry_manifest_jsonb`-bol jojjon,
  ne a worker talaljon ki uj meretforrast.

Ha a raw output olyan `part_id`-t vagy `sheet_index`-et ad, amely nem oldhato
fel a snapshotbol, az legyen determinisztikus normalizer hiba, ne csendes
adatvesztes.

#### 3. A projection sorok legyenek platform-kompatibilisek
A normalizer minimum ezt allitsa elo:

- `app.run_layout_sheets`
  - egy sor hasznalt sheet indexenkent;
  - `sheet_revision_id`, `width_mm`, `height_mm`, `utilization_ratio`,
    `metadata_jsonb` ertelmes kitoltessel.
- `app.run_layout_placements`
  - egy sor placementenkent;
  - `part_revision_id` a snapshot truth alapjan;
  - `quantity=1`;
  - `transform_jsonb` legalabb `x`, `y`, `rotation_deg`, `sheet_index`,
    `instance_id` informacioval;
  - `bbox_jsonb` determinisztikusan szamitva a snapshot geometry bbox es a
    placement transzformacio alapjan.
- `app.run_layout_unplaced`
  - ne nyers instance-lista dump legyen, hanem platformszintu projection;
  - minimum elvart, hogy `part_revision_id + reason` szinten aggregaljon es a
    `remaining_qty` mar a fennmaradt darabszamot jelentse;
  - a metadata tegye visszakereshetove az instance-szintu eredetet, ha ezt a
    task megorzi.
- `app.run_metrics`
  - `placed_count`, `unplaced_count`, `used_sheet_count`, `utilization_ratio`
    kitoltve;
  - `remnant_value` H1 minimum szinten maradhat `null`, ha nincs megbizhato
    gazdasagi input;
  - `metrics_jsonb` tartalmazzon ertelmes reszleteket (pl. per-sheet counts,
    raw status, runtime/meta atvezetett adatok) anelkul, hogy solver-specific
    dump lenne.

#### 4. A metrika-szamitas legyen determinisztikus es dokumentalt
A H1 minimum metrikak ne a legacy `report.json` fallbackbol vagy kulso route
heurisztikabol jojjenek.

Minimum elvart:
- `placed_count = placement sorok szama`;
- `unplaced_count = unplaced projection osszegzett darabszama`;
- `used_sheet_count = azoknak a sheet projection soroknak a szama, amelyeken
  tenyleges placement van`;
- `utilization_ratio` dokumentalt, determinisztikus modon szamolodjon.

Jo H1 minimum irany:
- a partszintu terulet a snapshot geometry polygon(outer-holes) alapjan
  szamolodjon;
- a sheet terulet `width_mm * height_mm`;
- a runszintu es sheetszintu utilization ezekbol legyen kepezve.

Ha ettol el kell terni, azt a reportban explicit nevezd meg es indokold.

#### 5. Az iras legyen run-szintu idempotens replace, ne append-halmaz
A normalizer retry vagy ujrafuttatas eseten ne duplazza a projection sorokat.

Minimum elvart:
- ugyanarra a runra a normalizer ujrafuttatasa ugyanarra a vegallapotra jusson;
- a meglevo `run_layout_sheets`, `run_layout_placements`, `run_layout_unplaced`,
  `run_metrics` run-szintu rekordjai kontrollaltan lecserelodjenek;
- ne maradjanak stale sorok egy korabbi reszleges normalizer futasbol;
- a write sorrend legyen olyan, hogy normalizer hiba eseten ne maradjon hamis
  `done` allapot félig feltoltott projectionnel.

Megengedett jo irany:
- explicit delete+insert / upsert run-scoped boundary,
- lehetoseg szerint egyertelmu helperrel a `WorkerSupabaseClient` oldalan.

#### 6. A worker lifecycle-be a normalizer a megfelelo helyre keruljon
A worker sorrendje H1 minimum szinten legyen kovetkezetes:
1. snapshot -> solver input mapping,
2. solver futtatas,
3. raw artifact persistence,
4. result normalizer,
5. run `done` zaras a normalizer summary alapjan.

Ezert:
- a jelenlegi `_read_run_metrics(run_dir)` fallback ne maradjon canonical truth;
- normalizer hiba eseten a run ne menjen `done` allapotba;
- retry/requeue logika maradjon ervenyes, ha a projection write hibazik.

#### 7. A task ne csusszon at viewer/export scope-ba
Ebben a taskban meg nincs:
- sheet SVG generalas,
- sheet DXF/export artifact generalas,
- bundle zip,
- nagy viewer endpoint redesign.

A `api/routes/runs.py` jelenlegi raw-outputos viewer-data aga legfeljebb
kontextus; a T1 celja a canonical projection truth letetele. A task ne nyisson
kulon frontend vagy letoltesi workflowt csak azert, mert a projection mar
elerheto.

#### 8. A smoke script bizonyitsa a fo normalizer agakat
Legyen task-specifikus smoke, amely fake snapshot + fake DB gateway mellett
legalabb ezt bizonyitja:
- a part es sheet mapping a snapshot truth-bol tortenik;
- a `run_layout_sheets` / `placements` / `unplaced` / `run_metrics` projectionek
  helyes sorokat kapnak;
- az unplaced agregacio `remaining_qty` alapon tortenik;
- a bbox/transform/metrics determinisztikus;
- ugyanazon bemenetre a normalizer ujrafuttatasa ugyanazt a vegallapotot adja;
- ismeretlen `part_id` vagy ervenytelen `sheet_index` determinisztikus hibat ad;
- a smoke nem igenyel valos solver binaryt vagy Supabase kapcsolatot.

### DoD
- [ ] Keszul explicit worker-oldali result normalizer helper/boundary.
- [ ] A normalizer a raw `solver_output.json`-t a snapshot manifest truth-tal egyutt dolgozza fel.
- [ ] A `run_layout_sheets` projection hasznalt sheetenkent feltoltodik.
- [ ] A `run_layout_placements` projection placementenkent feltoltodik platform-kompatibilis `transform_jsonb` es `bbox_jsonb` adattal.
- [ ] A `run_layout_unplaced` projection aggregalt `remaining_qty` szemantikaval feltoltodik.
- [ ] A `run_metrics` sor determinisztikusan kiszamolt counts/utilization adatokkal frissul.
- [ ] A projection write run-szintu idempotens replace viselkedest ad.
- [ ] A worker `done` zarasa mar a normalizer summary-ra epul, nem a legacy `_read_run_metrics(run_dir)` fallbackra.
- [ ] A task nem csuszik at viewer SVG/DXF/export vagy nagy runs API redesign scope-ba.
- [ ] Keszul task-specifikus smoke a sikeres es hibas normalizer agakra.
- [ ] A checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a projection mappinghez a worker ad hoc raw heuristikakat hasznal a snapshot
    truth helyett;
  - a normalizer appendeli a sorokat, es retry utan duplikalt/stale projection marad;
  - a normalizer hiba mellett a run megis `done` allapotba megy;
  - a task atcsuszik viewer/export vagy route-redesign scope-ba.
- Mitigacio:
  - explicit helper/boundary;
  - run-scoped replace write;
  - smoke-ban fedett mapping/aggregacio/idempotencia/error agak;
  - a report mondja ki vilagosan, hogy a T1 mit NEM vallal meg.
- Rollback:
  - a helper/worker/smoke/report/checklist diff egy task-commitban
    visszavonhato;
  - schema-modositas csak akkor johet, ha tenyleg elkerulhetetlen, es ezt a
    reportban ki kell mondani.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/engine_adapter_input.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
  - `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/solver_io_contract.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `worker/main.py`
- `worker/engine_adapter_input.py`
- `worker/raw_output_artifacts.py`
- `api/services/run_snapshot_builder.py`
- `api/routes/runs.py`
