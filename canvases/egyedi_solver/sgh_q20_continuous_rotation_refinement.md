# SGH-Q20 — Continuous rotation refinement v1

## Context

Q16 és Q18A/R1 után a CDE final commit gate és az observability útvonal már auditálható. A következő feladat már minőségtermelő solver-munka, nem újabb hygiene/report javítás.

A jelenlegi `RotationPolicy::Continuous` nem valódi minőségi continuous rotation stratégia. A Q07/Q18A állapotban főleg előre feloldott, véges angle-listát ad a solvernek, amely canonical szögeket és kevés seedelt mintát tartalmaz. Ez önmagában kevés egy jagua_rs/Sparrow irányú solverhez, mert:

- nem garantálja a hasznos 22.5°/45°/67.5° jellegű minták jelenlétét;
- nincs lokális rotációs finomítás az aktuális incumbent körül;
- a compression phase csak a már feloldott rotációs listán iterál;
- a minőségi döntés még túl könnyen beragad a kezdeti coarse sample halmazba.

Q20 célja: a `continuous` policy legyen ténylegesen használható production irányú rotációs keresési alap, backend-aware commit gate mellett.

## Scope

Implementálj egy determinisztikus, auditálható **continuous rotation refinement v1** réteget.

Ez nem Q19 benchmark gate, nem CDE session/cache rewrite, és nem Q21 full geometry-aware loss rewrite.

### Kötelező részek

#### 1. Sparrow-szerű coarse continuous candidate alap

A `RotationPolicyKind::Continuous` ne csak canonical + néhány seedelt random szög legyen.

Minimum elvárás:

- deterministic uniform/coarse angle set `[0, 360)` tartományban;
- default continuous sample count legalább 16 vagy repo-configból indokolva;
- canonical `0/90/180/270` maradjon benne;
- hasznos diagonális minták, például 45° és/vagy 22.5° alapból elérhetők legyenek, ha a sample count ezt indokolja;
- dedupe és normalizáció stabil maradjon;
- legacy `allowed_rotations_deg` precedence ne sérüljön.

Fontos: ha a repo korábbi Q07 tesztje seedelt continuous variációt vár, akkor ne törd el vakon. Válassz olyan megoldást, amely determinisztikus és dokumentált: például uniform base + seedelt jitter/extra minták, vagy külön helper a refinement fázishoz. A cél nem a véletlenesség, hanem a minőségi és reprodukálható lefedés.

#### 2. Local rotation refinement / wiggle candidates

Adj hozzá lokális rotációs finomítást az aktuális placement szöge körül, csak ott, ahol az effective policy `Continuous`.

Minimum elvárás:

- aktuális rotation körüli szimmetrikus offsetek, például `±15°, ±7.5°, ±3°, ±1.5°, ±0.75°` vagy repo-konfigurált megfelelőjük;
- normalizált, deduplikált candidate lista;
- maximált candidate szám, hogy ne robbanjon a futás;
- deterministic sorrend/tie-break;
- `Locked`, `HalfTurn`, `Orthogonal`, `FortyFive`, `Discrete` policy esetén ne keletkezzen unsupported extra szög.

#### 3. Compression phase wiring

A `CompressionPhase` jelenleg a resolved rotation listán megy végig. Bővítsd úgy, hogy Continuous policy esetén a lokális refinement candidate-eket is kipróbálja.

Kötelező invariánsok:

- csak score-javító candidate commitolható;
- commit előtt `validate_placements_for_backend(...)` vagy azzal egyenértékű backend-aware gate fusson;
- CDE/Jagua exact esetén nincs bbox fallback;
- rollback-safe maradjon: rossz rotation/refinement candidate nem ronthatja el az incumbent layoutot;
- output determinisztikus marad azonos seed mellett.

#### 4. Optional but recommended: fit-rescue angle coverage

Ha az aktuális architecture engedi, adj célzott tesztet vagy implementációt olyan esetre, ahol egy rectangle orthogonally nem fér, de diagonális continuous szöggel igen.

Példa gondolat:

- stock: kb. `90 x 90`;
- part: kb. `100 x 20`;
- orthogonal `0/90` nem fér;
- 45° körül már férhet a rotated bbox.

Nem kell ezt LV8 benchmarkká alakítani. Ez csak bizonyíték arra, hogy Q20 ténylegesen új quality capability-t ad.

#### 5. Diagnostics

Adj minimális diagnosztikát a PhaseOptimizer/OptimizerDiagnostics útvonalon.

Javasolt mezők:

```text
rotation_refinement_attempts
rotation_refinement_accepts
rotation_refinement_rejections
rotation_refinement_best_delta
rotation_refinement_enabled
```

A pontos nevek igazodhatnak a repo stílusához, de a reportból egyértelműen derüljön ki:

- futott-e refinement;
- hány candidate-et próbált;
- hányat fogadott el;
- javított-e score-on;
- backend gate volt-e a commit előtt.

A wall-clock timing továbbra is csak Q18A/R1 szabály szerint jelenjen meg env alatt.

## Explicit non-goals

- Ne csinálj Q19 realistic LV8 benchmark gate-et.
- Ne csinálj CDE session/cache rewrite-ot.
- Ne írd át teljesen a score/loss modellt Q21 módjára.
- Ne tedd vissza a bbox-ot production quality alapnak.
- Ne engedj unsupported rotationt Discrete/Locked/HalfTurn/Orthogonal/FortyFive policy mellett.
- Ne kezeld a main solvert hole-aware módon; a Q15 hole-free prepack szerződés marad.

## Acceptance criteria

PASS csak akkor adható, ha mind igaz:

1. `Continuous` policy alatt coarse candidate coverage erősebb, deterministic, és tartalmaz hasznos diagonális mintákat.
2. Local rotation refinement candidate-ek futnak legalább a compression phase-ben.
3. Refinement candidate commit csak backend-aware validáció után történik.
4. CDE alatt `bbox_fallback_queries == 0` invariáns sértetlen.
5. Default determinism nem sérül.
6. Discrete/Orthogonal/FortyFive/Locked policy alatt nincs jogosulatlan extra angle.
7. Van célzott unit test a candidate generationre.
8. Van célzott unit/integration test a compression/refinement wiringra.
9. Van smoke vagy report evidence phase_optimizer + continuous + CDE/Jagua exact útvonalra.
10. Report tartalmazza: módosított fájlok, futtatott parancsok, teszteredmények, regressziós kockázatok, és explicit `SGH-Q20_STATUS: READY_FOR_AUDIT` vagy `REVISE`.

## Suggested files to audit/modify

```text
rust/vrs_solver/src/rotation_policy.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
scripts/smoke_sgh_q18a_cde_observability.py
scripts/smoke_sgh_q20_continuous_rotation_refinement.py  # új, ha hasznos
```

## Verification commands

Minimum:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q18a_cde_observability.py
python3 scripts/smoke_sgh_q20_continuous_rotation_refinement.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q20_continuous_rotation_refinement.md
```

Ha a Q20 smoke script nem készül el, a reportban indokold, de helyette legyen legalább egy cargo integration test, amely bizonyítja a continuous refinement útvonalat.

## Report markers

A report első sora legyen pontosan egyik:

```text
PASS
REVISE
BLOCKED
```

PASS esetén kötelező markerek:

```text
SGH-Q20_STATUS: READY_FOR_AUDIT
SGH-Q21_STATUS: READY|HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

Q19 maradjon HOLD, mert benchmark gate-ként csak Q20/Q21 után érdemes.
