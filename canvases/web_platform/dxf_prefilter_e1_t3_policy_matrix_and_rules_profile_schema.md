# DXF Prefilter E1-T3 Policy matrix es rules profile schema

## Funkcio
Ez a task a DXF prefilter lane harmadik, **docs-only szabalyfagyaszto** lepese.
A cel most nem backend implementacio, nem migration, nem route es nem UI form kod,
hanem annak rogzitese, hogy a jovobeli DXF prefilter V1 milyen **policy matrix**
es milyen **rules profile schema** alapjan fog mukodni.

A task kozvetlenul az E1-T1 es E1-T2 utan jon:
- a T1 rogzitette a V1 scope es boundary keretet;
- a T2 lefagyasztotta a fogalmi szinteket es a canonical role-vilagot;
- ez a T3 ezekre epitve rogziti a konfiguracios szerzodest.

A tasknak a jelenlegi repora kell raulnie:
- a low-level importer ma hardcoded `CUT_OUTER` / `CUT_INNER` layer-konvenciot hasznal;
- a file upload route ma `stock_dxf` / `part_dxf` legacy inputot `source_dxf`-re normalizal;
- a ProjectDetailPage ma uploadot kezel, de nincs kulon preflight settings vagy diagnostics panel;
- a repo mas domainjeiben mar letezik verziozott profile/schema minta (cut rule set, run strategy profile, scoring profile), de prefilter rules profile domain meg nincs.

Ez a task azert kell, hogy a kesobbi state machine, data model, API contract es UI settings
ne ad hoc mezokkel, hanem ugyanarra a szabaly-szerzodesre epuljenek.

## Scope
- Benne van:
  - a DXF prefilter V1 policy dimenzioinak rogzitese;
  - a rules profile schema V1 dokumentacios definicioja;
  - current-code truth vs future canonical contract szetvalasztasa;
  - a default / override / review-required policy viselkedes leirasa;
  - a minimum user-beallitasok es a javasolt future profile mezok szetvalasztasa;
  - egy dedikalt architecture dokumentum letrehozasa a policy matrixrol es a rules profile schemarol.
- Nincs benne:
  - SQL migration;
  - uj `rules_profiles` tabla vagy version tabla implementacio;
  - FastAPI route vagy service implementacio;
  - frontend settings panel implementacio;
  - inspect/repair algoritmus kod;
  - review modal implementacio;
  - importer hardcoded layer-konvencio atirasa;
  - geometry import pipeline tenyleges preflight gate atkotese.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `vrs_nesting/dxf/importer.py`
  - current-code truth: strict `OUTER_LAYER_DEFAULT = "CUT_OUTER"`, `INNER_LAYER_DEFAULT = "CUT_INNER"`;
  - tamogatott entity tipusok es determinisztikus fail-fast hibavilag;
  - bizonyitja, hogy a V1 profile nem irhat elo olyan canonical role-t, amit az acceptance gate nem tud visszatesztelni.
- `api/routes/files.py`
  - current-code truth: `stock_dxf` / `part_dxf` legacy upload kind normalizalasa `source_dxf`-re;
  - current upload vilagban nincs preflight-specific beallitas vagy rules-profile ref.
- `api/config.py`
  - current-code minta egyszeru, validalt numeric/string konfiguracios mezokre (`API_MAX_DXF_SIZE_MB`, rate limit, signed url ttl);
  - hasznos referencia arra, hogy a future profile mezok nevei es tipusai legyenek egyszeruek es validalhatok.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - current UI upload kind vilag: `stock_dxf` / `part_dxf`;
  - nincs benne `max_gap_close_mm`, color mapping, strict mode vagy diagnostics state.
- `frontend/src/pages/NewRunPage.tsx`
  - current legacy wizard szemlelet, nem megfelelo source-of-truth a prefilter policy schemahoz;
  - fontos rogzitendo anti-pattern, hogy a rules profile ne ide legyen betakolva.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - T1 output; rogziti a V1 fail-fast acceptance gate keretet.
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
  - T2 output; rogziti a canonical role-vilagot es a tiltott fogalmi osszemosasokat.
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
  - meglevo repo-minta owner-scoped, verziozhato rules domainhez.
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
  - meglevo repo-minta profile + version truth retegre.
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
  - meglevo repo-minta versioned config-profile szerzodesre.

## Jelenlegi repo-grounded helyzetkep
A repoban ma nincs DXF prefilter policy matrix es nincs rules profile schema.
A jelenlegi truth-kep:
- importer hardcoded layer-konvencio;
- upload route legacy file-kind normalizalas;
- UI-ban nincs preflight settings fogalom;
- nincs per-project vagy per-owner prefilter config domain.

Ezert a T3-ban nem szabad ugy tenni, mintha a repo mar tartalmazna `rules_profile_id`,
`preflight_settings_jsonb` vagy hasonlo mezo(ke)t.
A helyes output most egy **architecture-level schema freeze**, amelyre a kesobbi
E1-T4/E1-T5/E1-T6 taskok ra tudnak ulni.

## Konkret elvarasok

### 1. A policy matrix role-first legyen, ne szin-first
A dokumentumnak rogzitnie kell, hogy a policy matrix alapegysege nem a nyers szin,
hanem a canonical role:
- `CUT_OUTER`
- `CUT_INNER`
- `MARKING`
- opcionálisan kesobbi `IGNORE`

A szin csak input-hint policy mezo lehet.
Ez a T2 glossary szerzodesbol kovetkezik, es illeszkedik a jelenlegi importer truth-hoz.

### 2. A rules profile schema kulonitse el a V1 minimumot es a kesobbi boviteseket
A dokumentumban kulon szerepeljen:
- **V1 minimum profile mezok**:
  - `profile_code`
  - `display_name`
  - `description`
  - `strict_mode`
  - `auto_repair_enabled`
  - `interactive_review_on_ambiguity`
  - `max_gap_close_mm`
  - `duplicate_contour_merge_tolerance_mm`
  - `cut_color_map`
  - `marking_color_map`
  - `canonical_layer_colors`
  - `metadata_jsonb`
- **kesobbi / V1.1+ jeloltek**:
  - `ignore_color_map`
  - linetype-hint policy
  - text/bend/guide feature role-ok
  - entity-type specific policy

Rogzitve legyen, hogy a `IGNORE` es egyeb non-cut role-ok nem current-code truth,
hanem future schema extension lehetosegek.

### 3. A mezok tipusa legyen egyszeru es repo-kompatibilis
A schema ne talaljon ki bonyolult vagy nem bizonyithato formakat.
A dokumentumnak rogzitenie kell, hogy a future schema preferaltan egyszeru,
JSON-serializable tipusokat hasznaljon:
- bool
- positive numeric mm ertek
- string list / code list
- simple mapping (`color -> role intent`)
- metadata json

A schema ne vallaljon olyan shape-et, amelyhez jelenleg nincs UI vagy backend precedent.

### 4. Kulon legyen a policy matrix es a rules profile schema
A dokumentumnak ki kell mondania, hogy:
- a **policy matrix** az uzleti/validacios dontesi szabalyok tablazatos leirasa;
- a **rules profile schema** a tarolhato konfiguracios objektum szerzodese.

Ez azert fontos, mert a kovetkezo taskok kozul:
- a state machine a policy matrixra fog ulni;
- a data model es API contract a rules profile schema-ra fog ulni.

### 5. Rogzitve legyen a default / override / review-required modell
A dokumentumban kulon szerepeljen:
- default profile policy viselkedes;
- project/file-level temporary override helye mint future integration igeny;
- mely esetek mennek auto-fix / auto-reject / review-required iranyba.

A task ne implementalja ezt, csak rogzitse a matrix nyelven.

### 6. A dokumentum kapcsolodjon a repo mar meglevo profile mintaihoz, de ne implementalja oket
A dokumentumban kulon legyen kimondva, hogy a future DXF rules profile domain
szerkezetileg kovetheti a repo mar meglevo profile/version mintait (`cut_rule_sets`,
`run_strategy_profiles`, `scoring_profiles`), de ebben a taskban nincs migration vagy CRUD.

### 7. Legyen explicit anti-scope lista
A dokumentum kulon nevezze meg, hogy ebben a taskban nem szabad:
- DB schema mezoneveket vegleges SQL truth-kent bevezetni migration nelkul;
- preflight state machine-t implementacios reszletesseggel lefagyasztani;
- API endpoint payloadot veglegesiteni;
- UI form-komponens strukturaig lemenni.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema/run.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `codex/codex_checklist/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.md`
- `codex/reports/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.md`

## DoD
- [ ] Letrejon a `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md` dokumentum.
- [ ] A dokumentum explicit kulonvalasztja a policy matrix es a rules profile schema szerepet.
- [ ] Rogziti a V1 minimum rules profile mezoket.
- [ ] Rogziti, hogy a szin input-hint, a canonical role a source-of-truth.
- [ ] Rogziti a default / override / review-required alapmodellt.
- [ ] Kulon jeloli a current-code truth, a future canonical contract es a later extension reszeket.
- [ ] Repo-grounded hivatkozasokat ad az importerre, upload route-ra, UI upload entrypointokra es a meglevo profile/version mintakra.
- [ ] Nem vezet be sem SQL migrationt, sem route/service implementaciot.
- [ ] A YAML outputs listaja csak valos, szukseges fajlokat tartalmaz.
- [ ] A runner prompt egyertelmuen tiltja a schema-implementacios scope creep-et.

## Kockazat + mitigacio + rollback
- Kockazat:
  - a task osszecsuszna a data model vagy API contract taskkal;
  - a schema tul implementacio-kozeli lenne jelenlegi kodfedezet nelkul;
  - a szin/layer policy uj fogalmi zavarokat hozna be a T2 utan.
- Mitigacio:
  - kulon current-code truth / future canonical contract / later extension szekcio;
  - docs-only scope;
  - kotelezo hivatkozas az importer, files route, ProjectDetailPage es a meglevo profile/version mintak fele.
- Rollback:
  - docs-only task; a letrehozott dokumentumok egy commitban visszavonhatok.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t3_policy_matrix_and_rules_profile_schema.md`
- Feladat-specifikus:
  - nincs uj kod-smoke; ez docs-only policy/schema freeze task.

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `vrs_nesting/dxf/importer.py`
- `api/routes/files.py`
- `api/config.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324110000_h3_e1_t2_scoring_profile_modellek.sql`
