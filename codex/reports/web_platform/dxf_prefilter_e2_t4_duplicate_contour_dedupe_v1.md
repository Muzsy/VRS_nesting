PASS

## 1) Meta
- Task slug: `dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1`
- Kapcsolodo canvas: `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.yaml`
- Futas datuma: `2026-04-20`
- Branch / commit: `main@bc4fa73` (folytatva)
- Fokusz terulet: `Backend (duplicate contour dedupe only)`

## 2) Scope

### 2.1 Cel
- Kulon T4 backend duplicate-dedupe service letrehozasa az E2-T1 inspect + E2-T2 role-resolution + E2-T3 gap-repair truth retegekre epitve.
- Az eredeti zart kontur inventory importer public probe feluleten keresztuli ujraepitese (`normalize_source_entities`, `probe_layer_rings`), majd T3 repaired konturok bevonasa.
- Csak cut-like (`CUT_OUTER`, `CUT_INNER`) zart konturvilagban futtatott tolerancias duplicate-ekvivalencia es determinisztikus keeper/drop policy.
- Rejtegezett kimenet: `closed_contour_inventory`, `duplicate_candidate_inventory`, `applied_duplicate_dedupes`, `deduped_contour_working_set`, `remaining_duplicate_candidates`, `review_required_candidates`, `blocking_conflicts`, `diagnostics`.
- Unit teszt + smoke deterministic bizonyitek az exact/tolerancias/cross-role/profile boundary esetekre.

### 2.2 Nem-cel (explicit)
- Nem keszult normalized DXF writer (T5).
- Nem keszult acceptance gate (`accepted_for_import` / `preflight_rejected`) (T6).
- Nem keszult DB persistence, API route, upload trigger vagy frontend UI valtoztatas.
- Nem nyitott uj parser/chainer motort; a meglevo importer truth maradt az egyetlen forras.
- Nem nyitottuk ujra a gap-repair vagy role-resolver policy domaineket.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok
- Backend service:
  - `api/services/dxf_preflight_duplicate_dedupe.py`
- Unit teszt + smoke:
  - `tests/test_dxf_preflight_duplicate_dedupe.py`
  - `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- Codex artefaktok:
  - `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
  - `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.yaml`
  - `codex/prompts/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1/run.md`
  - `codex/codex_checklist/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
  - `codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`

### 3.2 Miert valtoztak?
- **Service:** a T4 lane kulon tolerancias keeper/drop dedupe truth-ot igenyel, amely expliciten elkulonul az inspect exact duplicate signal retegétol.
- **Teszt + smoke:** deterministic bizonyitek kellett arra, hogy a service helyesen kezeli az exact/tolerancias/over-threshold/cross-role/profile es original-vs-T3 eseteket.
- **Doksi artefaktok:** task checklist/report evidence alapu lezarasahoz.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md` (eredmeny az AUTO_VERIFY blokkban)

### 4.2 Opcionalis, feladatfuggo parancsok
- `python3 -m py_compile api/services/dxf_preflight_duplicate_dedupe.py tests/test_dxf_preflight_duplicate_dedupe.py scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- `python3 -m mypy --config-file mypy.ini api/services/dxf_preflight_duplicate_dedupe.py`
- `python3 -m pytest -q tests/test_dxf_preflight_duplicate_dedupe.py`
- `python3 scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Letrejott kulon backend duplicate dedupe service az E2-T1/E2-T2/E2-T3 truth-okra epitve. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:75` | A `dedupe_dxf_duplicate_contours` bemenetkent inspect+role+gap objektumot kap, es ezekbol allitja elo a T4 dedupe truth-ot. | `python3 -m pytest -q tests/test_dxf_preflight_duplicate_dedupe.py` |
| A T4 minimal rules profile boundary validalva/normalizalva van. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:54`; `api/services/dxf_preflight_duplicate_dedupe.py:523` | `_ALLOWED_RULES_PROFILE_FIELDS` + `_normalize_rules_profile` csak a 4 T4 mezôt fogadja el, a tobbit diagnosticsba sorolja. | `tests/test_dxf_preflight_duplicate_dedupe.py:153` |
| A service csak cut-like zart konturvilagban dolgozik. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:53`; `api/services/dxf_preflight_duplicate_dedupe.py:101`; `api/services/dxf_preflight_duplicate_dedupe.py:201` | `_CUT_LIKE_ROLES` + `dedupe_eligible` szures biztosítja, hogy auto-dedupe csak `CUT_OUTER`/`CUT_INNER` role-okon fusson. | `tests/test_dxf_preflight_duplicate_dedupe.py:306` |
| A duplicate equivalence tolerancias es determinisztikus. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:743` | `_ring_alignment_distance` ciklikus/iranyfuggetlen illesztessel mer tavolsagot; threshold a `duplicate_contour_merge_tolerance_mm`. | `tests/test_dxf_preflight_duplicate_dedupe.py:210`; `tests/test_dxf_preflight_duplicate_dedupe.py:231` |
| A keeper/drop policy explicit es bizonyithato. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:682`; `api/services/dxf_preflight_duplicate_dedupe.py:450` | `_keeper_rank_key` + `keeper_evidence` rogziti: importer_probe elony, canonical layer elony, stabil tie-break. | `tests/test_dxf_preflight_duplicate_dedupe.py:252`; `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py:186` |
| A kimenet kulon retegeken adja vissza a T4 contract mezoket. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:506` | A return shape kulon adja a `closed_contour_inventory`, `duplicate_candidate_inventory`, `applied_duplicate_dedupes`, `deduped_contour_working_set`, `remaining_duplicate_candidates`, `review_required_candidates`, `blocking_conflicts`, `diagnostics` retegeket. | `tests/test_dxf_preflight_duplicate_dedupe.py:132` |
| Nem nyitottuk meg a normalized DXF writer / acceptance gate / route / persistence / UI scope-ot. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:506`; `tests/test_dxf_preflight_duplicate_dedupe.py:139` | Nincs acceptance vagy writer kimenet; nincs route/db/frontend erintes. | `tests/test_dxf_preflight_duplicate_dedupe.py:139` |
| A report kulon elvalasztja inspect exact duplicate jelet es T4 tolerancias keeper/drop dontest. | PASS | `api/services/dxf_preflight_duplicate_dedupe.py:839`; `api/services/dxf_preflight_duplicate_dedupe.py:844` | `diagnostics.notes` expliciten kulon nevezi a T1 exact signal vs T4 tolerance decision reteget. | `tests/test_dxf_preflight_duplicate_dedupe.py:185`; `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py:122` |
| Keszult task-specifikus unit teszt es smoke script. | PASS | `tests/test_dxf_preflight_duplicate_dedupe.py:1`; `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py:1` | 11 unit teszt + tobb smoke scenario deterministic fixture-ekkel. | `python3 -m pytest -q tests/test_dxf_preflight_duplicate_dedupe.py`; `python3 scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py` |
| Checklist + report evidence alapon frissult. | PASS | `codex/codex_checklist/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md:1`; `codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md:61` | DoD pontok kipipalva, matrix es futtatasi bizonyitek rogzitve. | self-review |
| `./scripts/verify.sh --report ...` PASS. | PASS | `codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md:91`; `codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.verify.log` | A wrapper futas eredmenye az AUTO_VERIFY blokkban rogzitve. | `./scripts/verify.sh --report ...` |

## 6) Kulon kiemelesek (run.md kovetelmenyek)

- **Minimal rules profile mezok:** `auto_repair_enabled`, `duplicate_contour_merge_tolerance_mm`, `strict_mode`, `interactive_review_on_ambiguity`.
- **Inspect exact vs T4 tolerance kulonvalasztas:** a T1 `duplicate_contour_candidates` csak exact fingerprint jel; a T4 kulon tolerancias alignment tavolsag alapjan hoz keeper/drop dontest.
- **Auto-dedupe candidate definicio:** csak cut-like, zart kontur, same-role, tolerancian beluli geometria, policy szerint egyertelmu keeper.
- **Keeper policy:** importer probe first, canonical source layer second, stabil tie-break harmadik.
- **Over-tolerance / ambiguity / cross-role kezeles:** named conflict family-k (`duplicate_candidate_over_tolerance`, `ambiguous_duplicate_group`, `duplicate_cross_role_conflict`, stb.) review/blocking routinggal.
- **Mi maradt T5/T6-ra:** normalized DXF writer (T5), acceptance gate (T6).

## 7) Advisory notes
- A T4 duplicate equivalence point-count alapu topology-safety gate-et hasznal: eltero vertexszam eseten nincs silent merge.
- A `strict_mode` vagy `interactive_review_on_ambiguity=False` ugyanazzal a konfliktus-nevvel blocking szintre emeli a bizonytalan eseteket.
- A T4 outputban a `deduped_contour_working_set` mar dedupe-aware closed contour truth, amit a kovetkezo lane-ek ujrakitallalas nelkul tudnak hasznalni.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-20T19:44:53+02:00 → 2026-04-20T19:47:45+02:00 (172s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.verify.log`
- git: `main@bc4fa73`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? api/services/dxf_preflight_duplicate_dedupe.py
?? canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md
?? codex/codex_checklist/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md
?? codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.yaml
?? codex/prompts/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1/
?? codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md
?? codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.verify.log
?? scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py
?? tests/test_dxf_preflight_duplicate_dedupe.py
```

<!-- AUTO_VERIFY_END -->
