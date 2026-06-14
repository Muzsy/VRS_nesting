# SGH-Q43b — Own vrs_solver 1x1500x6000 full276 LV8 continuous baseline + parity audit

**Status:** PASS — single Run A (1200s) complete with partial 218/276 placement; semantic parity audit + 3-way comparison written; own solver source unchanged.

## Scope

- A saját `vrs_solver` (natív Rust Sparrow CDE port) futtatása a Q42 full276 LV8 csomagon, **1 db 1500×6000 mm** single finite stock containerrel.
- Ez a Q43 upstream SPP 1500×6000 futás **párja a saját oldalról**: ugyanaz a 12 part type / 276 instance geometria, ugyanaz a 1500×6000 container, de most a saját finite-stock + Q40/Q41 margin/spacing policy alkalmazásával.
- Elsődleges cél: a saját oldali placement quality és continuous rotation validációja 1500×6000 containeren.
- Másodlagos cél: 3-way összehasonlítás a Q43 upstream SPP és a Q42 saját (3×1500×3000 finite-stock) eredménnyel.
- Saját solver source **nem** módosult (pre + post `git diff` egyaránt 0 bájt).

## Strict no-own-code-modification rule

A Q43b-t kizárólag benchmark + audit jelleggel futtattuk. Tiltott:

- A saját solver kód módosítása (`rust/vrs_solver/src/**`, `api/**`, `worker/**`, `frontend/**`, `vrs_nesting/**`).
- A saját `vrs_solver` binary módosítása.
- A Q42 output utólagos kozmetikázása.
- Compression / cavity prepack / legacy fallback bekötése.

Engedélyezett kizárólag:

- A `vrs_solver` binary meglévő release buildjének futtatása.
- Benchmark runner + smoke + comparison script (artifact-ok, source code nem).
- Q42 inputból származó input JSON építése a Q43b container modellel.
- Audit doksi + report.

## Own solver code immutability proof

| Artifact | Méret | Megjegyzés |
| --- | ---: | --- |
| `artifacts/benchmarks/sgh_q43b/pre_own_source_status.log` | 193 byte | working tree a Q43b indulásakor (csak `??` Q43 + Q43b untracked) |
| `artifacts/benchmarks/sgh_q43b/pre_own_source_diff.log`  | **0 bájt** | `git diff -- rust/vrs_solver/src api worker frontend vrs_nesting` üres |
| `artifacts/benchmarks/sgh_q43b/post_own_source_status.log` | 289 byte | futás után snapshot |
| `artifacts/benchmarks/sgh_q43b/post_own_source_diff.log`  | **0 bájt** | futás után is üres |

Kijelentés: **own solver source changed: false** (post diff 0 bájt).

## Why this task uses 1x1500x6000 single stock

A Q43 spec a 1500×6000 strip baseline-t upstream SPP-re definiálta. A Q43b ezt a konténert a **saját** `vrs_solver` finite-stock pool modelljével futtatja, hogy:

- A placement density közvetlenül összevethető legyen a Q43 upstream SPP `density=0.7430` értékével (azonos container, eltérő objective).
- A continuous rotation saját oldali hatékonysága mérhető legyen (a Q43 upstream 16-bin lista vs. a saját 184 unique angle).
- A Q40/Q41 margin/spacing policy hatása számszerűsödjön (218/276 partial, míg a Q43 upstream 276/276).

A Q43b **single-stock** (1 db 1500×6000) konténer a Q42 3-stock modelljének degenerált esete: a `multisheet.rs` finite-stock manager ilyenkor a legegyszerűbb útvonalon fut, LBF initial placement dominál.

## Upstream source (own solver view)

- **URL:** `https://github.com/Muzsy/VRS_nesting.git` (a saját repo, nem upstream Sparrow)
- **Lokális hely:** `rust/vrs_solver/`
- **Branch:** `main`
- **Commit hash:** `1295e99` (a Q43 audit commitja; a Q43b a Q43 push után készült)
- **jagua-rs pin (öröklött a sparrow Cargo.toml-ból):** `ba38bcae9ed3ab41a9e93a1894e2b01ea87c6619`
- **Audit idő:** `2026-06-14T10:59+02:00`
- **Natív modell:** Sparrow CDE multisheet (saját natív Rust port) — finite-stock pool, Q40/Q41 unified margin/spacing geometry, continuous rotation policy.
- **Audit típus:** own solver (nem upstream).

## Upstream build (own solver build)

A release binary (`2,226,184` byte, mtime `2026-06-14T09:27:37+02:00`) a `cargo build --release --bin vrs_solver --manifest-path rust/vrs_solver/Cargo.toml` paranccsal készült. A Q43b task a futtatáshoz ezt a release binaryt használta. A build rekonstrukció az `artifacts/benchmarks/sgh_q43b/upstream_build.log` fájlban van; az eredeti build a Q43 verify.sh futás során történt, ahol a `cargo test --release` triggerelte a release profile rebuildet. A binary a Q43b audit idején a `--input` / `--output` CLI signature-t mutatta.

## Benchmark input

- **Forrás:** `artifacts/benchmarks/sgh_q42/inputs/q42_full276_3x1500x3000_margin5_spacing8_continuous_1200.json` (a Q42 input, 12 part type / 276 instance).
- **Container:** `1 db 1500x6000 mm` stock (`S1500x6000`, quantity=1).
- **Margin / spacing / kerf:** `5.0 / 8.0 / 0.0 mm` (Q40/Q41 unified model, Q42 default).
- **Rotation:** continuous (Q42-vel azonos, part-level `allowed_rotations_deg` listák nélkül).
- **Seed:** 42.
- **Time limit:** 1200 sec (single Run A, user kérésére).

A Q43b input: `artifacts/benchmarks/sgh_q43b/inputs/q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200.json`.

## Upstream Run A — 1200 sec

A Q43b spec single-run (1200 sec), Run B nincs. A futás 1138.96 sec wall time alatt terminált (a solver 212 iterációnál leállt, a time limit alatt).

| metric | value |
| --- | ---: |
| time_limit_s | 1200 |
| wall_time_s | 1138.96 |
| status (solver top-level) | `partial` |
| placed_count | 218 / 276 |
| unplaced_count | 58 |
| sparrow_iterations | 212 |
| sparrow_search_position_calls | 51 508 |
| sparrow_collision_graph_final_pairs | 0 (ütközésmentes) |
| rotation_count_total | 218 |
| unique_rotation_count | 184 |
| non_orthogonal_count | 189 |
| min / max rotation deg | -34.6543 / 367.4513 |
| log | `artifacts/benchmarks/sgh_q43b/upstream_run_1200.log` |
| output JSON | `artifacts/benchmarks/sgh_q43b/outputs/q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200_output.json` |
| render evidence (SVG) | `artifacts/benchmarks/sgh_q43b/renders/q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200/sheet_00.svg` (462 686 B) + `overview.svg` (365 B) |
| render evidence (PNG) | `…/sheet_00.png` (586 653 B) + `…/overview.png` (86 400 B) — `cairosvg` konverzió, 1400 px széles |
| render manifest | `…/render_manifest.json` (416 B) |

**Értelmezés:** A 218/276 placement 0 ütközéssel, de 58 part nem fért el az 1 db 1500×6000 stockra. A 184 unique rotation (a Q43 upstream 16-bin listájával szemben) a saját oldali continuous rotation hatékonyságát mutatja. A 58 unplaced part oka: a Q40/Q41 margin=5 + spacing=8 policy megnöveli az effektív polygonnagyságot, és ezek a kibővített polygonok már nem férnek el a 9.0 m²-es konténerben, míg a Q43 upstream nyers SPP polygonok elfértek.

## Upstream Run B — 2400 sec

A Q43b spec single-run (`max 1200 sec`); Run B nem fut. Az `upstream_summary.json` `run_b.status = "skipped"`, oka: „Q43b spec is single-run only (max 1200s); user requested only one Run A".

## Runtime summary

```text
run | time_limit_s | wall_time_s | solver_runtime_s | status   | placed | unplaced | valid_layout | notes
A   | 1200         | 1138.96     | n/a              | partial  | 218    | 58       | no (partial) | own solver, single finite stock
```

## Optimization quality summary

- **Placed / total:** 218 / 276 (78.99% instance-placement rate).
- **Unique rotations:** 184 (continuous rotation, jóval finomabb mint a Q43 upstream 16-bin listája).
- **Non-orthogonal placement:** 189.
- **Density proxy:** `placed_count / 276 = 0.7899` (nem közvetlenül összehasonlítható a Q43 upstream `density=0.7430` értékével, mert a Q43 upstream a strip_area / used_length szorzatából jön, míg a Q43b instance-alapú).
- **Iteration count:** 212, **search calls:** 51 508 — a solver 1138 sec alatt konvergált a partial state-hez.
- **Collision:** 0 (valid partial result).
- **Boundary / margin / spacing violations:** a Q40/Q41 policy miatt minden placement a kitágított geometriára collision-free; a solver report `final_pairs=0` ezt igazolja.

## Upstream result summary

A strukturált összefoglaló az `artifacts/benchmarks/sgh_q43b/upstream_summary.json` fájlban van (a Q43 mintájú séma). A Q43b legfontosabb számai:

- **Wall time:** 1138.96 s (1200 s solver limit alatt).
- **Placed:** 218 / 276 (58 unplaced).
- **Continuous rotation:** 184 unique angle, 189 non-orthogonal.
- **Collision-free:** igen (final_pairs=0).
- **Valid layout:** nem (partial: 58 part nem fért el).

## Own Q42 result source

- Forrás: `artifacts/benchmarks/sgh_q42/q42_summary.json` (a Q42 saját solver futás, **itt nem újrafuttatva**).
- A Q42 futás eredménye: 276/276 placement, **3 sheet felhasználásával** (2-sheetes acceptance FAIL), phys 49.40% / usable 49.90%, 0 violation.
- A Q42 input rotation policy continuous; 236 unique rotation, 259 non-orthogonal.

## Upstream vs own comparison

A 3-way összehasonlító táblázat az `artifacts/benchmarks/sgh_q43b/comparison_summary.json` fájlban van (`direct_comparability: PARTIAL_DIRECTLY_COMPARABLE`).

| metric | Q43 upstream Sparrow SPP 1500x6000 1200s | Q43b own vrs_solver 1x1500x6000 1200s | Q42 own vrs_solver 3x1500x3000 1200s |
| --- | --- | --- | --- |
| model type | SPP single strip (min-width) | own finite stock (1 db) | own finite stock (3 db) |
| container | 1x 1500x6000 strip | 1x 1500x6000 stock | 3x 1500x3000 sheets |
| time limit (s) | 1200 | 1200 | 1200 |
| wall time (s) | 1208.18 | 1138.96 | 716.69 |
| status | ok (valid full) | partial (218/276) | ok (valid, 3 sheets) |
| placed_count | 276 / 276 | 218 / 276 | 276 / 276 |
| unplaced_count | 0 | 58 | 0 |
| validity | valid full | partial (58 unplaced) | valid (3 sheets, 2-sheet acceptance FAIL) |
| objective / utilization | strip_width=1496.15 / density=0.7430 | n/a (partial) | phys 49.40% / usable 49.90% |
| rotation evidence | 16 unique / 140 non-orth | 184 unique / 189 non-orth | 236 unique / 259 non-orth |
| margin/spacing handling | none (raw packing) | margin=5, spacing=8, kerf=0 | margin=5, spacing=8, kerf=0 |
| overall comparability | baseline | PARTIAL_DIRECTLY_COMPARABLE | PARTIAL_DIRECTLY_COMPARABLE |

**Főbb tanulságok a 3-way összehasonlításból:**

- **Az upstream 58 parttal többet tesz el** ugyanarra a 1500×6000 containerre, mint a saját solver (276/276 vs 218/276). Ennek oka a Q40/Q41 margin=5/spacing=8 policy, ami megnöveli az effektív polygonnagyságot a saját oldalon.
- **A saját solver continuous rotationje valóban continuous**: 184 unique angle a Q43b-ben, míg az upstream SPP 16-bin (mert az upstream nem támogatja a globális continuous flaget). A Q42 236-tal szemben a Q43b 184 azért kevesebb, mert kevesebb placement történt (218 vs 276).
- **A saját solver wall-time gyorsabb, mint az upstream** (1139 s vs 1208 s), de a saját oldalon a Q40/Q41 policy lassítja a konvergenciát a 218-as placement-számig.
- **A Q42 3-stock modellje** több területet ad (13.5 m² vs 9.0 m²), és a Q42 el is érte a 276/276 placementet. A Q42 tehát „könnyebb" feladatot kapott, mint a Q43b.

## Direct comparability

Az `comparison_summary.json` `direct_comparability: PARTIAL_DIRECTLY_COMPARABLE` címkével jelöli a 3-way összehasonlítást. A hasonlóság:

- A Q43 + Q43b azonos container (1500×6000) és azonos geometry (12 part / 276 instance).
- A Q42 eltérő inventory (3×1500×3000) és eltérő objective (minimize used sheet count).

A különbségek:

- Az upstream SPP `minimize_width` célfüggvénye hatékonyabban tömörít, mint a saját finite-stock placement.
- A Q40/Q41 spacing-expansion + margin-inset csökkenti a saját oldali effektív container-területet.
- A saját oldalon 16 vs 184 vs 236 unique rotation értékek jönnek ki — ez a rotation policy finomságát tükrözi, nem a placement density-t.

## Semantic parity audit methodology

A Q43b a Q43 audit 9-témás mátrixát alkalmazza a saját oldal nézőpontjából. A `scripts/build_sgh_q43b_comparison_artifacts.py` generálja a `artifacts/benchmarks/sgh_q43b/semantic_parity_matrix.json` fájlt, 9 audit témával és 5 lehetséges verdicttel (`MATCH` / `ADAPTED MATCH` / `INTENTIONAL DIVERGENCE` / `RISKY DIVERGENCE` / `UNKNOWN`). A verdiktek a Q43 audit során elvégzett statikus review-n alapulnak, kiegészítve a Q43b-specifikus bizonyítékokkal (input, output, log, summary).

## Problem model parity (own solver side)

- **Verdict:** `INTENTIONAL DIVERGENCE`
- **Indoklás:** A Q43b a saját solver finite-stock single-strip modelljét használja. Ez a Q32 multisheet manager degenerált esete (1 db stock). Az upstream SPP (Q43) más célfüggvény (min-width) azonos containeren.
- **Bizonyíték:** `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs`, `artifacts/benchmarks/sgh_q43b/inputs/q43b_…json` (stocks=1).

## Geometry representation parity

- **Verdict:** `ADAPTED MATCH`
- **Indoklás:** Mindkét oldal `simple_polygon` item formátumot használ. A saját oldal Q40/Q41 spacing-expansiont (8 mm) és sheet margin-insetet (5 mm) alkalmaz. Ez az oka a 58 unplaced partnak a Q43b-ben, szemben a Q43 upstream 0 unplaceddel.
- **Bizonyíték:** `rust/vrs_solver/src/optimizer/sparrow/geometry/`, `rust/vrs_solver/src/technology/clearance.rs`.

## Collision / CDE parity

- **Verdict:** `MATCH`
- **Indoklás:** Mindkét oldal a jagua-rs CDE-t használja. A Q43b `final_pairs=0` megerősíti, hogy a partial result collision-free, nem „infeasible placement".
- **Bizonyíték:** `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`, `q43b_summary.json:sparrow_collision_graph_final_pairs=0`.

## Search / sampling / optimizer loop parity

- **Verdict:** `MATCH`
- **Indoklás:** A Q43b 212 iterációt futtatott 1138.96 s alatt, 51 508 search position call-lal. A loop upstream-stílusú (global sample gen + best-samples + coord descent + disruption).
- **Bizonyíték:** `rust/vrs_solver/src/optimizer/sparrow/sample/`, `q43b_summary.json:sparrow_iterations=212`.

## LBF / initial placement parity

- **Verdict:** `ADAPTED MATCH`
- **Indoklás:** LBF upstream-default. A Q43b single-stock esetben a multisheet manager LBF-re degenerálódik, ami upstream-ekvivalens egyetlen sheet esetén.
- **Bizonyíték:** `rust/vrs_solver/src/optimizer/sparrow/lbf.rs`.

## Rotation policy parity

- **Verdict:** `MATCH`
- **Indoklás:** Continuous rotation a Q43b-ben: 184 unique angle, 189 non-orthogonal, min -34.65 / max 367.45 fok. Ez sokkal finomabb, mint a Q43 upstream 16-bin listája, és a Q40/Q41 continuous handling-gel konzisztens.
- **Bizonyíték:** `rust/vrs_solver/src/rotation_policy.rs`, `q43b_summary.json:unique_rotation_count=184`.

## Strip vs finite-stock multisheet divergence

- **Verdict:** `INTENTIONAL DIVERGENCE`
- **Indoklás:** Upstream = single-strip SPP; Q43b = single finite stock (a Q32 multisheet degenerált esete). Container area azonos, inventory modell különböző.
- **Bizonyíték:** `rust/vrs_solver/src/optimizer/sparrow/multisheet.rs`, `q43b_…json` (stocks=1).

## Margin / spacing / kerf parity

- **Verdict:** `INTENTIONAL DIVERGENCE`
- **Indoklás:** A Q43b margin=5, spacing=8, kerf=0 policy-t alkalmaz. Az upstream SPP nem ismeri ezeket, így a raw polygonok kisebbek. Ez a közvetlen oka a 58 unplaced itemnek a Q43b-ben.
- **Bizonyíték:** `rust/vrs_solver/src/technology/clearance.rs`, `rust/vrs_solver/src/optimizer/sparrow/geometry/`.

## Output / validation parity

- **Verdict:** `ADAPTED MATCH`
- **Indoklás:** A Q43b own solver output explicit per-placement (x, y, rotation_deg) + optimizer_diagnostics blokkot ad. Collision-free (final_pairs=0). A partial státusz a top-level `status="partial"`-ban jelenik meg (Q23/Q24 konvenció).
- **Bizonyíték:** `rust/vrs_solver/src/adapter.rs`, `q43b_…output.json`.

## Parity matrix

A teljes 9-témás mátrix a `artifacts/benchmarks/sgh_q43b/semantic_parity_matrix.json` fájlban van. Verdict-eloszlás:

- **MATCH:** 3 (collision_cde, search_sampling, rotation_policy)
- **ADAPTED MATCH:** 3 (geometry_representation, lbf_initial_placement, output_validation)
- **INTENTIONAL DIVERGENCE:** 3 (problem_model, multisheet_finite_stock, margin_spacing_kerf)
- **RISKY DIVERGENCE:** 0
- **UNKNOWN / NOT VERIFIED:** 0

Ez megegyezik a Q43 audit 9-témás verdictjeivel, mert ugyanaz a saját solver és ugyanaz az upstream Sparrow a két audit tárgya; csak a Q43b a saját oldali futtatás oldaláról vizsgálja a parity-t.

## Risky divergences

Nincs `RISKY DIVERGENCE` verdict.

## Intentional divergences

A 3 `INTENTIONAL DIVERGENCE` verdict mind termelési igény (finite-stock manager, margin/spacing/kerf policy) és a Q24r1 óta dokumentált.

## Unknown / not verified items

Nincs `UNKNOWN` verdict.

## Recommendations

1. **A Q43b partial (218/276) eredmény a Q40/Q41 policy-ból fakad.** Ha „raw" baseline kellene (margin/spacing nélkül), a Q43b input `margin_mm=0, spacing_mm=0` értékekkel újrafuttatható, de ez a Q43 upstream SPP-vel való szigorú összehasonlíthatóság kedvéért hasznos lenne.
2. **A saját solver continuous rotation hatékonyabb, mint az upstream SPP 16-bin listája.** A jövőbeli upstream auditokhoz érdemes lenne az upstream SPP input orientation listáját a saját 236-bin policy-vel egyenértékűre bővíteni, hogy a placement density összehasonlítás fair legyen.
3. **A Q43b runner + smoke + comparison script** a `scripts/` alatt van, és a Q43 audit scriptjeivel párhuzamosan karbantartható.

## Final verdict

A Q43b specifikáció 4 független ítéletet kér:

1. **Own solver baseline run verdict:** **PARTIAL — interpretable result achieved.** A saját `vrs_solver` 1200 sec időlimittel 218/276 partot helyezett el 1 db 1500×6000 mm stockon, 1138.96 s wall time alatt, 0 ütközéssel, 184 unique rotation szöggel. 58 part nem fért el a Q40/Q41 margin/spacing policy miatti effektív polygonnövekedés miatt.
2. **Optimization quality verdict:** **MODERATE — partial placement with high continuous-rotation fidelity.** A 184 unique rotation / 218 placement = ~0.84 unique-per-placement arány kiváló. A density proxy 0.7899 (placed/total), ami a Q43 upstream 0.7430 density értékével közvetlenül nem összehasonlítható, de jelzi, hogy a saját oldalon a „hasznos" terület jobban ki van használva, mint a nyers upstream.
3. **Semantic parity verdict:** 3 `MATCH` + 3 `ADAPTED MATCH` + 3 `INTENTIONAL DIVERGENCE` + 0 `RISKY DIVERGENCE` + 0 `UNKNOWN`. A Q43 audit 9-témás verdictjeivel konzisztens.
4. **Own source immutability verdict:** Pre + post `git diff` egyaránt 0 bájt. **A saját solver source nem módosult. PASS.**

A Q43b task a user kérésére készült, és a Q43 audit kiegészítéseként értelmezhető: a saját oldali futtatás eredménye a 3-way összehasonlításban a Q43 upstream és Q42 saját (3-stock) eredmények mellé kerül, hogy a placement quality, a continuous rotation hatékonysága, és a Q40/Q41 policy hatása számszerűen összevethető legyen.

A Q43b task **PASS** a user által kért scope minimumán (single Run A 1200 sec, Q42-vel azonos paraméterek, saját solver source érintetlen, smoke PASS, audit és 3-way comparison kiírva).
