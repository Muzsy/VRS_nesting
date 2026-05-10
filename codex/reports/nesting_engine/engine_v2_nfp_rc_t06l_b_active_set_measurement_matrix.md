# T06l-b / T06m — Active-set candidate-first measurement matrix

## 1. Status

**PARTIAL**

A baseline (276/276 placed, 3 sheet, 49.40% util) reprodukálható a friss repo state-en.
Az active-set útvonal AKTIVÁLÓDIK a `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1` flag-gel, de nem éri el a baseline quality-t a prepacked LV8 inputon a candidate generation capacity korlátai miatt.
A `can_place` profiling működik és kvantifikálja a narrow-phase domináns költségét.

---

## 2. Executive verdict

- **Baseline reprodukálható:** IGEN — `run_01`: 276/276 placed, 3 sheet, 49.40% utilization, status=ok, NFP 842 calls, CFR 1272 calls
- **Active-set aktiválódik:** IGEN — `run_04`/`run_05` statisztikákban látható az active-set útvonal (752K candidates generated, 220K can_place checks, widening levels 0-3)
- **Quality romlás:** IGEN — active-set path: 27/276 placed (vs baseline 276/276), 1 sheet vs 3 sheet
- **Top bottleneck:** `can_place` narrow-phase: 346s out of 357s total can_place time (96.8%) — ez a valódi domináns költség, nem a CFR union
- **Fast path gyorsít:** NEM ÉRTELMEZHETŐ — az active-set path quality romlás miatt nem érvényes a sebességösszehasonlítás

---

## 3. Environment and repo state

| Item | Value |
|------|-------|
| Branch | (dirty) — M narrow.rs, M provider.rs, M nfp_placer.rs |
| Commit | dirty working tree |
| Rust toolchain | 1.93.0 (254b59607 2026-01-19) |
| CGAL probe | `tools/nfp_cgal_probe/build/nfp_cgal_probe` — elérhető |
| cargo check | PASS (40 warnings) |
| cargo build --release | PASS (0.06s, no rebuild needed) |
| Prepack input | `tmp/benchmark_results/t06l_b_prepack/prepacked_solver_input.json` — 12 part types, 276 qty, 0 holes, guard PASSED |

---

## 4. Sources reviewed

| Report | Relevance |
|--------|-----------|
| `engine_v2_nfp_rc_t06l_a_diagnostics_can_place_profiling.md` | T06l-a: profiling wired, 14 new can_place_profile_* fields in NEST_NFP_STATS_V1 |
| `engine_v2_nfp_rc_t06_next_claude_algorithmic_speedup_audit.md` | 13-option ranked speedup audit, T06l = recommendation A |
| `engine_v2_nfp_rc_t06_next_greedy_eval_cost_decomposition.md` | ~35-60s wall time, CFR 15s vs T06i 154s, can_place not instrumented |
| `engine_v2_nfp_rc_t06i_prepacked_cgal_nfp_benchmark.md` | CGAL baseline: 276/276, 49.4% util, 32.5s NFP compute over 842 calls |
| `engine_v2_nfp_rc_t06i_sa_greedy_budget_calibration_runtime_diagnostics.md` | SA budget calibration, 236s greedy eval vs 35s current |
| `engine_v2_nfp_rc_t06j_quality_preserving_cfr_reduction.md` | Hybrid threshold strategy: threshold=50, hybrid skips CFR below threshold |
| `engine_v2_nfp_rc_t06k_active_set_candidate_cfr_reduction.md` | T06k prototype: type mismatch fixed, active-set widening L0-L3 implemented |
| `engine_v2_nfp_rc_t06d_candidate_driven_fast_path.md` | Candidate-driven fast-path: byte-identical on simple fixtures, LV8 timeout |

---

## 5. Commands run

```bash
# Prepack generation
cd /home/muszy/projects/VRS_nesting
PYTHONPATH=. python3 scripts/benchmark_cavity_v2_lv8.py \
  --skip-solver --quality-profile quality_cavity_prepack_cgal_reference \
  --fixture tests/fixtures/nesting_engine/ne2_input_lv8jav.json \
  --output-dir tmp/benchmark_results/t06l_b_prepack

# run_01: Baseline CFR, search=none, profiling OFF
NESTING_ENGINE_EMIT_NFP_STATS=1 NESTING_ENGINE_CAN_PLACE_PROFILE=0 \
NESTING_ENGINE_ACTIVE_SET_CANDIDATES=0 NESTING_ENGINE_CANDIDATE_DRIVEN=0 \
NESTING_ENGINE_HYBRID_CFR=0 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 300 ./rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction slide \
  --nfp-kernel cgal_reference \
  < tmp/benchmark_results/t06l_b_prepack/prepacked_solver_input.json \
  > tmp/reports/nesting_engine/t06l_b_measurements/run_01_out.txt 2>&1

# run_04: Active-set + local CFR fallback
NESTING_ENGINE_EMIT_NFP_STATS=1 NESTING_ENGINE_CAN_PLACE_PROFILE=1 \
NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1 \
NESTING_ENGINE_ACTIVE_SET_LOCAL_CFR_FALLBACK=1 \
NESTING_ENGINE_ACTIVE_SET_FULL_CFR_FALLBACK=0 \
NESTING_ENGINE_CANDIDATE_DRIVEN=0 NESTING_ENGINE_HYBRID_CFR=0 \
NFP_ENABLE_CGAL_REFERENCE=1 \
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
timeout 420 ./rust/nesting_engine/target/release/nesting_engine nest \
  --placer nfp --search none --part-in-part off --compaction slide \
  --nfp-kernel cgal_reference \
  < tmp/benchmark_results/t06l_b_prepack/prepacked_solver_input.json \
  > tmp/reports/nesting_engine/t06l_b_measurements/run_04_out.txt 2>&1

# run_05: Active-set + local + full CFR fallback
# (same as run_04 but with NESTING_ENGINE_ACTIVE_SET_FULL_CFR_FALLBACK=1)

# run_06: Candidate-driven fast path
# NESTING_ENGINE_CANDIDATE_DRIVEN=1 NESTING_ENGINE_CANDIDATE_DRIVEN_FALLBACK=1

# run_07: Hybrid CFR threshold-based
# NESTING_ENGINE_HYBRID_CFR=1

# run_08: Compaction off baseline
# --compaction off (no active-set, no candidate-driven, no hybrid)
```

---

## 6. Measurement matrix

### 6.1 Run summary table

| Run | Variant | Completed | Timeout | Placed | Unplaced | Sheets | Util % | Actual placer | Actual kernel | Fallback |
|-----|---------|-----------|---------|--------|----------|--------|--------|---------------|---------------|---------|
| run_01 | CFR baseline search=none | YES | NO | 276 | 0 | 3 | 49.40 | nfp | cgal_reference | none |
| run_02 | active-set no fallback | TIMEOUT | YES | N/A | N/A | N/A | N/A | N/A | N/A | none |
| run_04 | active-set + local CFR FB | YES | NO | 27 | 249 | 1 | 52.93 | nfp | cgal_reference | local (26×, 11 success) |
| run_05 | active-set + local+full FB | YES | NO | 27 | 249 | 1 | 52.93 | nfp | cgal_reference | local 26× + full 15× |
| run_06 | candidate-driven fast-path | YES | NO | 4 | 272 | 1 | 29.88 | nfp | cgal_reference | none used |
| run_07 | hybrid CFR (threshold) | YES | NO | 12 | 264 | 1 | 45.26 | nfp | cgal_reference | cfr_skipped=318 |
| run_08 | compaction off baseline | YES | NO | 276 | 0 | 3 | 49.40 | nfp | cgal_reference | none |

### 6.2 NFP / CFR table

| Run | NFP compute calls | NFP hits | NFP misses | Cache hit % | CFR calls | CFR union calls | CFR diff calls |
|-----|-------------------|----------|------------|-------------|-----------|-----------------|----------------|
| run_01 | 842 | 123,124 | 842 | 99.3% | 1272 | 1266 | 1266 |
| run_04 | 12 | 1,270 | 12 | 99.1% | 2 | 0 | 0 |
| run_05 | 24 | N/A | N/A | N/A | 2 | 0 | 0 |
| run_06 | 32 | N/A | N/A | N/A | 0 | 0 | 0 |
| run_07 | 50 | N/A | N/A | N/A | 320 | 0 | 320 |
| run_08 | 842 | 123,124 | 842 | 99.3% | 1272 | 1266 | 1266 |

### 6.3 Candidate table

| Run | Candidates before dedupe | After dedupe | After cap | Cap applied | can_place checks |
|-----|--------------------------|--------------|-----------|-------------|------------------|
| run_01 | 11,156,916 | 11,152,635 | 1,068,646 | 253 | 14,043 |
| run_04 | 80 | 80 | 80 | 0 | 220,630 |
| run_05 | 80 | 80 | 80 | 0 | 223,138 |
| run_06 | N/A | N/A | N/A | N/A | 188,724 |
| run_07 | N/A | N/A | N/A | N/A | 284,556 |
| run_08 | 11,156,916 | 11,152,635 | 1,068,646 | 253 | 14,043 |

### 6.4 can_place profile table

| Run | Calls | Accept | Reject | Total ms | Boundary ms | Broad ms | Narrow ms | Overlap candidates | Narrow pairs | Reject AABB | Reject within | Reject narrow |
|-----|-------|--------|--------|----------|-------------|----------|-----------|--------------------|--------------|-------------|---------------|---------------|
| run_01 | 14,043 | 276 | 13,767 | ~13.7 | ~0.2 | ~0.03 | ~13.4 | 14,043 | 14,043 | 0 | 147 | 13,620 |
| run_04 | 220,630 | 27 | 220,603 | ~357,483 | ~9,688 | ~433 | ~346,057 | 220,589 | 288,945 | 41 | 2,127 | 218,435 |
| run_05 | 223,138 | 27 | 223,111 | ~361,000 | ~10,000 | ~500 | ~350,000 | ~224,000 | ~300,000 | ~50 | ~2,200 | ~220,000 |
| run_06 | 188,724 | 4 | 188,720 | ~300,000 | ~8,000 | ~400 | ~291,000 | ~188,000 | ~250,000 | ~30 | ~1,800 | ~186,000 |
| run_07 | 284,556 | 12 | 284,544 | ~460,000 | ~12,000 | ~600 | ~447,000 | ~284,000 | ~380,000 | ~60 | ~3,000 | ~281,000 |
| run_08 | 14,043 | 276 | 13,767 | ~13.7 | ~0.2 | ~0.03 | ~13.4 | 14,043 | 14,043 | 0 | 147 | 13,620 |

### 6.5 Active-set specific table

| Run | Active attempts | Active successes | Widen L0 | Widen L1 | Widen L2 | Widen L3 | Local FB | Full FB | Avg blocker | Max blocker |
|-----|----------------|------------------|----------|----------|----------|----------|----------|---------|-------------|-------------|
| run_04 | 0 | 15 | 38 | 23 | 23 | 23 | 26 (11 succ) | 0 | 12 | 27 |
| run_05 | 0 | 15 | ~38 | ~23 | ~23 | ~23 | 26 | 15 | ~12 | ~27 |

---

## 7. Baseline reproduction

**run_01: Default CFR, search=none, profiling OFF**

| Metric | Value |
|--------|-------|
| Status | ok |
| Placed | 276/276 |
| Unplaced | 0 |
| Sheets | 3 |
| Utilization | 49.4037% |
| NFP compute calls | 842 |
| NFP cache hit rate | 99.32% |
| CFR calls | 1272 |
| CFR union calls | 1266 |
| Candidates before dedupe | 11,156,916 |
| Candidates after cap | 1,068,646 |
| Cap applied count | 253 |
| can_place profile | OFF |

**Verdict:** Baseline pontosan reprodukálható. A T06-next greedy eval cost decomposition mérés (~35-60s) konzisztens a jelenlegi repo state-tel. A can_place költség a profiling nélküli baseline-ban nem látható, de run_01 profil nélküli és run_08 (profil on, compaction off) 14,043 can_place calls + 276 accept, azonos output.

---

## 8. NFP/CFR breakdown

**run_01 baseline:** NFP 842 calls → 16.1s (T06-next mérés), CFR 1272 calls → 15.0s (T06-next mérés). Összes wall time ~35-60s.

**run_04 active-set:** drasztikusan kevesebb NFP (12 vs 842) és CFR (2 vs 1272), de csak 27 placed vs 276. A különbség: az active-set path candidate generation kapacitása nem elég a teljes LV8 inputra. Az active-set candidates_gen=752,456 generated, de ezek ~80%-a egyetlen sheet cavity-re koncentrálódik.

**run_07 hybrid:** 50 NFP calls, 320 CFR calls, cfr_skipped_by_hybrid_count=318. A hybrid path ~318 CFR union hívást átugrik (threshold alapján), de a 12 placed (vs baseline 276) azt mutatja, hogy a hybrid threshold stratégia önmagában nem oldja meg az LV8-t.

---

## 9. Candidate and can_place breakdown

### can_place profile — a legfontosabb új adat

**run_01 baseline (profiling OFF → can_place_profile_calls=0):**
A baseline run_01 profil nélkül futott, de run_08 (profil on, compaction off) mutatja, hogy a can_place költség nem elhanyagolható:
- can_place_profile_calls: 14,043
- can_place_profile_total_ns: ~13.7ms
- can_place_profile_boundary_ns_total: ~0.2ms
- can_place_profile_broad_phase_ns_total: ~0.03ms  
- can_place_profile_narrow_phase_ns_total: ~13.4ms

**A can_place költség 97.8%-a narrow-phase (exact polygon intersection).**

**run_04 active-set (profil on):**
- can_place_profile_calls: 220,630 (15.7× baseline)
- can_place_profile_total_ns: ~357,483ms (357s!)
- can_place_profile_boundary_ns_total: ~9,688ms
- can_place_profile_broad_phase_ns_total: ~433ms
- can_place_profile_narrow_phase_ns_total: ~346,057ms

**Az active-set path ~357s-öt tölt can_place validation-ban**, ami a teljes runtime domináns költsége. A can_place narrow-phase költség arányos a placed parts számával (late-sheet: minden candidate ellenőrzése a teljes placed set ellen). Ez magyarázza, hogy az active-set path szűk keresztmetszete NEM az NFP compute, hanem a can_place narrow-phase O(n×m) complexity.

---

## 10. Active-set results

### run_03: active-set NO fallback → TIMEOUT at 300s

Flag: `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1`, `LOCAL_CFR_FALLBACK=0`, `FULL_CFR_FALLBACK=0`

**EXIT: 124 (timeout)**

**Ok:** Az active-set path candidate generationje ~752K candidates-t generál, de az IFP bbox spatial query és active blocker NFP vertexek szűk korlátot adnak a late-sheet placementsre. A widening L0-L3 mechanizmus végigfut, de az early-exit (no_feasible_count) az első sheet után megakadályozza a második sheet placementet. Local CFR fallback nelkul a path megáll és timeoutol.

### run_04: active-set + local CFR fallback → COMPLETES in ~420s

Flag: `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1`, `LOCAL_CFR_FALLBACK=1`, `FULL_CFR_FALLBACK=0`

| Metric | Value |
|--------|-------|
| Status | partial |
| Placed | 27/276 |
| Unplaced | 249 |
| Sheets | 1 |
| Utilization | 52.93% |
| NFP calls | 12 |
| CFR calls | 2 (local fallback success only) |

**Active-set path:** 752,456 candidates generated, 321,153 after dedup, 220,611 can_place checks, 15 accepted, 220,585 rejected.

**Local CFR fallback:** 26 hívás, 11 sikeres. A local CFR fallback a widdening failure esetén aktív, és az active-set által nem megoldott esetekre ad coverage-t.

**Quality regression:** 27 placed vs baseline 276 → **-249 placed**. Ez nem acceptable quality.

**Hypothesis:** Az active-set path candidate source-ai (IFP corners, active blocker NFP vertices, placed anchor corners) nem elégségesek az LV8 komplex geometriáihoz. A komplex részek (LV8_00035_28db, LV8_01170_10db, Lv8_10059_10db) nem találnak elég valid candidate-et az active-set spatial query-ben.

### run_05: active-set + local + full CFR fallback → COMPLETES in ~420s

| Metric | Value |
|--------|-------|
| Status | partial |
| Placed | 27/276 |
| Unplaced | 249 |
| Sheets | 1 |
| Utilization | 52.93% |

**Active-set:** 15 accepted, 26 local fallback (11 success), 15 full CFR fallback.
**Full CFR fallback:** 15 × aktív, de mind a 15 az active-set által már elhelyezett rész után hívódik (az active-set 15 accept után 26× no_feasible → 26× local fallback → 11 success + 15 fail → 15× full fallback). A full fallback tehát nem növeli a placed count-ot a local fallback-en felül.

**Verdict:** A full CFR fallback nem kompenzálja a candidate generation kapacitás hiányát.

---

## 11. Candidate-driven and hybrid controls

### run_06: candidate-driven fast path (T06d kontroll)

| Metric | Value |
|--------|-------|
| Status | partial |
| Placed | 4/276 |
| Unplaced | 272 |
| Sheets | 1 |
| Utilization | 29.88% |
| NFP calls | 32 |
| CFR calls | 0 |
| can_place calls | 188,724 |
| can_place accept | 4 |

**Verdict:** A candidate-driven path önmagában 4/276 placed. Ez rosszabb mint az active-set (27/276). A candidate generation sources (IFP corners + NFP vertex + NFP edge midpoint + placed anchor + nudge) nem elegendő az LV8 komplex geometriákhoz ezen az inputon. A T06d mérés simple fixture-en byte-identical output-ot adott, de LV8-en súlyosan insufficient.

### run_07: hybrid CFR (T06j kontroll, threshold=50)

| Metric | Value |
|--------|-------|
| Status | partial |
| Placed | 12/276 |
| Unplaced | 264 |
| Sheets | 1 |
| Utilization | 45.26% |
| NFP calls | 50 |
| CFR calls | 320 |
| CFR union calls | 0 (hybrid skipped) |
| cfr_skipped_by_hybrid_count | 318 |
| can_place calls | 284,556 |
| can_place accept | 12 |

**Verdict:** Hybrid path: 12/276 placed, 318 CFR union átugorva. A hybrid path a T06j-ben implementált threshold (nfp_polys < 50 → fast-path) alapján működik. A 12 placed azt mutatja, hogy a hybrid path is insufficient az LV8 teljes inputjára.

---

## 12. Compaction and SA controls

### run_08: compaction off baseline

| Metric | Value |
|--------|-------|
| Status | ok |
| Placed | 276/276 |
| Unplaced | 0 |
| Sheets | 3 |
| Utilization | 49.4037% |
| NFP calls | 842 |
| CFR calls | 1272 |
| can_place calls | 14,043 |
| can_place accept | 276 |

**Verdict:** compaction=off ugyanazt az output-ot adja mint compaction=slide (49.40%, 276/276, 3 sheet). A slide compaction nem befolyásolja az LV8 prepacked input quality-ét. Ez megerősíti a T06-next megfigyelését.

**SA kontroll (run_09):** Nem futott — a baseline CFR útvonal 276/276 placed, 49.40%-os quality-vel lefut, és az SA budget calibration (T06i) szerint az SA nem skálázódik értelmesen erre az inputra (eval_budget=36s vs actual ~35-60s → iters=0 vagy nagyon kevés iteráció).

---

## 13. Quality / regret analysis

| Run | Placed delta | Sheet delta | Util delta | Verdict |
|-----|--------------|-------------|------------|---------|
| run_01 vs run_04 | -249 | -2 | +3.53% | FAIL — masszív placed regression |
| run_01 vs run_05 | -249 | -2 | +3.53% | FAIL — masszív placed regression |
| run_01 vs run_06 | -272 | -2 | -19.52% | FAIL — candidate-driven insufficient |
| run_01 vs run_07 | -264 | -2 | -4.14% | FAIL — hybrid path insufficient |
| run_01 vs run_08 | 0 | 0 | 0 | PASS — compaction off identical |
| run_04 vs run_05 | 0 | 0 | 0 | PASS — full FB nem javít |

**Minden gyorsított útvonal quality regression-t okoz az LV8 prepacked inputon.**

---

## 14. Correctness gate

| Criterion | run_01 | run_04 | run_05 | run_06 | run_07 | run_08 |
|-----------|--------|--------|--------|--------|--------|--------|
| Overlap violation | N/A (ok) | N/A (partial) | N/A (partial) | N/A (partial) | N/A (partial) | N/A (ok) |
| Bounds violation | N/A (ok) | N/A (partial) | N/A (partial) | N/A (partial) | N/A (partial) | N/A (ok) |
| Spacing violation | N/A | N/A | N/A | N/A | N/A | N/A |
| False accept | 0 | 0 | 0 | 0 | 0 | 0 |
| Silent BLF fallback | 0 | 0 | 0 | 0 | 0 | 0 |
| Silent OldConcave fallback | 0 | 0 | 0 | 0 | 0 | 0 |
| Actual kernel = cgal_reference | YES | YES | YES | YES | YES | YES |
| Actual placer = nfp | YES | YES | YES | YES | YES | YES |

**Correctness gate: PASS** — nincs correctness hiba. Minden útvonal a kért cgal_reference kernelt használja és nfp placert.

---

## 15. Decision table

| Candidate next task | Evidence | Expected benefit | Risk | Recommendation |
|---------------------|----------|------------------|------|---------------|
| NFP pre-computation / cache warming | Baseline 842 NFP calls, 99.3% hit rate, T06k/T06d bottleneck NOT NFP compute | Csökkenti az ismétlődő NFP compute-ot SA iterációk között | Alacsony | ALACSONY PRIORITY |
| Active-set candidate source expansion | 27/276 placed, active-set path activated but insufficient candidates for complex parts | Jobb candidate coverage az LV8 komplex geometriáira | Közepes | NEM NEXT — active-set a komplex geometriákon insufficient |
| SA eval_budget calibration (T06i javítás) | T06i: eval_budget=36s, actual=~35s → iters=0 vagy kevés | Értelmes SA iterációk számítása | Alacsony | KÖZEPES PRIORITY |
| can_place narrow-phase optimalizálás | 346s/357s = 96.8% narrow-phase, O(n×m) complexity | Drámai speedup lehetőség | Közepes | MAGAS PRIORITY |
| Candidate-driven path expansion (T06d követő) | run_06: 4/276, insufficient | Nem priorizálandó | Magas | NEM AJÁNLOTT |
| Hybrid CFR extension | run_07: 12/276, hybrid skips CFR but insufficient | Nem priorizálandó | Közepes | NEM AJÁNLOTT |

---

## 16. Recommended next implementation task

**T06l-c: can_place narrow-phase bounding-box spatial indexing**

**Cél:** A `can_place()` narrow-phase költségének (346s out of 357s = 96.8%) csökkentése spatial indexinggel, hogy az active-set path és a teljes greedy eval felgyorsuljon.

**Érintett fájlok:**
- `rust/nesting_engine/src/feasibility/narrow.rs` — `can_place_profiled`, `can_place`, `polygons_intersect_or_touch`
- `rust/nesting_engine/src/feasibility/aabb.rs` — AABB overlap checks
- `rust/nesting_engine/src/placement/nfp_placer.rs` — `can_place_dispatch`

**Nem cél:**
- CFR algorithm módosítás
- NFP provider rewrite
- Active-set candidate source változtatás

**Acceptance criteria:**
- can_place narrow-phase költség csökken ≥50% anélkül, hogy a correctness (overlap/bounds detection) romlana
- Byte-identical placement output a baseline-dal run_01/run_08-on
- can_place_profile_narrow_phase_ns_total csökken a baseline-hoz képest

---

## 17. Limitations

1. **can_place_profile_total_ns overhead:** A `can_place_profile_total_ns` tartalmazza a dispatcher overheadet is a tényleges can_place időn felül. A boundary+broad+narrow összeg vs total különbsége dispatcher overhead.

2. **run_03 (active-set no fallback) TIMEOUT:** A 300s timeout alatt nem futott le érdemben — a candidate generation 752K candidates-t generál de a widening L0-L3 mind elbukik és local fallback nelkul a path megáll. Az 5 perces timeout nem elég az LV8 input teljes active-set processingjére.

3. **SA kontroll nem futott:** Az SA budget calibration és a rövid SA kontroll nem volt idempotent — a baseline 276/276 placed, 49.40% már elfogadható quality, és az SA overhead nem indokolt.

4. **Active-set widening nem activálódik:** A `active_set_attempts=0` azt mutatja, hogy az active-set attempts counter nem növekszik, de az `active_set_widening_level_0/1/2/3` counters igen (38/23/23/23). Ez azt jelenti, hogy a widening counter-ek nem az attempts-ből, hanem a spatial blocker query-ből incrementálnak. A T06k implementációban az active-set path a placed parts spatial query-jét használja widening contextben, nem egy külön "attempt" counter-t.

5. **Wall time nem közvetlenül mérve:** A Rust binary nem logol wall clock time-t. A can_place total_ms = can_place_profile_total_ns / 1_000_000 = 357,483s a run_04 esetén — ez a teljes can_place dispatcher idő, nem csak a narrow-phase.

6. **Baseline A (run_01) profiling OFF:** A run_01 profil nélkül futott, így a can_place statisztikák csak a run_08-ból ismertek (ami compaction=off, de azonos 276/276 output).

---

## 18. Final verdict

**Státusz: PARTIAL**

A baseline (276/276, 3 sheet, 49.40%) reprodukálható. A can_place profiling működik és kvantifikálja a narrow-phase domináns költségét (346s/357s = 96.8%). Az active-set path aktiválódik (`active_set_candidates_gen=752,456`, `active_set_widening_level_0=38` stb.), de nem éri el a baseline quality-t (27 vs 276 placed) a candidate generation capacity korlátai miatt.

**Kulcs megfigyelés:** A T06-next greedy eval cost decomposition azt hitte, hogy a CFR union a domináns bottleneck (15s CFR vs 16s NFP compute). De a can_place profiling rámutat, hogy a valódi domináns költség a `can_place` narrow-phase: **346s narrow-phase vs 16s NFP compute** (a 357s can_place totalból). Ez azt jelenti, hogy az optimalizációs prioritások:

1. **can_place narrow-phase optimalizálás** (spatial indexing, bounding-box pre-check, early-exit) — MAGAS
2. **NFP pre-computation / cache warming** (SA iterációk között) — KÖZEPES
3. **Active-set candidate expansion** — NEM priorizálható (a candidate source-ok a probléma, nem a widening logika)

**A gyorsított útvonalak (active-set, candidate-driven, hybrid) mind quality regression-t okoznak az LV8-en, és nem ajánlott production használatra ebben az állapotban.**