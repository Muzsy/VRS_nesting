# DXF Prefilter E2-T5 — Normalized DXF writer V1

## Cel
A DXF prefilter lane-ben az inspect truth (E2-T1), a canonical role-resolution truth (E2-T2),
a gap-repair working truth (E2-T3) es a duplicate-dedupe working truth (E2-T4) alapjan keszuljon el a
**determinista normalized DXF writer backend reteg**, amely mar kepes egy helyben letrehozott,
letoltheto / tovabbadhato **normalizalt DXF artifactot** eloallitani a jelenlegi kodbazisra ulve.

A T5 feladata nem acceptance gate es nem persistence/API/UI, hanem a prefilter lane jelenlegi working
truth-jabol egy olyan lokalis DXF artifact eloirasa, amely:
- a cut-like zart konturokat mar a T4 `deduped_contour_working_set` alapjan irja ki,
- a marking-like geometriat a jelenlegi importer truth-bol, canonical layerre forditva tudja tovabbvinni,
- canonical layer/szin vilagot hasznal,
- es a kovetkezo T6 acceptance gate-nek mar konkret, writer-szintu artifact truth-ot ad.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E2-T1 inspect mar kulon nyers inventory/candidate truth-ot ad;
- az E2-T2 role resolver mar ad canonical layer/entity szerepkor-vilagot (`CUT_OUTER`, `CUT_INNER`, `MARKING`);
- az E2-T3 gap repair mar eloallit repair-aware closed/open working truth-ot;
- az E2-T4 duplicate dedupe mar eloallitja a `deduped_contour_working_set` cut-like closed kontur truth-ot,
  es explicit kimondja, hogy a normalized DXF writer a T5 scope.

Ugyanakkor a mai repoban meg **nincs** olyan kulon prefilter writer reteg, amely:
- a T4 dedupe-aware cut konturokat valodi DXF artifactta irja,
- a role-resolved marking-like geometriat canonical `MARKING` layerre forditja,
- a `canonical_layer_colors` policy mezót tenylegesen felhasznalja,
- es egy helyben eloallitott, deterministic normalized DXF artifactot ad vissza persistence nelkul.

A T5 helyes iranya ezert:
- a meglevo importer truth-ra (`normalize_source_entities`) epiteni a source-entity replay boundary-t;
- a cut-like worldot **nem** az eredeti source entity-kbol, hanem a T4 `deduped_contour_working_set`-bol ujrairni;
- a marking-like worldot a T2 entity/layer role truth alapjan, a source geometry determinisztikus replay-jevel canonical layerre forditani;
- de meg **nem** belepni acceptance gate / DB persistence / API route / upload trigger / UI scope-ba.

## Scope boundary

### In-scope
- Kulon backend normalized DXF writer service a T1/T2/T3/T4 truth retegekre epitve.
- Minimal, T5-ben tenylegesen hasznalt rules profile boundary:
  - `canonical_layer_colors`
- A source entity replay-hez a meglevo importer public truth hasznalata (`normalize_source_entities`).
- A cut-like world ujrairasa a T4 `deduped_contour_working_set` alapjan canonical `CUT_OUTER` / `CUT_INNER` layerre.
- A marking-like world deterministic replay-je canonical `MARKING` layerre, ahol a source entity geometry ezt lehetove teszi.
- Canonical layer-szin policy alkalmazasa a writerben.
- Lokalis, explicit `output_path`-ra irt normalized DXF artifact.
- Writer metadata + diagnostics + skipped-entity summary.
- Task-specifikus unit teszt + smoke.

### Out-of-scope
- Uj DXF parser vagy a meglevo importer truth lecserelese.
- Role resolver policy ujranyitasa (T2 marad a source-of-truth a canonical role vilagra).
- Gap repair vagy duplicate dedupe policy ujranyitasa (T3/T4 marad a source-of-truth).
- Acceptance outcome (`accepted_for_import`, `preflight_rejected`, stb.) vagy lifecycle dontes (T6).
- DB persistence, `preflight_artifacts` record, storage bucket, API route, upload trigger, frontend UI.
- Full fidelity source-preserving rewriter minden letezo entity-tipusra.
- Machine/export artifact world (`vrs_nesting/dxf/exporter.py` sheet placement / part insert logika) ujranyitasa.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/services/dxf_preflight_inspect.py`
  - current-code truth: `source_path`, raw inventories, `contour_candidates`, `open_path_candidates`, `duplicate_contour_candidates`, diagnostics.
- `api/services/dxf_preflight_role_resolver.py`
  - current-code truth: `layer_role_assignments`, `entity_role_assignments`, `resolved_role_inventory`, `review_required_candidates`, `blocking_conflicts`.
- `api/services/dxf_preflight_gap_repair.py`
  - current-code truth: `repaired_path_working_set`, `remaining_open_path_candidates`, diagnostics.
- `api/services/dxf_preflight_duplicate_dedupe.py`
  - current-code truth: `deduped_contour_working_set`, `applied_duplicate_dedupes`, `remaining_duplicate_candidates`, diagnostics.
- `vrs_nesting/dxf/importer.py`
  - current-code truth: a meglevo parser/public normalization source-of-truth;
  - relevans public feluletek:
    - `normalize_source_entities(...)`
    - `probe_layer_rings(...)`
    - `probe_layer_open_paths(...)`
- `vrs_nesting/dxf/exporter.py`
  - current-code truth: van benne repo-szintu, ezdxf-alapu entity replay/iras minta;
  - a T5 feladata nem a placement exporter foltozasa, de a line/polyline/arc/circle/spline/ellipse irasi mintak groundingkent hasznalhatok.
- `tests/test_dxf_exporter_source_mode.py`
  - current-code truth: mar bizonyitja, hogy a repo tud source entity-ket DXF-be replay-elni `ezdxf` alapon.
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
  - E1-T3 freeze; rogziti a `canonical_layer_colors` mezót.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
  - E1-T1 freeze; rogziti, hogy a prefilter accepted/rejected/review world csak a gate-ben (kesobb) formalodik.
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
  - E1-T4 freeze; az `accepted_for_import` vilag T6 scope.
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
  - E1-T7 freeze; user-facing / diagnostics csaladok groundingja.
- `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
  - immediate predecessor; explicit mondja, hogy a normalized DXF writer a T5 scope.

## Jelenlegi repo-grounded helyzetkep
A T4 mar eloallitja a dedupe-aware, cut-like closed contour truth-ot:
- `deduped_contour_working_set`
- `applied_duplicate_dedupes`
- `remaining_duplicate_candidates`
- `review_required_candidates`
- `blocking_conflicts`

Ez elegendo ahhoz, hogy a T5 **ne** az eredeti, potencialisan nyitott vagy duplikalt source cut entity-ket replay-elje,
hanem mar a T4 altal megtisztitott closed contour truth-bol irja ki a cut-vilagot.

Masik fontos current-code teny:
- a `normalize_source_entities(...)` mar hordozza a raw source entity geometry-t es a preflight raw signalokat
  (`layer`, `type`, `closed`, `color_index`, `linetype_name`, pontok/center/radius/stb.),
  igy a T5-nek van meglevo repo-grounded forrasa a marking-like entity-k deterministic replay-jehez.

Kovetkezmeny:
- a T5 helyes writer-modellje **ketcsatornas**:
  1. **cut-like canonical writer** a T4 `deduped_contour_working_set` alapjan;
  2. **marking-like passthrough writer** a source entity truth + T2 role truth alapjan.

Harmadik fontos current-code gap:
- a `canonical_layer_colors` policy mezot eddig egyik E2 service sem hasznalta;
- a T5 az elso pont, ahol ez a mezo tenylegesen writer-side hatassal birhat.

## Konkret elvarasok

### 1. A T5 a meglevo importer truth-ra es a T4 working truth-ra epuljon, ne uj writer/parse motorra
A normalized writer ne sajat DXF-olvasot vagy sajat geometry-helyreallitot epitsen.
A helyes boundary:
- source geometry replay: `normalize_source_entities(...)`;
- cut-like normalized truth: T4 `deduped_contour_working_set`;
- marking-like canonical role truth: T2 `entity_role_assignments` / `layer_role_assignments`.

### 2. A cut-like worldot a T4 `deduped_contour_working_set` irja felul a source entity vilag helyett
A T5-ben a `CUT_OUTER` / `CUT_INNER` layer geometriat **nem** az eredeti source entity-kbol kell visszairni,
hanem a T4 `deduped_contour_working_set` elemeibol.

Indok:
- a T3/T4 mar kezelt gap/duplicate truth-ot hoz letre;
- ha a writer az eredeti source entity-ket irna vissza, a normalized artifact visszahozhatna a mar kiszurt nyitott vagy duplikalt vagokonturokat.

A T5 V1-ben a cut-like world egyszeru, determinisztikus writer alakja lehet:
- closed `LWPOLYLINE` kiiras canonical `CUT_OUTER` / `CUT_INNER` layerre.

### 3. A marking-like worldot a source entity truth-bol, canonical layerre forditva kell tovabbvinni
A T5 ne probalja a marking entity-ket T3/T4 stilusu repair/dedupe logikaval ujrairni.
A helyes boundary:
- a T2 role truth mondja meg, hogy mely entity/layer marking-like;
- a T5 ezeket a source geometry alapjan replay-elheti canonical `MARKING` layerre;
- ahol a source entity tipus a repo-grounded writer boundaryn belul van (`LINE`, `LWPOLYLINE`, `POLYLINE`, `ARC`, `CIRCLE`, `SPLINE`, `ELLIPSE`), ott deterministic replay tortenjen;
- ahol ez nem lehetseges, ott structured `skipped_source_entities` / diagnostics szülessen, de ez meg ne legyen acceptance outcome.

### 4. A minimal rules profile boundary a T5-ben a `canonical_layer_colors`
A T5 a policy schema teljes vilagat ne nyissa ujra.
Minimal rules profile mezok:
- `canonical_layer_colors`

Elvaras:
- a writer normalizalja/validalja ezt a boundary-t;
- csak az elfogadott T5 mezo keruljon a `rules_profile_echo` kimenetbe;
- legyen deterministic default a canonical layerekre, ha a profil nem ad meg explicit szint.

### 5. A writer kimenete legyen explicit artifact + metadata, de meg ne persistence/API vilag
A minimum output shape kulon retegeken adja vissza peldaul:
- `rules_profile_echo`
- `normalized_dxf`
  - `output_path`
  - `writer_backend`
  - `written_layers`
  - `written_entity_count`
  - `cut_contour_count`
  - `marking_entity_count`
- `writer_layer_inventory`
- `skipped_source_entities`
- `diagnostics`

Kritikus boundary:
- ez meg **nem** `preflight_artifacts` record;
- nincs storage upload / DB insert;
- nincs acceptance outcome.

### 6. A writer lehetoleg egyetlen lokalis output path-ra dolgozzon
A T5 service helyes boundary-ja egy explicit `output_path` parameter.
Ez deterministic tesztelest es smoke-ot tesz lehetove, es elvalasztja a T5-ot a kesobbi E3 persistence vilagtol.

### 7. A T5 ne valjon acceptance gate-te, de a diagnosticsban nevezze meg az unresolved truth-ot
A T5 nem mondhatja ki, hogy a file `accepted_for_import` vagy `rejected`.
Viszont a diagnosticsban kulon nevezze meg:
- ha a T4 `blocking_conflicts` / `review_required_candidates` tovabbra is jelen vannak;
- hogy a writer artifact onmagaban nem acceptance verdict;
- hogy az acceptance gate a T6 scope.

### 8. A T5 kulon nevezze meg, hogy a normalized cut world mar polygonizalt/canonicalizalt
Ez kulcskovetelmeny.
A reportban es diagnosticsban kulon kell nevezni:
- hogy a source cut entity-kbol a T3/T4 working truth utan mar canonical closed contour writer lett;
- hogy a cut-like entity world ezert nem full-fidelity source replay, hanem canonicalized normalized output;
- a marking-like passthrough ettol kulon kezelt reteg.

### 9. A teszteles fedje le a fontos writer csaladokat
Minimum deterministic coverage:
- T4 deduped `CUT_OUTER` / `CUT_INNER` konturokbol sikerul DXF-et irni;
- az output DXF-ben a cut-like geometriak canonical layeren vannak;
- a `canonical_layer_colors` tenylegesen megjelenik a layer/entity writer oldalon;
- duplicate/open source cut geometry nem szivarog vissza az artifactba;
- marking-like source entity canonical `MARKING` layerre kerul;
- out-of-scope / unsupported source entity structured skip diagnosztikat kap;
- output nem tartalmaz acceptance outcome-ot;
- legalabb egy smoke scenario a teljes T1->T2->T3->T4->T5 lancot bizonyitja lokalis artifact irassal es visszaolvasassal.

### 10. Kulon legyen kimondva, mi marad a kovetkezo taskra
A reportban es canvasban is legyen explicit:
- T6: acceptance gate

A T5 csak a normalized DXF artifact + writer metadata truth-ot kesziti elo.

## Erintett fajlok / celzott outputok
- `canvases/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1/run.md`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `tests/test_dxf_preflight_normalized_dxf_writer.py`
- `scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- `codex/reports/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.verify.log`

## DoD
- [ ] Letrejott kulon backend normalized DXF writer service, amely az E2-T1/E2-T2/E2-T3/E2-T4 truth-ra ul.
- [ ] A T5-ben tenylegesen hasznalt rules profile mezok minimal validator/normalizer hataron mennek at.
- [ ] A cut-like world a T4 `deduped_contour_working_set` alapjan, canonical `CUT_OUTER` / `CUT_INNER` layerre irodik ki.
- [ ] A marking-like world source entity replay-jel, canonical `MARKING` layerre tud tovabbmenni, ahol a geometry boundary ezt megengedi.
- [ ] A writer alkalmazza a `canonical_layer_colors` policy-t, deterministic defaulttal.
- [ ] A service lokalis normalized DXF artifactot ir explicit `output_path`-ra, es writer metadata / diagnostics kimenetet ad.
- [ ] A task nem nyitotta meg az acceptance gate / persistence / route / UI scope-ot.
- [ ] A report kulon nevezi a canonicalized cut-world vs marking passthrough writer boundary-t.
- [ ] Keszult task-specifikus unit teszt es smoke script.
- [ ] A checklist es report evidence-alapon frissult.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md` PASS.

## Kockazat + rollback
- Kockazat:
  - a T5 idovel elott acceptance gate-te vagy persistence layerre csuszik;
  - a writer visszaszivarogtatja az eredeti duplicate/open cut source entity-ket;
  - a marking passthrough tul sok, jelenleg nem kezelt entity-tipust probal silent replay-elni.
- Mitigacio:
  - a cut-like world kizárólag a T4 `deduped_contour_working_set`-bol irhato vissza;
  - a marking-like world csak a repo-grounded source entity boundaryn belul replay-elheto;
  - explicit skipped-source diagnostics kell, nincs silent acceptance.
- Rollback:
  - az uj normalized writer service + teszt + smoke egy task-commitban visszavonhato a T1/T2/T3/T4 truth retegek erintese nelkul.

## Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- Feladat-specifikus ellenorzes:
  - `python3 -m py_compile api/services/dxf_preflight_normalized_dxf_writer.py tests/test_dxf_preflight_normalized_dxf_writer.py scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`
  - `python3 -m pytest -q tests/test_dxf_preflight_normalized_dxf_writer.py`
  - `python3 scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`

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
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/dxf/exporter.py`
- `tests/test_dxf_exporter_source_mode.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `tests/test_dxf_preflight_duplicate_dedupe.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
