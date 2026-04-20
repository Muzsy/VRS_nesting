# DXF Prefilter E2-T4 — Duplicate contour dedupe V1

## Cel
A DXF prefilter lane-ben az inspect truth (E2-T1), a canonical role-resolution truth (E2-T2)
es a gap-repair working truth (E2-T3) alápjan keszuljon el a **determinista,
csak egyertelmuen duplikalt zart vagokonturokat osszevono duplicate contour dedupe backend reteg**.
A T4 feladata nem a normalized DXF artifact es nem az acceptance gate, hanem a cut-like, mar lezart
konturvilagbol a tenylegesen azonos / tolerancian belul azonos duplicate ring-ek felismerese,
determinisztikus keeper/drop dontese es naplozasa ugy, hogy a T5/T6 lane-ek mar egy dedupe-aware
working truth-ra tudjanak ulni.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E2-T1 inspect engine mar tudja a nyers inventory/candidate truth-ot:
  - `entity_inventory`, `layer_inventory`, `color_inventory`, `linetype_inventory`
  - `contour_candidates`, `open_path_candidates`, `duplicate_contour_candidates`
  - `outer_like_candidates`, `inner_like_candidates`, `diagnostics`
- az E2-T2 role resolver mar kulon, determinisztikus canonical role-vilagot ad:
  - `layer_role_assignments`
  - `entity_role_assignments`
  - `resolved_role_inventory`
  - `review_required_candidates`
  - `blocking_conflicts`
- az E2-T3 gap repair mar eloallit egy kulon repair-aware working truth-ot:
  - `applied_gap_repairs`
  - `repaired_path_working_set`
  - `remaining_open_path_candidates`
  - `review_required_candidates`
  - `blocking_conflicts`

Ugyanakkor a T4 szempontjabol a mai truth meg **nem eleg**:
- az inspect `duplicate_contour_candidates` csak exact fingerprint-szintu jelzo; nem tolerancias,
  nem canonical-role-aware, es nem tartalmaz keeper/drop policyt;
- az inspect `contour_candidates` csak bbox + fingerprint shape-et hordoz, nem a vegso dedupe working setet;
- a T3 `repaired_path_working_set` mar hordoz lezart ringeket, de nincs olyan kulon service,
  amely az eredeti closed ring-eket es a T3-bol jovo repaired ring-eket egyesiti, osszeveti es
  determinisztikusan dedupalja;
- a `duplicate_contour_merge_tolerance_mm` policy mezot az E1 docs freeze rogzitette,
  de a jelenlegi kod meg nem hasznalja.

Ezert a T4 helyes iranya:
- a meglevo importer public probe truth-ra (`normalize_source_entities` + `probe_layer_rings`) epiteni az eredeti,
  cut-like closed ring inventory-t;
- ehhez hozzavenni a T3 `repaired_path_working_set` closed ring-jeit;
- kulon backend duplicate-dedupe service-ben, szuk policy alatt eldonteni, hogy mely konturok
  tarthatoak meg es melyek torolhetoek duplicate-kent;
- de meg **nem** belepni normalized DXF writer / acceptance gate / route / persistence / UI scope-ba.

## Scope boundary

### In-scope
- Kulon backend duplicate contour dedupe service az inspect + role-resolution + gap-repair truth-ra epitve.
- Minimal, T4-ban tenylegesen hasznalt rules profile boundary:
  - `auto_repair_enabled`
  - `duplicate_contour_merge_tolerance_mm`
  - `strict_mode`
  - `interactive_review_on_ambiguity`
- Az eredeti, cut-like closed ring inventory ujra-probe-ja a meglevo importer public feluleten keresztul.
- A T3 `repaired_path_working_set` bevonasa ugyanabba a dedupe working truth-ba.
- Duplicate candidate-ek felismerese csak zart, cut-like konturvilagban.
- Determinisztikus keeper/drop policy ugyanazon duplicate group-on belul.
- Applied duplicate-dedupe summary + deduped working set + unresolved/review/blocking signalok.
- Task-specifikus unit teszt + smoke.

### Out-of-scope
- Uj DXF parser vagy a meglevo importer truth lecserelese.
- Color/layer role policy ujranyitasa (T2 marad a canonical role truth).
- Gap repair ujranyitasa vagy `CHAIN_ENDPOINT_EPSILON_MM` policy modositas.
- Normalized DXF writer vagy artifact export (T5).
- Acceptance gate, `accepted_for_import` / `preflight_rejected` jellegu kimenet (T6).
- DB persistence, API route, upload trigger, frontend UI.
- Reszleges atfedes, containment, hasonlo-de-nem-azonos topology automatikus merge-je.
- Cross-role duplicate silent merge (pl. outer vs inner ugyanazzal a geometriaval).

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/services/dxf_preflight_inspect.py`
  - current-code truth: inspect-only layer; ma exact `duplicate_contour_candidates` jelet ad,
    de vegso dedupe working setet nem.
- `api/services/dxf_preflight_role_resolver.py`
  - current-code truth: canonical role assignment; mar elvalasztja a cut-like vs marking-like reteget.
- `api/services/dxf_preflight_gap_repair.py`
  - current-code truth: kulon `repaired_path_working_set`-et ad a T3 residual gap fixekrol;
    explicit mondja, hogy a duplicate contour dedupe a T4 scope.
- `vrs_nesting/dxf/importer.py`
  - current-code truth: az egyetlen parser/chaining truth a repoban;
  - relevans public feluletek:
    - `normalize_source_entities(...)`
    - `probe_layer_rings(...)`
  - a T4-hez mar elegendo, hogy a closed ring geometriat public probe-on keresztul vissza lehessen olvasni.
- `vrs_nesting/geometry/clean.py`
  - current-code truth: determinisztikus ring-normalizalo/clean helper-ek;
  - relevans lehet a tolerancias canonicalization es keep/drop előtti ring-normalform kialakitasahoz,
    de a T4 ne nyisson meg uj geometry-clean policy sávot.
- `tests/test_dxf_preflight_inspect.py`
  - current-code truth: mar bizonyitja az exact duplicate contour jelzes es topology-proxy shape-et.
- `tests/test_dxf_preflight_role_resolver.py`
  - current-code truth: a cut-like vs marking-like layer truth mar stabil.
- `tests/test_dxf_preflight_gap_repair.py`
  - current-code truth: a T3 `repaired_path_working_set` contract mar stabil.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - E1-T1 freeze; rogziti, hogy a V1-ben az egyertelmu duplikalt zart kontur dedupe auto-fix lehet.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - E1-T3 freeze; rogziti a `duplicate_contour_merge_tolerance_mm` mezot.
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
  - E1-T7 freeze; rogziti a duplicate/review/error csaladok helyet.
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
  - immediate predecessor; explicit mondja, hogy a T4 duplicate contour dedupe kulon modosito lepes.

## Jelenlegi repo-grounded helyzetkep
Az inspect jelenleg ket kulon, de nem elegseges duplicate truth-ot ad:
- `probe_layer_rings(...)` public szinten visszaadja az eredeti closed ring geometriat;
- `duplicate_contour_candidates` csak exact fingerprint-group, amely elsosorban inspect-level signal.

Kovetkezmeny:
- a T4 **nem** elegedhet meg az inspect `duplicate_contour_candidates` exact fingerprint-groupjaival,
  mert a V1 policy mező `duplicate_contour_merge_tolerance_mm` tolerancias duplicate dedupe-t var;
- a T4-nek kulon, determinisztikus closed-contour working setet kell osszeallitani:
  - eredeti importer ring-ek (cut-like canonical role-u layerekrol)
  - plusz T3 `repaired_path_working_set` elemek
- es erre kell duplicate equivalence / keeper policy-t alkalmaznia.

Masodik fontos current-code gap:
- ma nincs kulon policy arra, hogy ugyanazon duplicate group-ban melyik kontur maradjon meg;
- a T5 normalized DXF writernek viszont mar egy dedupe-aware working truth kell,
  kulonben ugyanaz a geometriatovabbitas tobb peldanyban maradna benne.

Ezert a T4-ben explicit, tesztelt keeper policy kell.

## Konkret elvarasok

### 1. A T4 a meglevo importer probe + T3 working truth-ra epuljon, ne uj parserre
A duplicate dedupe ne sajat DXF-olvasot vagy sajat ring-epitot vezessen be.
A helyes boundary:
- eredeti closed ring-ek: `normalize_source_entities(...)` + `probe_layer_rings(...)`;
- repaired closed ring-ek: `gap_repair_result["repaired_path_working_set"]`;
- a service ne olvasson mas truth-ot, mint amit ugyanaz az importer es a T3 mar hasznal.

### 2. A T4 inputja az inspect + role-resolution + gap-repair truth legyen
A T4 service helyes boundary-ja:
- bemenet: `inspect_result`
- bemenet: `role_resolution`
- bemenet: `gap_repair_result`
- bemenet: minimal rules profile

Indok:
- a T2 mar eldontotte, mely layer/path cut-like vagy marking-like;
- a T3 mar eloallitotta a repaired, lezart ring-eket;
- a T4-nek ezekbol kell egy egyesitett closed-contour working truth-ot epitenie.

### 3. A T4 csak cut-like, zart konturvilagban dolgozzon
A duplicate dedupe V1 fokusza:
- csak olyan kontur kerulhet dedupe vizsgalatba, amely a T2 szerint `CUT_OUTER` vagy `CUT_INNER`;
- marking-like vagy unassigned kontur ne kapjon csendes duplicate dedupe-t;
- open path vilag tovabbra sem T4 scope; a T4 csak zart konturokkal foglalkozhat.

### 4. A duplicate equivalence definicioja legyen explicit es szuk
Csak az legyen auto-dedupe candidate, ahol egyszerre teljesul:
- `auto_repair_enabled = true`
- a ket kontur ugyanabban a canonical role-ban van (`CUT_OUTER` vagy `CUT_INNER`)
- a ring-geometriak ugyanazt a zart konturt reprezentaljak, legfeljebb
  `duplicate_contour_merge_tolerance_mm` alatti pont-/elteres mellett
- nincs topology-konfliktus (nem reszleges atfedes, nem containment, nem mas belso struktura)
- a duplicate group keeper/drop policy alapjan egyertelmu, melyik maradjon

Ami nem fer bele a T4 V1-be:
- reszleges atfedes merge
- containment alapu "ez majdnem ugyanaz" heurisztika
- cross-role duplicate auto-merge
- marking/unassigned duplicate auto-merge
- nyitott path auto-javitas

### 5. A keeper policy legyen determinisztikus es dokumentalt
A T4-nek explicit, tesztelt keeper policy kell ugyanazon duplicate group-on belul.
Javasolt, repo-grounded sorrend:
1. eredeti importer-forrasbol jovo closed ring elvezzen elsoseget a T3 `source="T3_gap_repair"` ringgel szemben;
2. ugyanazon origin-tipuson belul a mar explicit canonical source layerrol jovo kontur elvezzen elonyt a nem-canonical source layerrol jovovel szemben;
3. ezutan stabil, deterministic tie-break kovesse pl. `(canonical_role, layer, source, ring_index/path_index)` sorrenddel.

Kritikus boundary:
- a T4 reportban kulon legyen megnevezve, hogy miert pont ez marad meg;
- az `applied_duplicate_dedupes` lista ne csak a drop-ot, hanem a keeper evidenciat is hordozza.

### 6. A T4 kimenete legyen dedupe-aware working truth, de meg ne artifact
A minimum output shape kulon retegeken adja vissza peldaul:
- `rules_profile_echo`
- `closed_contour_inventory`
- `duplicate_candidate_inventory`
- `applied_duplicate_dedupes`
- `deduped_contour_working_set`
- `remaining_duplicate_candidates`
- `review_required_candidates`
- `blocking_conflicts`
- `diagnostics`

Kritikus boundary:
- nincs normalized DXF file iras;
- nincs `accepted_for_import` vagy vegso lifecycle dontes;
- nincs DB/persistence/API side-effect.

A T4 altal eloallitott `deduped_contour_working_set` legyen eleg a T5/T6 kovetkezo lane-eknek,
anelkul hogy meg egyszer ki kellene talalni, mely konturok duplicate-kent mar kiestek.

### 7. Az ambiguity kezelese legyen policy-vezerelt es evidence-alapu
Minimum konfliktus/review csaladok:
- `duplicate_dedupe_disabled_by_profile`
- `duplicate_candidate_over_tolerance`
- `ambiguous_duplicate_group`
- `duplicate_cross_role_conflict`
- `duplicate_topology_not_safe`
- `cut_like_duplicate_remaining_after_dedupe`

Policy:
- `interactive_review_on_ambiguity=true` -> ambiguity review-required retegbe menjen;
- `strict_mode=true` -> ugyanaz a csalad blocking retegbe kerulhessen, ha a V1 fail-fast policy ezt keri;
- a T4 ne emeljen acceptance outcome-ot, csak dedupe truth-ot es konfliktusjeleket adjon.

### 8. A T4 kulon reportolja az inspect exact duplicate jelet es a T4 tolerancias dedupe dontest
Ez kulcskovetelmeny.
A reportban es diagnosticsban kulon kell nevezni:
- hogy az inspect `duplicate_contour_candidates` exact fingerprint-szintu jel mar T1-ben megjelent;
- a T4 csak a closed working seten futtatta le a tenyleges, tolerancias keeper/drop dedupe dontest;
- az `applied_duplicate_dedupes` lista csak a T4 altal tenylegesen eldobott duplicate konturokat tartalmazza.

### 9. A teszteles fedje le a fontos duplicate csaladokat
Minimum deterministic coverage:
- exact duplicate same-role closed ring -> keeper/drop sikeres dedupe;
- kis coordinate-noise mellett, tolerancian beluli duplicate -> sikeres dedupe;
- tolerancian kivuli, hasonlo de nem ugyanaz -> nincs auto-dedupe;
- eredeti source ring vs T3 repaired duplicate -> az eredeti ring marad;
- cross-role duplicate geometry -> nem silent merge, hanem review/blocking;
- marking/unassigned duplicate -> nem silent dedupe;
- output nem tartalmaz acceptance outcome-ot vagy DXF artifactot;
- legalabb egy scenario, ahol dedupe sikeres;
- legalabb egy scenario, ahol review-required objektum jon;
- legalabb egy scenario, ahol blocking conflict jon.

### 10. Kulon legyen kimondva, mi marad a kovetkezo taskokra
A reportban es canvasban is legyen explicit:
- T5: normalized DXF writer
- T6: acceptance gate

A T4-ben ezekhez csak a deduped contour working truth keszul el.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1/run.md`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `tests/test_dxf_preflight_duplicate_dedupe.py`
- `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.verify.log`

## DoD
- [ ] Letrejott kulon backend duplicate contour dedupe service, amely az E2-T1 inspect + E2-T2 role resolver + E2-T3 gap repair truth-ra ul.
- [ ] A T4-ben tenylegesen hasznalt rules profile mezok minimal validator/normalizer hataron mennek at.
- [ ] A service csak cut-like, zart konturvilagban dolgozik.
- [ ] A duplicate equivalence `duplicate_contour_merge_tolerance_mm` policy menten, determinisztikusan van definialva.
- [ ] A keeper/drop policy explicit, tesztelt, es kulon evidenciaval visszaadhato.
- [ ] A kimenet kulon listazza a `duplicate_candidate_inventory` / `applied_duplicate_dedupes` /
      `deduped_contour_working_set` / `review_required_candidates` / `blocking_conflicts` retegeket.
- [ ] A task nem nyitotta meg a normalized DXF writer / acceptance gate / route / persistence / UI scope-ot.
- [ ] A T4 report kulon elvalasztja az inspect exact duplicate jelet es a T4 tolerancias dedupe dontest.
- [ ] Keszult task-specifikus unit teszt es smoke script.
- [ ] A checklist es report evidence-alapon frissult.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md` PASS.

## Kockazat + rollback
- Kockazat:
  - a T4 idovel elott belecsuszik normalized DXF writer vagy acceptance gate scope-ba;
  - a tolerancias duplicate equivalence tul agressziv lesz es valos, de nem azonos konturokat egyesit;
  - a keeper policy nem lesz eleg determinisztikus, es ugyanaz a fixture mas kept/drop eredmenyt adhat.
- Mitigacio:
  - a T4 csak a meglevo importer probe + T3 working truth altal hordozott closed ring-ekkel dolgozhat;
  - explicit tolerance boundary es explicit cross-role tiltast kell tesztelni;
  - nincs DXF iras, nincs acceptance outcome.
- Rollback:
  - az uj duplicate dedupe service + teszt + smoke egy task-commitban visszavonhato a T1/T2/T3 truth retegek erintese nelkul.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/dxf_preflight_duplicate_dedupe.py tests/test_dxf_preflight_duplicate_dedupe.py scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
  - `python3 -m pytest -q tests/test_dxf_preflight_duplicate_dedupe.py`
  - `python3 scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`

## Lokalizacio
Nem relevans.

## Kapcsolodasok
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/geometry/clean.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
