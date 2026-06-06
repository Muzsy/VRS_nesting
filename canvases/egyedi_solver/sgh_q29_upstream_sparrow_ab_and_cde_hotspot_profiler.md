# SGH-Q29 — Upstream Sparrow A/B comparison + local CDE/search hotspot profiler

## 🎯 Cél

A Q28 után nem szabad újabb vak performance patch-et írni. Először bizonyítani kell, hogy az eredeti upstream Sparrow ugyanazon vagy ekvivalens geometrián hogyan fut, utána szét kell bontani a saját `sparrow_cde` CDE/search útvonal idő- és query-költségét.

A task két kötelező fázisból áll:

1. **Phase A — valódi upstream Sparrow A/B összehasonlítás**
   - upstream forrás: `.cache/sparrow`
   - tilos saját `vrs_solver` / no-session buildet upstream referenciának nevezni
   - ha nincs valódi upstream futás, Phase A **FAIL / BLOCKED**, nem PASS

2. **Phase B — saját CDE/search hotspot profiler**
   - csak mérés és instrumentation
   - semmilyen solver-optimalizálás nem megengedett
   - cél: kideríteni, hogy a saját `native_search_placement` / CDE candidate evaluation alatt mi viszi el az időt

## Miért ez a task?

A Q28 inkrementális session reuse irány architekturálisan helyes volt, de a T04 vs no-session reference mérés nem hozott érdemi runtime javulást. Ez azt jelenti, hogy a korábbi `session build a bottleneck` hipotézis nincs bizonyítva; a következő kérdés:

```text
1. Valóban lassabb-e a saját CDE/search útvonal az upstream Sparrowhoz képest?
2. Ha igen vagy ha a saját útvonal drága, pontosan melyik rész drága?
```

Ezt a taskot ezért **mérésként**, nem tuningként kell végrehajtani.

## Nem-célok — kötelező tiltások

- Nem cél a solver optimalizálása.
- Nem cél az algoritmus, GLS, worker ordering, LBF, sampler, separator vagy exploration viselkedésének módosítása.
- Nem cél compression bevezetése.
- Nem cél LV8/full-276 benchmark-optimalizálás.
- Nem megengedett a Q28 T05 gate lazítása vagy átnevezése sikernek.
- Nem megengedett saját no-session buildet upstream Sparrow referenciának nevezni.
- Nem megengedett olyan A/B report, ahol az upstream commit/bináris/path nem szerepel.
- Nem megengedett olyan CDE profiler, amely csak wall-time-ot mér, de nem bontja fel a költséget.

## Phase A — upstream Sparrow A/B összehasonlítás

### Kötelező upstream-felderítés

A feladat elején ellenőrizd:

```bash
ls -la .cache/sparrow
git -C .cache/sparrow rev-parse HEAD
git -C .cache/sparrow status --short
find .cache/sparrow -maxdepth 3 -type f | sed -n '1,120p'
```

Majd keresd meg az upstream input példákat, CLI-t, bináris/build parancsot és output formátumot. Nem szabad feltételezni a sémát.

### Kötelező upstream build/run

- Buildeld/futtasd az upstream Sparrowt a `.cache/sparrow` forrásból.
- Rögzítsd:
  - upstream commit hash,
  - build parancs,
  - upstream bináris vagy futtatási entrypoint,
  - upstream input schema / példa forrása,
  - upstream output mezők, amikből mérsz.

Ha upstream build/run nem lehetséges, a reportban legyen:

```text
Phase A: BLOCKED
Reason: <konkrét ok>
No upstream A/B claim is made.
```

Ebben az esetben a task ne állítsa, hogy upstream parity mérve lett.

### Ekvivalens inputok

A fixed-sheet és strip-packing modell különbsége miatt nem kell bitazonos outputot várni. De az input-geometriának ekvivalensnek kell lennie.

Legalább három futási szint:

1. **micro polygon set**
   - 5–10 egyszerű polygon/rect
   - cél: schema/runner sanity

2. **medium single-sheet equivalent**
   - 20–50 instance
   - vegyes méretek, rotációk
   - cél: search/runtime összevetés

3. **LV8-derived compatible subset**
   - lehetőleg a `samples/real_work_dxf/0014-01H/lv8jav_normalized` vagy a repo JSON-fixture alapján
   - csak akkor, ha upstream formátumba korrektül konvertálható
   - ha a 191 dense fixture upstreamre nem konvertálható korrektül, ezt explicit írd le, és használj kisebb LV8-derived subsetet

A dense191 futás upstreamen opcionális, de ha lefut, külön `dense191` case-ként rögzítendő.

### A/B report kötelező mezők

Hozd létre:

```text
artifacts/benchmarks/sgh_q29/upstream_ab_summary.json
artifacts/benchmarks/sgh_q29/upstream_ab_report.md
```

A JSON minimum séma:

```json
{
  "task": "sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler",
  "phase": "upstream_ab",
  "status": "PASS|BLOCKED|FAIL",
  "upstream_sparrow": {
    "source_path": ".cache/sparrow",
    "commit": "...",
    "binary_or_entrypoint": "...",
    "build_command": "..."
  },
  "local_solver": {
    "binary": "rust/vrs_solver/target/release/vrs_solver",
    "commit_or_git_status": "..."
  },
  "cases": [
    {
      "case_id": "micro|medium|lv8_subset|dense191",
      "input_provenance": "...",
      "geometry_equivalence_notes": "...",
      "upstream": {
        "status": "ok|partial|error|unsupported",
        "runtime_ms": 0,
        "iterations": null,
        "placed_count": null,
        "collision_or_loss_metric": null
      },
      "local": {
        "status": "ok|partial|error|unsupported",
        "runtime_ms": 0,
        "iterations": null,
        "placed_count": null,
        "final_pairs": null,
        "search_calls": null,
        "search_samples": null
      }
    }
  ]
}
```

## Phase B — local CDE/search hotspot profiler

### Profiling scope

Instrumentáld a saját `sparrow_cde` útvonalat úgy, hogy a default futás szemantikája ne változzon. A profiler lehet env-flag mögött, például:

```bash
SGH_Q29_CDE_PROFILE=1
```

Mérni kell legalább:

```text
per run:
- total solver runtime ms
- total native_search_placement calls
- total candidates evaluated
- total CDE exact/batch/custom query count
- total early termination count

per native_search_placement aggregate:
- total search ms
- session build ms
- live-session deregister/reregister ms
- candidate transform / shape prepare ms
- CDE query / collect ms
- specialized CDE pipeline ms
- hazard collector / loss calculation ms
- boundary check ms
- broadphase/bbox reject count
- exact CDE collision count
- coord descent step count
- global sample count
- focused sample count
```

Ha egy fenti mező a jelenlegi architektúrában nem mérhető, a reportban `not_available` értékkel és konkrét indokkal kell szerepelnie. Nem szabad egyszerűen kihagyni.

### Érinthető Rust fájlok

A profilinghez csak mérési/instrumentation célból módosíthatók:

- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs`
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/io.rs`

Ha más Rust fájl kell, előbb frissíteni kell a YAML-t és a reportban indokolni.

### Local profiler artifactok

Hozd létre:

```text
artifacts/benchmarks/sgh_q29/local_cde_hotspot_summary.json
artifacts/benchmarks/sgh_q29/local_cde_hotspot_report.md
```

A JSON minimum séma:

```json
{
  "task": "sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler",
  "phase": "local_cde_hotspot_profiler",
  "status": "PASS|FAIL",
  "profile_flag": "SGH_Q29_CDE_PROFILE=1",
  "cases": [
    {
      "case_id": "medium|lv8_subset|dense191",
      "status": "ok|partial|error",
      "runtime_ms": 0,
      "profile": {
        "native_search_calls": 0,
        "candidates_evaluated": 0,
        "session_build_ms": 0.0,
        "deregister_reregister_ms": 0.0,
        "candidate_transform_prepare_ms": 0.0,
        "cde_query_collect_ms": 0.0,
        "specialized_pipeline_ms": 0.0,
        "hazard_loss_ms": 0.0,
        "boundary_check_ms": 0.0,
        "broadphase_reject_count": 0,
        "early_termination_count": 0
      },
      "top_costs_percent": [
        {"name": "cde_query_collect_ms", "percent": 0.0}
      ]
    }
  ]
}
```

## Acceptance criteria

A task akkor tekinthető PASS-nak, ha:

1. A report egyértelműen kimondja, volt-e valódi upstream Sparrow futás.
2. Ha volt, az upstream commit, build parancs és entrypoint rögzítve van.
3. Legalább micro + medium upstream A/B case lefutott, vagy explicit BLOCKED indok van.
4. Saját solver CDE/search profiler lefutott legalább medium + LV8-derived case-en.
5. A profiler JSON tartalmazza a kötelező költségbontási mezőket.
6. `scripts/smoke_sgh_q29_upstream_ab_and_cde_hotspot_profiler.py` PASS-t ad a létrejött artifactokra.
7. `cargo test --manifest-path rust/vrs_solver/Cargo.toml` PASS.
8. `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler.md` PASS vagy a reportban világos, reprodukálható BLOCKED státusz van csak az upstream Phase A-ra.

## Különösen fontos értelmezési szabály

A task végén tilos ilyen állítást írni:

```text
A saját solver upstream Sparrow-val össze lett hasonlítva
```

ha valójában csak saját `no-session`, `reference`, `fallback`, `T04 off` vagy más lokális build futott.

Helyes megfogalmazás:

```text
Upstream Sparrow A/B: PASS, commit <hash>, cases <...>
```

vagy:

```text
Upstream Sparrow A/B: BLOCKED, reason <...>. No upstream-runtime claim is made.
```

## Kötelező report következtetés

A végső reportban legyen külön szakasz:

```text
## Final answer to the two questions

1. Upstreamhez képest hol állunk?
2. A saját CDE/search útvonalon mi viszi el az időt?
```
