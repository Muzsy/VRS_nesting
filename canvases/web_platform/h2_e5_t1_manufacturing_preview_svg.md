# H2-E5-T1 Manufacturing preview SVG

## Funkcio
A feladat a H2 manufacturing truth lanc kovetkezo, a persisted plan retegbol
kozvetlenul kovetkezo lepese.
A cel, hogy a mar meglevo `run_manufacturing_plans` +
`run_manufacturing_contours` truth-bol per-sheet, gepfuggetlen,
visszanezheto `manufacturing_preview_svg` artifactok generalodjanak.

A jelenlegi repoban mar megvan:
- a manufacturing snapshot minimum (`H2-E4-T1`),
- a persisted manufacturing plan truth (`H2-E4-T2`),
- a persisted manufacturing metrics truth (`H2-E4-T3`),
- a H1 `run_artifacts` artifact-reteg es a deterministic SVG storage minta,
- a `manufacturing_canonical` derivative, amely a previewhoz szukseges
  contour-geometriat hordozza.

Ez a task ezekre epulve gyartasi review celu SVG preview artifactokat vezet be.

Ez a task szandekosan nem postprocessor adapter, nem machine-neutral exporter,
nem worker full auto-integracio, nem frontend redesign, es nem vegleges operatori
UI. A scope kifejezetten az, hogy a persisted manufacturing plan truth alapjan
reprodukalhato, auditalhato, gepfuggetlen preview artifact jojjon letre.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.artifact_kind` bovitese `manufacturing_preview_svg` ertekkel;
  - a legacy bridge fuggvenyek frissitese, hogy a generic artifact-lista es
    signed URL flow ezt az artifact tipust is konzisztensen vigye;
  - dedikalt preview generator service bevezetese;
  - owner-scoped run betoltes, persisted manufacturing plan es contour truth
    olvasasa;
  - a `run_manufacturing_contours.geometry_derivative_id` referencia menten a
    `manufacturing_canonical` derivative contour geometriak beolvasasa;
  - per-sheet SVG preview generalasa:
    - contour path render,
    - entry marker,
    - lead-in / lead-out jeloles,
    - alap cut-order jeloles vagy metadata-kompatibilis jeloles;
  - artifact upload + `app.run_artifacts` regisztracio `manufacturing_preview_svg`
    tipussal;
  - task-specifikus smoke a deterministic render / no-write-out-of-scope /
    idempotens replace invariansokra.
- Nincs benne:
  - postprocessor profile/version aktivacio;
  - machine-neutral export artifact;
  - machine-specific program vagy gepfuggo emit;
  - H1 `sheet_svg` viewer artifact ujratervezese;
  - `api/routes/runs.py` nagy redesignja vagy uj dedikalt preview endpoint;
  - worker automatikus bekotes, ha ez a task scope-jat tul szelesitene.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E5-T1 task: manufacturing preview SVG.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - preview generator cel, artifact tipusbovites es scope-hatarok.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a manufacturing plan truth kulon marad a postprocess
    modultol; a preview review artefakt, nem machine-ready output.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - artifact vs source-of-truth szemlelet: az SVG derived artifact, nem truth.
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
  - a canonical run artifact bucket a `run-artifacts`.
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
  - a jelenlegi `app.artifact_kind` enum alapja.
- `supabase/migrations/20260318103000_h1_e3_t3_security_and_schema_bridge_fixes.sql`
  - a `legacy_artifact_type_to_kind` / `artifact_kind_to_legacy_type` bridge-ek.
- `api/services/manufacturing_plan_builder.py`
  - a preview forras truth-ja: `run_manufacturing_plans` es
    `run_manufacturing_contours`.
- `api/services/manufacturing_metrics_calculator.py`
  - minta a H2 truth-retegre epulo, kulon service boundaryra.
- `api/services/geometry_derivative_generator.py`
  - a `manufacturing_canonical` payload contour szerkezete.
- `worker/sheet_svg_artifacts.py`
  - minta deterministic SVG renderhez, hash-alapu storage pathhoz es artifact
    metadata policyhoz.
- `api/routes/runs.py`
  - a generic artifact-lista es signed URL eleres jelenlegi szerzodese.

### Konkret elvarasok

#### 1. A preview generator persisted manufacturing truth-bol dolgozzon
A preview generator kizarlag a mar persisted H2 truth retekre epuljon:
- `run_manufacturing_plans`
- `run_manufacturing_contours`
- `run_layout_sheets` a sheet meretekhez
- `geometry_derivatives` a `manufacturing_canonical` contour pontokhoz

A generator ne olvasson:
- raw solver outputot;
- live project manufacturing selectiont;
- postprocessor configot;
- H1 `sheet_svg` artifactot mint forrast.

#### 2. Uj artifact kind kell, bridge-frissitessel egyutt
A task vezesse be a `manufacturing_preview_svg` artifact tipust.

Ez repo-hu, mert a `run_artifacts.artifact_kind` enumos, es a jelenlegi
insert/list bridge a legacy type <-> enum lekepzest fugvenyekkel kezeli.

Minimum elvaras:
- migration, amely hozzaadja az enum erteket;
- migration vagy ugyanabban a taskban kezelt patch, amely a bridge
  fuggvenyeket is frissiti a `manufacturing_preview_svg` legacy type-ra.

#### 3. A render tartalmazzon manufacturing-meta informaciot, ne csak layoutot
A preview ne ugyanaz legyen, mint a H1 `sheet_svg`.

Minimum elvart sheet-szintu tartalom:
- sheet boundary/background;
- contour pathok a `manufacturing_canonical` contour pontokbol;
- kulon megkulonboztetes outer/inner contourra;
- entry marker az `entry_point_jsonb` alapjan;
- lead-in / lead-out jeloles a persisted lead descriptor alapjan;
- determinisztikus cut-order jeloles vagy legalabb egyertelmu metadata-alapu
  label, hogy a gyartasi sorrend reviewzhato legyen.

Nem cel most:
- valodi toolpath gepgeometria;
- kerf-kompenzalt machine path;
- G-code jellegu emit.

#### 4. A preview artifact persistence legyen canonical es idempotens
A generalt SVG artifactok `app.run_artifacts` ala keruljenek.

Minimum elvart:
- bucket: `run-artifacts`;
- artifact kind / legacy type: `manufacturing_preview_svg`;
- filename legyen stabil es egyertelmu, peldaul
  `out/manufacturing_preview_sheet_001.svg`;
- metadata legyen legalabb:
  - `filename`
  - `sheet_index`
  - `size_bytes`
  - `content_sha256`
  - `legacy_artifact_type='manufacturing_preview_svg'`
  - opcionisan `preview_scope='h2_e5_t1'`
- storage path legyen hash-alapu es canonical, peldaul
  `projects/{project_id}/runs/{run_id}/manufacturing_preview_svg/{digest}.svg`.

Ugyanarra a run + sheet bemenetre ujrageneralaskor ne maradjon duplikalt preview
artifact ugyanarra a logical targetre.

#### 5. A generator maradjon kulon preview service, ne postprocess adapter
Ez a task meg review preview.

Ne vallalja:
- postprocessor profilt aktivalo logika;
- machine-neutral export artifactot;
- machine-specific adaptert;
- `run_manufacturing_plans` vagy `run_manufacturing_contours` visszairasat.

A generator legfeljebb `app.run_artifacts`-ba irhat.

#### 6. A task ne igenyeljen uj viewer-data szerzodest
A jelenlegi repoban mar van generic artifact lista + signed URL eleres.
Ezert ebben a taskban ne legyen kotelezo:
- `viewer-data` route attervezese;
- uj frontend oldal;
- preview-specifikus API response model.

A task outputja mar legyen reviewzhato a meglevo artifact endpointokon
keresztul.

#### 7. A smoke bizonyitsa a fo H2-E5-T1 invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- valid persisted manufacturing planbol per-sheet preview artifact letrejon;
- a preview SVG tenylegesen gyartasi meta-informaciot hordoz (entry/lead/cut order);
- a render a `manufacturing_canonical` contour geometriara ul;
- outer/inner contour vizualis megkulonboztetes jelen van;
- idempotens rerun ugyanarra a sheetre nem hagy duplikalt artifactot;
- a generator nem ir vissza `run_manufacturing_plans`,
  `run_manufacturing_contours`, `run_manufacturing_metrics` vagy mas korabbi
  truth tablaba;
- a task nem hoz letre export/postprocess artifactot;
- hiba jon, ha hianyzik a `manufacturing_canonical` derivative vagy ervenytelen
  a contour -> derivative hivatkozas.

### DoD
- [ ] Letezik `manufacturing_preview_svg` artifact kind a canonical artifact vilagban.
- [ ] A bridge fuggvenyek kezelik a `manufacturing_preview_svg` legacy type-ot.
- [ ] Keszul dedikalt manufacturing preview generator service.
- [ ] A generator persisted manufacturing plan truth + manufacturing_canonical
      derivative alapjan per-sheet preview SVG-t general.
- [ ] A preview a gyartasi meta-informaciot is hordozza (entry/lead/cut-order),
      nem csak layoutot.
- [ ] A preview artifactok a canonical `run-artifacts` bucketbe kerulnek.
- [ ] A filename + metadata policy stabil, auditalhato es generic artifact
      endpointtel hasznalhato.
- [ ] A preview artifact persistence idempotens ugyanarra a run + sheet targetre.
- [ ] A task nem ir vissza korabbi truth tablaba.
- [ ] A task nem nyit export / postprocessor / frontend-redesign scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a preview a H1 `sheet_svg` ujracsomagolasa lesz H2 manufacturing meta nelkul;
  - a generator live state-ra vagy raw solver outputra kezd epulni persisted
    manufacturing truth helyett;
  - az artifact kind bevezetese felig tortenik meg, es a bridge fuggvenyek nem
    kezelik konzisztensen;
  - a task export/postprocess iranyba csuszik;
  - a preview persistence nem idempotens.
- Mitigacio:
  - explicit truth-forras lista;
  - explicit no-worker-auto / no-route-redesign / no-postprocess boundary;
  - task-specifikus smoke a render, metadata, idempotencia es no-write
    invariansokra;
  - deterministic filename + storage path policy.
- Rollback:
  - migration + preview generator service + smoke valtozasok egy task-commitban
    visszavonhatok;
  - a H2-E4 truth reteg erintetlen marad, mert a task csak derived artifactot
    allit elo.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/manufacturing_preview_generator.py scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py`
  - `python3 scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `supabase/migrations/20260318103000_h1_e3_t3_security_and_schema_bridge_fixes.sql`
- `api/services/manufacturing_plan_builder.py`
- `api/services/manufacturing_metrics_calculator.py`
- `api/services/geometry_derivative_generator.py`
- `worker/sheet_svg_artifacts.py`
- `api/routes/runs.py`
