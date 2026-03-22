# H2-E4-T2 Manufacturing plan builder

## Funkcio
A feladat a H2 manufacturing run-eredmeny reteg elso tenyleges implementacios lepese.
A cel, hogy egy mar lezarult nesting run projectionjabol gepfuggetlen,
persistalt manufacturing plan alljon elo, kulon truth-retegkent,
`run_manufacturing_plans` es `run_manufacturing_contours` rekordokban.

A jelenlegi repoban mar megvan:
- a manufacturing snapshot minimum (`H2-E4-T1`),
- a manufacturing_canonical derivative (`H2-E2-T1`),
- a contour classification truth (`H2-E2-T2`),
- a deterministic rule matching engine (`H2-E3-T3`),
- es a H1 run projection tabla-vilag (`run_layout_sheets`, `run_layout_placements`).

Ez a task ezekre epulve letrehozza a manufacturing plan persisted truth retegét.

Ez a task szandekosan nem preview generator, nem postprocessor adapter,
nem machine-ready export, es nem manufacturing profile resolver. A scope
kifejezetten az, hogy a run projection + manufacturing derivative + contour
classification + explicit cut rule set alapjan reprodukalhato, auditálhato,
gepfuggetlen manufacturing plan keletkezzen.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - `app.run_manufacturing_plans` es `app.run_manufacturing_contours` tablák
    bevezetese vagy a docs-proposalhoz igazitott implementacioja;
  - a manufacturing plan builder service bevezetese;
  - a builder owner-scoped run betoltesre, snapshot truth olvasasra,
    projection olvasasra, derivative/classification/matching osszefuzesre
    epuljon;
  - per-sheet manufacturing plan rekordok letrehozasa;
  - per-placement / per-contour manufacturing contour rekordok letrehozasa;
  - determinisztikus cut order es alap entry/lead meta eloallitasa;
  - task-specifikus smoke a plan-present / no-write-out-of-scope /
    idempotencia alapokra.
- Nincs benne:
  - manufacturing preview SVG;
  - postprocessor profile/version aktivacio;
  - machine-neutral vagy machine-specific export artifact;
  - live project manufacturing selection resolver;
  - cut rule set resolver a manufacturing profile-bol, ha erre nincs valos FK;
  - truth visszairasa `geometry_contour_classes` vagy mas korabbi H2 truth tablaba;
  - workerbe teljes automatikus bekotes, ha ez a task scope-jat tul szelesitené.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E4-T2 task: manufacturing plan builder.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 detailed roadmap; itt szerepel a `run_manufacturing_plans` es
    `run_manufacturing_contours`, valamint hogy a plan a run projection +
    derivative + contour class + rule set alapjan keletkezik.
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
  - kritikus boundary: a manufacturing plan kulon truth/plan reteg, nem ugyanaz,
    mint a solver projection es nem machine-ready export.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - a futas reprodukalhatosaga snapshot-first elvre epul; a buildernek nem el
    project live allapotbol dolgoznia.
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
  - a jelenlegi H1 projection truth: `run_layout_sheets`, `run_layout_placements`.
- `api/services/run_snapshot_builder.py`
  - a H2-E4-T1 snapshot manufacturing manifest source-of-truth builderje.
- `api/services/cut_rule_matching.py`
  - a jelenlegi read-only matching engine; ezt kell felhasznalni, nem ujrairni.
- `api/services/geometry_contour_classification.py`
  - a contour classification truth struktura mintaja.
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
  - a `app.geometry_contour_classes` persisted truth tablája.
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
  - a `app.cut_contour_rules` truth reteg.
- `worker/main.py`
  - a H1 projection persisted write logikaja; fontos hatar, mert a plan reteg nem
    keverheto a projection write logikaval.
- `worker/result_normalizer.py`
  - a projection placement strukturak es determinisztikus sorrend mintaja.

### Konkret elvarasok

#### 1. A builder snapshot truth-bol dolgozzon, ne live project selectionbol
A manufacturing plan builder a runhoz tartozo snapshotot tekintse forrasnak.
A H2-E4-T1 jelenlegi repoallapotban a snapshot manufacturing selectiont tartalmaz,
postprocess placeholderrel.

A builder ezert:
- a `nesting_runs` -> `nesting_run_snapshots` lancot olvassa;
- a snapshot `manufacturing_manifest_jsonb` alapjan validalja, hogy van-e
  manufacturing selection;
- nem olvas kozvetlenul `project_manufacturing_selection` live truthot;
- nem probal manufacturing resolver lenni.

#### 2. A cut rule set ne legyen rejtett resolverrel feloldva
A jelenlegi repoban nincs bizonyitott, tartosan hasznalhato FK-lanc a snapshotolt
manufacturing profile version es az aktiv `cut_rule_set_id` kozott.
Ezert ebben a taskban a builder explicit `cut_rule_set_id` inputot kapjon,
es ezt a plan truthban is orizze meg audit celra.

Ez repo-hu, mert:
- a `cut_rule_matching.py` is explicit `cut_rule_set_id`-t var;
- a task nem talalhat ki nem letezo resolver-logikat.

#### 3. A plan tabla-vilag legyen kulon, verziozhato truth-kozel reteg
A minimum elvart schema:
- `app.run_manufacturing_plans`
  - `id`
  - `run_id`
  - `sheet_id`
  - `manufacturing_profile_version_id`
  - `cut_rule_set_id`
  - `status`
  - `summary_jsonb`
  - `created_at`
  - `unique(run_id, sheet_id)`
- `app.run_manufacturing_contours`
  - `id`
  - `manufacturing_plan_id`
  - `placement_id`
  - `geometry_derivative_id`
  - `contour_class_id`
  - `matched_rule_id`
  - `contour_index`
  - `contour_kind`
  - `feature_class`
  - `entry_point_jsonb`
  - `lead_in_jsonb`
  - `lead_out_jsonb`
  - `cut_order_index`
  - `metadata_jsonb`
  - `created_at`

A fenti plusz mezok (`geometry_derivative_id`, `contour_class_id`, `matched_rule_id`)
repo-hu audit-lancot adnak a H2-E2/H2-E3 truth tablakhoz. Ne irj vissza ezekbe,
csak hivatkozz rajuk.

#### 4. A manufacturing plan builder legyen idempotens es determinisztikus
Ugyanarra a run + sheet + cut_rule_set_id bemenetre a builder ugyanazt a plan tartalmat
adja.
A persisted viselkedes legyen replace-or-rebuild jellegu:
- ugyanazon runhoz ujrageneralaskor az adott run plan reteg cserelodik / frissul;
- ne maradjanak duplikalt plan rekordok ugyanarra a `run_id + sheet_id` parra.

#### 5. A contour mapping a manufacturing derivative-re epuljon
A builder placementenkent a `part_revisions.selected_manufacturing_derivative_id`
mezot hasznalja.
Ne essen vissza a `nesting_canonical` vilagra.
Ha nincs manufacturing derivative, az legyen explicit hiba vagy skip-elt,
a reportban dokumentalhato okkal.

#### 6. A rule matching meglvo service-re epuljon
A builder a `cut_rule_matching.py` read-only engine-jet hasznalja.
Ne masoljon sajat matching logikat masik fajlba.
A matching eredmenyet a plan truthban rogzitheted, de ne modositsd vissza:
- `geometry_contour_classes`
- `cut_contour_rules`
- `project_manufacturing_selection`
- vagy mas korabbi truth tablakat.

#### 7. Az entry/lead/cut-order csak alap, gepfuggetlen meta legyen
Ebben a taskban nem gep-specifikus path generacio kell.
A minimum elvart plan-meta:
- determinisztikus `entry_point_jsonb` placement-transzformalva;
- `lead_in_jsonb` / `lead_out_jsonb` strukturalt parameter-objektum vagy minimal
  gepfuggetlen descriptor a matched rule alapjan;
- determinisztikus `cut_order_index` per sheet.

Nem scope:
- valodi machine-ready lead path,
- G-code / CNC emit,
- postprocessor-specifikus geometriak.

#### 8. A plan builder ne csusszon at preview vagy export scope-ba
A taskban ne keletkezzen:
- manufacturing preview SVG,
- `run_artifacts` export bejegyzes,
- machine-neutral export artifact,
- machine-specific program.

A truth a tablákban jojjon letre, nem artifactban.

#### 9. A smoke bizonyitsa a fo H2-E4-T2 invariansokat
A task-specifikus smoke legalabb ezt bizonyitsa:
- egy valid run projectionbol per-sheet manufacturing plan letrejon;
- contour rekordok letrejonnek es matched rule-ra hivatkoznak;
- a builder explicit `cut_rule_set_id`-t var, nem resolver;
- a builder nem ir vissza korabbi truth tablaba;
- ujrageneralas nem hoz letre duplikalt per-sheet plan rekordokat;
- a `cut_order_index` determinisztikus;
- a task nem hoz letre preview/export artifactot.

### DoD
- [ ] Letezik `app.run_manufacturing_plans` es `app.run_manufacturing_contours` persisted truth reteg.
- [ ] A builder a run snapshot + run projection + manufacturing derivative + contour classification + explicit cut rule set alapjan plan-t tud epiteni.
- [ ] A builder nem live project manufacturing selectionbol dolgozik.
- [ ] A builder nem talal ki cut rule set resolver logikat.
- [ ] A contour rekordok matched rule hivatkozast es alap entry/lead/cut-order infot tartalmaznak.
- [ ] A builder idempotens a persisted reteg szintjen.
- [ ] A task nem ir vissza korabbi truth tablaba.
- [ ] A task nem nyit preview / postprocessor / export scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a builder live project state-bol kezd dolgozni snapshot helyett;
  - nem letezo rule-set resolver logikat talal ki;
  - a plan reteg preview/export iranyba kezd csuszni;
  - a persisted plan reteg nem idempotens;
  - a builder visszair classification vagy rule truth tablaba.
- Mitigacio:
  - explicit snapshot-first + explicit cut_rule_set_id input;
  - existing `cut_rule_matching.py` ujrahasznositasa;
  - artifact/write tiltas a `run_artifacts` iranyba;
  - task-specifikus smoke idempotencia es no-write bizonyitassal.
- Rollback:
  - migration + builder service + smoke valtozasok egy task-commitban
    visszavonhatok;
  - a H2-E4-T1 snapshot reteg valtozatlanul megmarad, ha a plan builder
    iranyat ujra kell gondolni.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/manufacturing_plan_builder.py scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`
  - `python3 scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_modulhatarok_es_boundary_szerzodes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- `supabase/migrations/20260322004000_h2_e2_t2_contour_classification_service.sql`
- `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
- `api/services/run_snapshot_builder.py`
- `api/services/cut_rule_matching.py`
- `api/services/geometry_contour_classification.py`
- `worker/main.py`
- `worker/result_normalizer.py`
