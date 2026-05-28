PASS

# Report — SGH-Q20R-R1 top-k coordinate descent + report consistency fix

SGH-Q20R_R1_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: NOT_REQUIRED_NOW

---

## 1) Meta

* **Task slug:** `sgh_q20r_r1_topk_report_consistency_fix`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q20r_r1_topk_report_consistency_fix.yaml`
* **Futás dátuma:** 2026-05-28
* **Branch / commit:** main / 5610d5645438c54b255ed523fa0a8c4d843985fe (uncommitted changes on top)
* **Fókusz terület:** Geometry | Mixed

---

## 2) Scope

### 2.1 Cél

1. Azonosítani a Q20R false claim-eket: `coord_descent_top_k`, `TransformCandidate`, top-k refinement nem léteztek Q20R-ban.
2. Implementálni a valódi top-k coordinate descent-et: `TransformCandidate` struct, determinisztikus sortolás, top-k coord descent loop.
3. Átnevezni az érintett Q20R teszteket a canonical R1 nevekre.
4. A Q20R report/checklist false claim-jeit javítani.
5. R1 report és checklist elkészítése.

### 2.2 Nem-cél (explicit)

1. Q21 shape-aware severity scoring.
2. Q22 shrink-loop redesign.
3. Q19 LV8 benchmark gate.
4. Q18B CDE session/cache rewrite.
5. Bármilyen IO contract változás (a JSON mezők neve és szemantikája azonos marad).

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

**Modified:**
* `rust/vrs_solver/src/optimizer/search_position.rs` — `coord_descent_top_k` mező hozzáadva, `TransformCandidate` struct, kandidátus-gyűjtő logika, determinisztikus sortolás, top-k coord descent loop, 4 új teszt, T7 átnevezése
* `rust/vrs_solver/src/optimizer/separator.rs` — `separator_search_position_reduces_simple_overlap` → `separator_search_position_reduces_simple_overlap_still_passes` átnevezés
* `codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md` — `PASS_WITH_NOTES` státusz, DoD #17 INCOMPLETE→R1, R1 korrekció megjegyzés, tesztnevezék frissítése
* `codex/codex_checklist/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md` — kitöltve (már meglévő volt)
* `codex/codex_checklist/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md` — kitöltve

### 3.2 Miért változtak?

**`search_position.rs`:** A Q20R csak az egyetlen legjobb kandid. eval értékét tartotta nyilván (`best_loss`, `best_x`, …). Az R1 `Vec<TransformCandidate>` gyűjtőt vezet be, determinisztikusan sortol (eval ASC, majd sheet_index, rotation, x, y), és a top-k-t külön-külön finomítja.

**`separator.rs`:** A tesztnév-átnevezés a R1 canonical tesztnév-készletet valósítja meg a canvas specifikációja szerint.

**Report/checklist:** A Q20R report DoD #17 tévesen állította, hogy `coord_descent_top_k` és `TransformCandidate` léteznek. Az R1 korrekcióval a Q20R report `PASS_WITH_NOTES` státuszt kap, az R1 report a valódi implementációt dokumentálja.

---

## 4) Verifikáció

### 4.1 Kötelező parancs

```
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
```

### 4.2 Feladatfüggő parancsok (előzetesen lefuttatva)

```
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::search_position
# → 11 passed; 0 failed  (7 Q20R + 4 új R1 teszt)

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
# → összes separator teszt zöld, incl. renamed _still_passes

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
# → q20_rotation_refinement_regression_still_passes: ok

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# → 383 passed; 0 failed

python3 scripts/smoke_sgh_q20r_sparrow_search_position.py
# → 37 passed, 0 failed — SMOKE: PASS
```

### 4.3 AUTO_VERIFY blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-28T23:11:02+02:00 → 2026-05-28T23:14:10+02:00 (188s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.verify.log`
- git: `main@6af4359`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 ...h_q20r_sparrow_search_position_coord_descent.md |  16 +-
 rust/vrs_solver/src/optimizer/search_position.rs   | 304 +++++++++++++++++----
 rust/vrs_solver/src/optimizer/separator.rs         |   2 +-
 3 files changed, 257 insertions(+), 65 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/reports/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md
 M rust/vrs_solver/src/optimizer/search_position.rs
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q20r_r1_topk_report_consistency_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix/
?? codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md
?? codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.verify.log
```

<!-- AUTO_VERIFY_END -->

---

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt |
| -------- | ------: | ------------------------ | ---------- | ---------------- |
| #1 Q20R false claims azonosítva | PASS | Q20R report DoD #17 audit | `coord_descent_top_k`, `TransformCandidate`, top-k loop nem volt Q20R-ban | — |
| #2 `SearchPositionConfig.coord_descent_top_k` | PASS | `search_position.rs` `SearchPositionConfig` struct | `pub coord_descent_top_k: usize`, default=3 | `search_position_refines_top_k_candidates_when_configured` |
| #3 `TransformCandidate` struct | PASS | `search_position.rs` `struct TransformCandidate` | sheet_index, rect_min_x, rect_min_y, rotation_deg, eval | `search_position_refines_top_k_candidates_when_configured` |
| #4 Globális finite kandidátusok gyűjtése | PASS | `search_position_for_target()` `candidates.push(...)` a global grid loopban | f64::MAX és Unsupported szűrve; zero-loss early-return megtartva | `search_position_refines_top_k_candidates_when_configured` |
| #5 Fókuszált finite kandidátusok gyűjtése | PASS | `search_position_for_target()` `candidates.push(...)` a focused loop-ban | Ugyanaz a logika, mint globális | `search_position_focused_sampling_is_deterministic` |
| #6 Unsupported kandidátusok szűrése | PASS | `if r.unsupported { stats.samples_unsupported += 1; continue; }` | CDE/Jagua Unsupported → skip, nem kerül `candidates`-be | `search_position_rejects_backend_unsupported_samples` |
| #7 Determinisztikus sortolás | PASS | `candidates.sort_by(...)` eval.total_cmp + sheet_index + rotation + x + y | `f64::total_cmp` (Rust 1.93) garantálja a stabilitást | `search_position_top_k_tie_break_is_deterministic` |
| #8 Top-k coord descent loop | PASS | `for cand in candidates.iter().take(top_k)` | Minden top-k kandid.-ra `coord_descent_from()` fut | `search_position_refines_top_k_candidates_when_configured` |
| #9 `refined_samples` == top_k (nonzero-loss fixture) | PASS | `stats.refined_samples += 1` minden iterációban | Full-sheet blocker garantálja, hogy minden grid pos. loss > 0 | `search_position_reported_refined_samples_matches_top_k_for_nonzero_loss_fixture` |
| #10 Legjobb refinált kandid. determinisztikusan | PASS | `best_refined.map_or(true, |(bl, ..)| cd_loss < bl)` | Pontosan az `eval` minimum-at veszi | `search_position_top_k_tie_break_is_deterministic` |
| #11 k=0 → refinement disabled | PASS | `top_k = cfg.coord_descent_top_k.min(candidates.len())` → 0 → loop skip | `best_refined = None` → fallback a legjobb unrefined kandid.-ra | `search_position_refine_top_k_zero_disables_refinement_or_is_rejected_by_config_validation` |
| #12 Continuous rotation axis változatlan | PASS | `coord_descent_from(... is_continuous ...)` logika érintetlen | R1 nem változtatta a rotation axis descent implementációt | `search_position_continuous_uses_rotation_axis_in_coord_descent` |
| #13 Non-continuous policies: no illegal rotations | PASS | `rotation_candidates_for_item()` logika érintetlen | R1 nem változtatta a rotation policy kezelést | `search_position_respects_non_continuous_rotation_policy` |
| #14 CDE/Jagua no bbox fallback | PASS | `eval_with_backend_trait()` nem változott; smoke fixture4 `bbox_fallback_queries==0` | R1 nem érintette a backend evaluation path-t | `search_position_existing_cde_no_bbox_fallback_still_passes` |
| #15 LBF fallback explicit + counted | PASS | `separator.rs` `allow_lbf_fallback`, `search_stats.lbf_fallback_used` érintetlen | R1 nem változtatta a separator integrációt | `separator_search_position_reduces_simple_overlap_still_passes` |
| #16 Renamed tests exist with canonical names | PASS | `search_position_existing_cde_no_bbox_fallback_still_passes`, `separator_search_position_reduces_simple_overlap_still_passes` | Mindkét teszt létezik és zöld | `cargo test --lib` |
| #17 Q20R report javítva | PASS | `sgh_q20r_sparrow_search_position_coord_descent.md`: `PASS_WITH_NOTES`, DoD #17 `INCOMPLETE→R1` | Report nem állít többé nem létező mezőket | — |
| #18 383 lib teszt zöld | PASS | `cargo test --lib` → 383 passed, 0 failed | +4 új R1 teszt hozzáadva a meglévő 379-hez | `cargo test --lib` |
| #19 Q20R smoke változatlan PASS | PASS | `python3 scripts/smoke_sgh_q20r_sparrow_search_position.py` → 37 passed | Top-k implementáció nem rontotta el a meglévő fixture-öket | Q20R smoke |

---

## 6) IO contract / minták

Nincs IO contract változás. A `search_position_*` JSON mezők neve és szemantikája azonos. A `refined_samples` értéke most ténylegesen a top-k iterációszámot tükrözi (Q20R-ban ez mindig 1 volt).

---

## 7) Doksi szinkron

Nem releváns — nincs docs/ változás.

---

## 8) Advisory notes

* **Q20R report státusz:** A Q20R report `PASS_WITH_NOTES`-ra változott. A DoD #17 inaccuracy nem érintette a search_position funkcionalitásának többi részét — a Q20R core implementáció (separator integráció, CDE backend, GLS preserving) helyes volt.
* **`refined_samples` szemantika Q20R vs R1:** Q20R-ban `refined_samples` mindig 1 volt (egyetlen best candidate refinement). R1 után `refined_samples == min(coord_descent_top_k, candidate_count)`. A smoke fixture-ök erre nem assertálnak explicit értékre, csak `> 0`-ra.
* **Zero-loss early return megmarad:** Ha bármely grid/focused sample `loss == 0`, azonnal visszatér — nincs szükség top-k refinement-re. Ez a teljesítmény-optimalizáció megmarad.
* **`total_cmp` a sortolásban:** `f64::total_cmp` (Rust 1.62+) NaN-safe és teljesen determinisztikus, szemben a `partial_cmp`-vel. Rustc 1.93 van, nincs kompatibilitási probléma.
* **Q18B:** A jelenlegi CDE correctness szint elegendő az R1 feladathoz. Dedikált Q18B task ha szükséges.

---

## 9) Follow-ups

* **Q21:** `evaluate_transform()` smooth severity proxyjának cseréje valódi CDE severity scoring-ra.
* **`coord_descent_top_k` tuning:** Default k=3 a 276-részes benchmark-on is megmérendő. Esetleg k=5 jobb minőséget ad elfogadható overhead-del.
* **Candidate cap:** Sok sheet + sok rotation esetén a `candidates` Vec nagy lehet. Cap hozzáadása (pl. top-500 globális) a memory footprint korlátozáshoz.
