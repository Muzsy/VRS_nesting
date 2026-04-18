# DXF Prefilter Policy Matrix and Rules Profile Schema (E1-T3)

## 1. Cel
Ez a dokumentum docs-only modban lefagyasztja a DXF prefilter V1 policy matrix
es rules profile schema szerzodeset. A cel az, hogy a kovetkezo taskok
(state machine, data model, API contract, UI settings) ugyanarra a fogalmi es
konfiguracios alapra epuljenek.

## 2. Scope boundary
- Ez architecture-level policy/schema freeze.
- Nem implementacio, nem migration, nem route/service/UI kodvaltoztatas.
- Nem vegleges state machine vagy API payload specifikacio.

## 3. Repo-grounded baseline (current-code truth)

### 3.1 Importer truth
- A low-level importer jelenleg strict layer-konvenciot hasznal:
  - `CUT_OUTER`
  - `CUT_INNER`
- Az importer determinisztikus hibavilaggal fail-fast viselkedik.

### 3.2 Upload route truth
- A file route legacy frontend `stock_dxf` / `part_dxf` inputot `source_dxf`-re
  normalizal.
- Jelenleg nincs prefilter-specific settings vagy rules profile hivatkozas az
  upload metadata flowban.

### 3.3 Config truth
- A backend config mintaja egyszeru, validalt primitive mezokkel dolgozik
  (pozitiv integer, bool, string/tuple).
- A future rules profile schema tipusrendszerehez ez a minta kovetendo:
  egyszeru, validalhato, JSON-serializable alakok.

### 3.4 Frontend truth
- A `ProjectDetailPage.tsx` upload oldalon legacy upload kind valaszto van
  (`stock_dxf` / `part_dxf`), de nincs prefilter policy panel.
- A `NewRunPage.tsx` legacy run wizard, nem prefilter policy source-of-truth.

### 3.5 Existing profile/version domain mintak
- A repoban letezik owner-scoped, verziozott profile/version minta:
  - `cut_rule_sets`
  - `run_strategy_profiles` + `run_strategy_profile_versions`
  - `scoring_profiles` + `scoring_profile_versions`
- DXF prefilter rules profile domain jelenleg nincs implementalva.

## 4. Policy matrix es rules profile schema kulon szerepe

### 4.1 Policy matrix
A policy matrix a dontesi szabalyok tablazatos leirasa:
- milyen signal milyen canonical role iranyba mutat;
- mely eset auto-fix, auto-reject vagy review-required;
- hogyan hat a `strict_mode`.

A policy matrix a viselkedest irja le, nem tarolasi formatumot.

### 4.2 Rules profile schema
A rules profile schema a tarolhato konfiguracios objektum szerzodese:
- mely mezoket tarolunk;
- milyen tipussal;
- milyen validacios korlatokkal.

A rules profile schema a konfiguracio formatumat irja le, nem endpointot,
nem SQL truthot, nem UI komponens strukturat.

## 5. Role-first policy elv
- A canonical role a source-of-truth.
- A szin csak input-hint policy mezo.
- A V1 canonical role-vilag a T2 glossary szerint:
  - `CUT_OUTER`
  - `CUT_INNER`
  - `MARKING`

Kovetkezmeny:
- nem szin-first osztalyozas;
- a mapping mindig role-celra tortenik;
- a color policy csak segedinformacio.

## 6. Rules profile schema V1 minimum contract (docs freeze)

| Mezo | Javasolt tipus (docs-level) | V1 statusz | Megjegyzes |
| --- | --- | --- | --- |
| `profile_code` | non-empty string | V1 minimum | stabil kod, owner-szintu egyediseg celjaval |
| `display_name` | non-empty string | V1 minimum | user-facing nev |
| `description` | string vagy null | V1 minimum | opcionais leiras |
| `strict_mode` | bool | V1 minimum | szigoru gate policy kapcsolo |
| `auto_repair_enabled` | bool | V1 minimum | engedett egyertelmu auto-fix policy |
| `interactive_review_on_ambiguity` | bool | V1 minimum | ketertelmu eset review-required flag |
| `max_gap_close_mm` | positive numeric | V1 minimum | kiskoz zarasi kuszob |
| `duplicate_contour_merge_tolerance_mm` | positive numeric | V1 minimum | duplikalt kontur merge tolerance |
| `cut_color_map` | simple mapping/list | V1 minimum | color-hint mapping cut role-okhoz |
| `marking_color_map` | simple mapping/list | V1 minimum | color-hint mapping marking role-hoz |
| `canonical_layer_colors` | simple mapping | V1 minimum | role/layer canonical szinpreferencia |
| `metadata_jsonb` | json object | V1 minimum | extra, nem-kritikus metadata |

Tipuselv:
- bool
- pozitiv numeric mm
- string/code lista
- egyszeru mapping
- metadata json

Ez a task nem fagyaszt le konkret SQL oszlopnevet, migration DDL-t vagy API
payload shape-et.

## 7. Default / override / review-required alapmodell

### 7.1 Default
- Egy aktiv default rules profile adja a policy matrix kiindulasi viselkedest.
- Default viselkedes docs-levelen role-first.

### 7.2 Override (future integration place)
- Project/file-level temporary override lehetoseg future integracios igeny.
- Ebben a taskban csak fogalmi helye van, nem implementacios kotese.

### 7.3 Review-required
- Ambiguous vagy policy-konfliktusos eset review-required allapotba megy.
- `interactive_review_on_ambiguity` meghatarozza, hogy ez kotelezoen UI review
  lepest igenyel-e.
- Ebben a taskban nem keszul state machine implementacio.

## 8. Current-code vs future canonical vs later extension

### 8.1 Current-code truth
- importer: `CUT_OUTER` / `CUT_INNER` layer truth.
- upload route: legacy kind normalizalas `source_dxf`-re.
- frontend: legacy upload terminology, prefilter settings panel nelkul.

### 8.2 Future canonical contract (V1)
- policy matrix + rules profile schema kulon szintu szerzodes.
- role-first policy nyelv.
- V1 minimum mezokeszlet (6. fejezet).

### 8.3 Later extension (V1.1+ jeloltek)
- `IGNORE` role es `ignore_color_map`
- linetype-hint policy
- text/bend/guide feature role-ok
- entity-type specific policy

Ezek nem current-code truth elemek.

## 9. Existing profile/version mintakhoz illeszkedes
A future DXF rules profile domain szerkezetileg kovetheti a meglevo
owner-scoped + versioned mintat:
- profile tabla + version tabla szetvalasztas
- owner-konzisztencia
- lifecycle/is_active jellegu allapotok
- metadata json mezok

Ebben a taskban nincs migration, CRUD vagy API route implementacio.

## 10. Explicit anti-scope es anti-pattern lista
- Ne vezessunk be migration nelkul vegleges SQL truth mezoneveket.
- Ne fagyasszunk le implementacios reszletessegu state machine-t.
- Ne veglegesitsunk API endpoint payloadot.
- Ne bontsuk UI komponens-strukturara a taskot.
- Ne kezeljuk a legacy frontend `stock_dxf` / `part_dxf` terminust domain truth-kent.
- Ne kezeljuk a szint canonical truth-kent role helyett.

## 11. Bizonyitek forrasok
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
