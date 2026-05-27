# SGH-Q18A — CDE correctness/runtime observability

## Státusz

Következő kötelező task az SGH-Q16 után.

Q16 megjavította a CDE final commit gate-et: explicit `collision_backend = "cde"` esetén a végső `WorkingLayout` commit már nem blanket `CDE_BACKEND_UNSUPPORTED`, hanem a valós `CdeCollisionBackend` útvonalon validál.

Q18A célja nem új solver-minőség és nem CDE cache/session rewrite. Q18A célja, hogy bizonyítható, mérhető és auditálható legyen, hogy a CDE hol, hányszor, milyen eredménnyel és milyen költséggel fut.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q18_STATUS: READY
```

Ha ez nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell?

Most már lehet CDE-vel final commitot csinálni, de még nem tudjuk elég pontosan:

```text
- hányszor hívódik meg a CDE backend egy solver futásban,
- ebből mennyi pair query és boundary query,
- hány CDEngine/per-call adapter build történik,
- hány unsupported query van,
- van-e bármilyen bbox fallback CDE final commit alatt,
- a final commit tényleg CDE-vel történt-e,
- a CDE útvonal csak részútvonalon fut-e, vagy végső acceptance backendként is,
- melyik fázis / validation lépés viszi el a költséget,
- érdemes-e Q18B-ben CDE session/cache réteget építeni.
```

Q18A tehát mérési és átláthatósági task. A Q18B-ről ne dönts előre. A report végén evidencia alapján adj döntést: kell-e session/cache task, vagy inkább mehetünk tovább a minőségtermelő solver munkákra.

## Cél

Q18A konkrét céljai:

1. CDE query-count observability bevezetése.
2. CDE final commit backend bizonyítása output diagnosztikával.
3. CDE unsupported/fallback diagnosztika egyértelművé tétele.
4. CDE per-call adapter build count mérése.
5. CDE runtime/per-phase mérés úgy, hogy a normál solver output determinisztikáját ne rontsuk el.
6. CDE valid és invalid fixture-ökön célzott smoke/teszt evidencia.
7. Reportban döntés-előkészítés Q18B-ről.

## Nagyon fontos determinisztikai szabály

Ne tegyél wall-clock runtime értékeket alapértelmezett `SolverOutput` JSON-ba úgy, hogy az megtörje a byte-identical determinism smoke-okat.

Elfogadott megoldások:

```text
- determinisztikus számlálók mehetnek a normál JSON-ba;
- runtime/timing mezők csak explicit env/diagnostics módban jelenhetnek meg;
- vagy runtime/timing csak külön smoke/report logban szerepelhet;
- meglévő determinism tesztek nem regresszálhatnak.
```

A query count determinisztikus, a wall-clock time nem az.

## Nem cél

Ne csináld most:

```text
CDE session/cache performance rewrite
CDE default backend bekapcsolása
hole-aware CDE collision a main solverben
Q19 realistic LV8 quality benchmark gate
Q20 continuous rotation refinement
Q21 geometry-aware loss rewrite
bbox fallback visszahozása CDE alá
legacy bbox production irányként kezelése
```

## Implementációs irány

### 1. Dependency és pre-audit

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
canvases/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q18a_cde_correctness_runtime_observability.yaml
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
```

Futtasd és reportold:

```bash
rg -n "CdeCollisionBackend|CdeAdapter::with_defaults|CDEngine::new|validate_and_commit_with_backend|validate_placements_with_backend_checked|score_with_backend|collision_backend_diagnostics|OptimizerDiagnosticsOutput|PhaseDiagnostics" rust/vrs_solver/src
```

Válaszold meg a reportban:

```text
- Hol épül CDEngine jelenleg?
- Melyik útvonalakon hívódik CDE scoring/separator/validation alatt?
- Hol van final commit CDE bizonyíték Q16 után?
- Milyen diagnosztika hiányzik még a döntéshez?
```

### 2. CDE runtime/query counters

Vezess be CDE observability réteget úgy, hogy ne legyen globális parallel-test versenyhelyzet.

Preferált irány:

```text
thread-local vagy explicit solve-scoped counter, nem process-global flaky mutable state.
```

Mérendő minimum:

```text
cde_pair_queries
cde_boundary_queries
cde_total_queries
cde_engine_builds
cde_collision_results
cde_no_collision_results
cde_unsupported_results
cde_prepare_failures
cde_cross_sheet_skipped_queries vagy hasonló, ha releváns
```

A számlálók fedjék le legalább a `CdeCollisionBackend::placement_overlaps` és `CdeCollisionBackend::placement_within_sheet` hívásokat.

Ha runtime timingot is kódból mérsz, az legyen explicit diagnostics módban. Ne törje meg az alapértelmezett determinisztikus outputot.

### 3. Output diagnosztika

Bővítsd az output diagnosztikát backward-compatible módon.

A meglévő mezők maradjanak:

```text
collision_backend_diagnostics.backend_used
collision_backend_diagnostics.unsupported_queries
collision_backend_diagnostics.bbox_fallback_queries
```

A Q16-kompatibilitás nem sérülhet.

Új mezők lehetnek például:

```text
final_commit_backend_used
final_commit_unsupported_queries
final_commit_bbox_fallback_queries
cde_pair_queries
cde_boundary_queries
cde_total_queries
cde_engine_builds
cde_collision_results
cde_no_collision_results
cde_unsupported_results
cde_prepare_failures
cde_observability_scope
```

A pontos elnevezés igazodjon a repo meglévő stílusához, de a reportban dokumentáld.

Fontos: ha explicit `collision_backend = "cde"` mellett backend-unsupported történik, lehetőleg az unsupported output is tartalmazza a CDE diagnosztikát. Ha ezt nem lehet tisztán megoldani, dokumentáld miért, és adj külön tesztet/report evidence-et a hiányra.

### 4. Per-phase / per-step runtime observability

A Q18A minimuma:

```text
- final commit validation runtime mérhető legyen;
- PhaseOptimizer esetén exploration/compression/bpp/final-commit idő legalább reportban látszódjon;
- legacy multisheet + CDE esetén final commit runtime látszódjon;
- ha outputba kerül runtime, az explicit env/diagnostics módban legyen.
```

Lehetséges megoldás:

```text
VRS_CDE_OBSERVABILITY_TIMING=1
```

vagy hasonló env flag, amellyel a smoke script bekapcsolja a timing mezőket/logokat. Az alapértelmezett futás maradjon determinisztikus.

### 5. Smoke script

Készíts célzott smoke scriptet, például:

```text
scripts/smoke_sgh_q18a_cde_observability.py
```

A script fusson legalább ezekre:

1. Valid simple rect, `collision_backend = "cde"`, legacy multisheet path.
2. Valid simple rect, `collision_backend = "cde"`, `optimizer_pipeline = "phase_optimizer"`.
3. Malformed geometry, `collision_backend = "cde"` → unsupported, nem bbox fallback.
4. Bbox false-positive notch fixture, ahol CDE pair query tényleg hasznos, nem csak bbox proxy.

A script ellenőrizze:

```text
backend_used == "cde_adapter"
final_commit_backend_used == "cde_adapter" vagy dokumentált megfelelője
bbox_fallback_queries == 0
cde_total_queries > 0 valid CDE esetben
cde_engine_builds > 0 valid CDE esetben
unsupported case reason == "CDE_BACKEND_UNSUPPORTED_QUERY"
normal/default bbox path nem kap CDE runtime számlálókat
```

Ha runtime timing env módban van, a script logolja a timingokat, de ne hasonlítsa őket determinisztikus exact értékre.

### 6. Tesztek

Adj célzott Rust és/vagy Python teszteket.

Minimum elvárt tesztek:

```text
cde_observability_counts_pair_and_boundary_queries
cde_observability_reports_engine_builds
cde_observability_reports_no_bbox_fallback
adapter_cde_valid_output_contains_observability_diagnostics
adapter_cde_unsupported_output_preserves_observability_or_documents_blocker
bbox_backend_does_not_emit_cde_observability
cde_observability_does_not_break_existing_q16_tests
```

Ha a pontos tesztnevek eltérnek, a reportban mapeld őket ezekre a követelményekre.

### 7. Döntési report Q18B-ről

A report végén adj táblázatos döntést:

```text
Metric / Evidence | Result | Interpretation | Decision impact
```

A döntés legyen egyértelmű:

```text
Q18B_RECOMMENDATION: REQUIRED
```

vagy

```text
Q18B_RECOMMENDATION: NOT_REQUIRED_NOW
```

vagy

```text
Q18B_RECOMMENDATION: INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```

A `PASS` nem azt jelenti, hogy CDE gyors; azt jelenti, hogy a mérési/observability réteg megbízhatóan elkészült.

## PASS feltételek

PASS csak akkor lehet, ha:

```text
- Q16 dependency PASS és SGH-Q18_STATUS: READY megvan;
- CDE final commit továbbra is működik valid layouton;
- explicit CDE outputból bizonyítható a final commit backend;
- CDE query/call counters léteznek és teszteltek;
- CDE unsupported count/fallback count auditálható;
- bbox_fallback_queries CDE alatt 0 marad;
- timing/per-phase mérés reportolható anélkül, hogy alapértelmezett determinism sérülne;
- smoke script fut és ellenőrzi a fenti fixture-öket;
- Q16 regressziós tesztek továbbra is zöldek;
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` zöld;
- repo `verify.sh` zöld;
- report első sora PASS;
- report tartalmazza a Q18B_RECOMMENDATION döntést.
```

## Report marker

PASS report végén legyen:

```text
SGH-Q18A_STATUS: READY_FOR_AUDIT
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
