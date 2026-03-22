# H2-E4-T1 Snapshot manufacturing bovites

## Funkcio
A feladat a H2 manufacturing snapshot reteg elso lepese.
A cel, hogy a `nesting_run_snapshots` mar ne H1 placeholder manufacturing manifestet
mentsen, hanem a projekt aktualis manufacturing kivalasztasat kontrollalt,
determinisztikus formaban snapshotolja a run indulasanak pillanataban.

A jelenlegi repoban a `run_snapshot_builder.py` a `manufacturing_manifest_jsonb`
mezobe csak ezt a placeholdert irja:
`{"mode": "not_in_scope_h1_e4_t1"}`.
Ez a H2-E1 manufacturing selection es a H2-E3 cut-rule reteg utan mar keves.
A task ezt valodi, de meg mindig szuk snapshot-adatta alakitsa.

Ez a task szandekosan nem manufacturing resolver, nem manufacturing plan builder,
nem rule matching persistencia, nem postprocessor domain aktivacio, es nem export.
A scope kifejezetten az, hogy a manufacturing selection run-snapshot truthkent
rogzuljon, mikozben a postprocess vilag explicit placeholder maradjon.

## Fejlesztesi reszletek

### Scope
- Benne van:
  - a `app.nesting_run_snapshots` schema minimalis H2 bovitese;
  - `includes_manufacturing` es `includes_postprocess` meta bevezetese;
  - a `run_snapshot_builder.py` frissitese ugy, hogy a project-level
    manufacturing selectiont beolvassa es snapshotolja;
  - a manufacturing manifest determinisztikus strukturara hozasa;
  - a `run_creation.py` snapshot fetch/return retegenek hozzaigazitasa,
    ha az uj schema ezt igenyli;
  - task-specifikus smoke a selection-present es selection-absent agakra.
- Nincs benne:
  - manufacturing profile resolver;
  - cut rule set feloldas manufacturing profile alapjan, ha arra nincs valos FK;
  - contour class, rule matching vagy manufacturing plan builder;
  - `run_manufacturing_plans` / `run_manufacturing_contours` irasa;
  - postprocessor profile/version domain aktivacio;
  - preview vagy export.

### Talalt relevans fajlok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
  - itt van a H2-E4-T1 task: snapshot manufacturing bovites.
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
  - a H2 detailed roadmap; itt szerepel, hogy a snapshot mar tartalmazza a
    manufacturing es postprocess kivalasztast, es `includes_manufacturing` /
    `includes_postprocess` meta is varhato.
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
  - kritikus boundary: a run snapshot append-only truth, futas kozben nem modosithato.
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
  - a jelenlegi `app.nesting_run_snapshots` schema; itt mar letezik a
    `manufacturing_manifest_jsonb`, de H2 meta meg nincs.
- `api/services/run_snapshot_builder.py`
  - a jelenlegi builder; itt a manufacturing manifest meg H1 placeholder.
- `api/services/run_creation.py`
  - a snapshot insert/fetch retege; ezt a schema boviteshez kell igazítani.
- `api/services/project_manufacturing_selection.py`
  - a projekt manufacturing selection truth beolvasasanak mintaja.
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
  - a manufacturing profile version + project manufacturing selection jelenlegi truthja.
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
  - fontos korlat: a cut rule set domain letezik, de a manufacturing profile
    verziohoz kotott explicit FK-lanc jelenleg nincs.

### Konkret elvarasok

#### 1. A snapshot manufacturing bovites a project selectionre epuljon, ne resolverre
A builder explicit a `project_manufacturing_selection` truthot olvassa a projektre.
Ne probaljon manufacturing resolver lenni, es ne talaljon ki olyan szabaly-set vagy
postprocessor feloldast, amihez meg nincs valos schema-lanc.

#### 2. A manufacturing manifest determinisztikus, olvashato snapshot legyen
Ha van projekt manufacturing selection, a `manufacturing_manifest_jsonb` minimum
legalabb ezeket tartalmazza determinisztikus kulcssorrenddel/strukturan belul:
- `mode`: `h2_e4_t1_snapshot_selection`
- `project_id`
- `selection_present`
- `selected_at`
- `selected_by`
- `active_manufacturing_profile_version_id`
- `manufacturing_profile_version`:
  - `manufacturing_profile_id`
  - `version_no`
  - `lifecycle`
  - `is_active`
  - `machine_code`
  - `material_code`
  - `thickness_mm`
  - `kerf_mm`
  - `config_jsonb`

Ha nincs selection, a manifest legyen szinten determinisztikus, de expliciten
jelezo placeholder, ne a regi H1 `not_in_scope` uzenet.

#### 3. A snapshot meta kulon jelezze a manufacturing es postprocess allapotot
A task vezesse be:
- `includes_manufacturing boolean`
- `includes_postprocess boolean`

Elvart viselkedes:
- manufacturing selection jelenlete eseten `includes_manufacturing=true`;
- selection hianya eseten `includes_manufacturing=false`;
- mivel a postprocessor domain jelenleg nincs tenylegesen implementalva,
  `includes_postprocess=false` marad.

#### 4. A task ne kapcsoljon be postprocessor domaint idovel elott
A postprocess vilag ebben a taskban csak explicit placeholder lehet.
A manufacturing manifestben megjelenhet peldaul:
- `postprocess_selection_present: false`
- vagy egy hasonloan tiszta, determinisztikus, null/false alapu jelzes.

De ne vezess be:
- `postprocessor_profiles`
- `postprocessor_profile_versions`
- active postprocessor resolver logikat.

#### 5. A snapshot hash valtozzon, ha a manufacturing selection valtozik
Mivel a manufacturing selection a snapshot truth resze lesz, a builder hash-payloadja
is tartalmazza az uj manufacturing manifestet.
Ez azt jelenti, hogy ugyanazon projekt/part/sheet/technology input mellett ket kulonbozo
manufacturing selection kulonbozo `snapshot_hash_sha256`-t eredmenyezzen.

#### 6. A H1 kompatibilitas ne torjon el
A task ne tegye kotelezove a manufacturing selectiont minden runhoz.
Ha nincs selection:
- a run snapshot tovabbra is felepulhet;
- a manufacturing manifest explicit `selection_present=false` allapotot mentsen;
- a builder ne dobjon hibat pusztan a selection hianya miatt.

#### 7. A smoke bizonyitsa a fo agakot
A task-specifikus smoke legalabb ezt bizonyitsa:
- selection nelkul a snapshot felepul, `includes_manufacturing=false`;
- selectionnel a snapshot manufacturing manifest tenylegesen tartalmazza a valasztott versiont;
- `includes_postprocess=false` marad;
- selection valtozas snapshot hash valtozast okoz;
- a task nem kezd el rule matchinget vagy manufacturing plan recordokat gyartani.

### DoD
- [ ] A `app.nesting_run_snapshots` schema megkapja a H2 snapshot manufacturing minimum meta mezoket.
- [ ] A `run_snapshot_builder.py` nem H1 placeholder manifestet ad vissza, hanem valos manufacturing snapshotot.
- [ ] Project manufacturing selection eseten a manufacturing profile version snapshotolodik.
- [ ] Selection hianya eseten a builder tovabbra is mukodik, tiszta placeholder allapottal.
- [ ] `includes_manufacturing` korrektul jelzi a selection jelenletet.
- [ ] `includes_postprocess` explicit false marad a jelenlegi repoallapotban.
- [ ] A snapshot hash valtozik, ha a manufacturing selection valtozik.
- [ ] A task nem nyitja ki a resolver / plan builder / postprocessor domain scope-ot.
- [ ] Keszul task-specifikus smoke script.
- [ ] Checklist es report evidence-alapon ki van toltve.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t1_snapshot_manufacturing_bovites.md` PASS.

### Kockazat + rollback
- Kockazat:
  - a task manufacturing resolverre kezd hasonlitani;
  - nem letezo postprocessor domainre kezd hivatkozni;
  - kotelezove teszi a manufacturing selectiont es regressziot okoz a H1 run flowban;
  - a snapshot hash nem veszi figyelembe a selection valtozasat.
- Mitigacio:
  - explicit no-resolver, no-plan-builder, no-postprocessor scope;
  - selection-hiany kompatibilitas megtartasa;
  - task-specifikus smoke hash-eltteresi es placeholder aggal;
  - csak valos schema mezok snapshotolasa.
- Rollback:
  - migration + snapshot builder + smoke valtozasok egy task-commitban
    visszavonhatok;
  - a H1 placeholder manifest visszaallithato, ha a H2 snapshot struktura rossznak bizonyul.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t1_snapshot_manufacturing_bovites.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/run_snapshot_builder.py api/services/run_creation.py scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py`
  - `python3 scripts/smoke_h2_e4_t1_snapshot_manufacturing_bovites.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/roadmap/dxf_nesting_platform_implementacios_backlog_task_tree.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h2_reszletes.md`
- `docs/web_platform/architecture/h0_snapshot_first_futasi_es_adatkontraktus.md`
- `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
- `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- `api/services/run_snapshot_builder.py`
- `api/services/run_creation.py`
- `api/services/project_manufacturing_selection.py`
