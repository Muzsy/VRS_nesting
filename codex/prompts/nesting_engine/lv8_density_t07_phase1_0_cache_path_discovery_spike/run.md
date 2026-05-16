# Runner — lv8_density_t07_phase1_0_cache_path_discovery_spike

## Feladat

Végrehajtandó task: **T07 — Phase 1.0 cache path discovery spike**.

Ez egy read-only audit / spike task. Nem új cache-t kell írni, nem kell LRU-t implementálni, nem kell Rust/Python production kódot módosítani. A cél a meglévő `NfpCache` valós használatának feltérképezése, és a T08–T10 scope pontosítása.

## Kötelező források

Olvasd el először:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/nesting_engine/lv8_density_task_index.md
codex/prompts/nesting_engine/lv8_density_master_runner.md
canvases/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t07_phase1_0_cache_path_discovery_spike.yaml
codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
```

A T06 `PASS_WITH_NOTES` és `hard_cut_decision=DEFER_HARD_CUT` nem blokkolja T07-et.

## Scope

Engedélyezett outputok:

```text
tmp/phase1_spike_cache_path_discovery.md
codex/codex_checklist/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.verify.log
```

Tilos módosítani:

```text
rust/nesting_engine/src/**
scripts/experiments/**
vrs_nesting/**
worker/**
tests/**
```

Ha production módosítás szükségesnek látszik, állj meg, és dokumentáld follow-upként T08/T09/T10 felé. T07-ben ne javítsd.

## Végrehajtási lépések

### 1) Előfeltétel ellenőrzés

Ellenőrizd:

```bash
python3 - <<'PY'
from pathlib import Path
reports = [
    'codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md',
    'codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md',
]
for r in reports:
    p = Path(r)
    print(r, 'OK' if p.is_file() else 'MISSING')
    if p.is_file():
        print('\n'.join(p.read_text(encoding='utf-8', errors='replace').splitlines()[:12]))
PY
```

Ha T06 hiányzik vagy FAIL/BLOCKED, készíts BLOCKED reportot, ne menj tovább.

### 2) Fájl inventory

Ellenőrizd:

```bash
python3 - <<'PY'
from pathlib import Path
paths = [
    'rust/nesting_engine/src/nfp/cache.rs',
    'rust/nesting_engine/src/placement/nfp_placer.rs',
    'rust/nesting_engine/src/multi_bin/greedy.rs',
    'rust/nesting_engine/src/nfp/provider.rs',
    'rust/nesting_engine/src/nfp/concave.rs',
    'rust/nesting_engine/src/nfp/cgal_reference_provider.rs',
]
for path in paths:
    print(path, 'OK' if Path(path).is_file() else 'MISSING')
PY
```

Rögzítsd az eredményt a T07 reportban.

### 3) Szimbólum scan

Futtasd:

```bash
mkdir -p tmp
grep -R "compute_nfp_lib\|compute_stable_concave_nfp\|compute_nfp_lib_with_provider\|NfpCache\|NfpCacheKey\|shape_id\|cache.get\|cache.insert" -n rust/nesting_engine/src > tmp/t07_cache_symbol_scan.txt
```

Ezután olvasd át kézzel a releváns szakaszokat, különösen:

```text
rust/nesting_engine/src/nfp/cache.rs
rust/nesting_engine/src/placement/nfp_placer.rs
rust/nesting_engine/src/multi_bin/greedy.rs
rust/nesting_engine/src/nfp/provider.rs
rust/nesting_engine/src/nfp/concave.rs
rust/nesting_engine/src/nfp/cgal_reference_provider.rs
```

A `tmp/t07_cache_symbol_scan.txt` nem kötelező output, csak munkaartefakt.

### 4) NFP call graph elkészítése

A spike reportban dokumentáld:

- mely függvények hívhatnak NFP compute-ot,
- melyik út használ `NfpCache::get` / `insert` párost,
- melyik út bypassolja a cache-t,
- melyik út inaktív vagy csak provider-végpont.

Minden állításhoz adj `file:line` hivatkozást a friss snapshotból.

### 5) Per-kernel audit

A spike reportban külön válaszolj:

```text
OldConcave path: cache-passing? where?
cgal_reference path: cache-passing? where?
reduced_convolution path, ha aktív: cache-passing?
```

Ha nem dönthető el statikusan, írd `UNPROVEN`, és adj konkrét T10 benchmark / instrumentation follow-upot.

### 6) shape_id origin audit

Vizsgáld meg:

- `shape_id()` canonicalizálása mit hash-el,
- milyen polygon jut el a `shape_id(&to_lib_polygon(...))` hívásokhoz,
- ez nominal vagy inflated geometriát jelent-e a fő placement flow-ban,
- a spacing-változás várhatóan más shape_id-t ad-e.

Ne írj T07-ben tesztet. Ha a kérdés csak teszttel bizonyítható, jelöld T09 follow-upként.

### 7) LRU vs clear_all döntési input

Dokumentáld:

- `MAX_ENTRIES` értéke,
- `clear_all()` hatása,
- jelenlegi `CacheStats` mezők,
- hit/miss reset kockázata,
- T06/T04 summaryból elérhető cache statok, ha vannak,
- kell-e most LRU, vagy elég T08-ban `clear_all_events` + `peak_entries`.

Ne implementálj LRU-t T07-ben.

### 8) pipeline_version szükségesség

Döntsd el vagy jelöld `UNPROVEN`-ként:

- előfordulhat-e, hogy két külön pipeline ugyanazt az inflated polygont adja, de eltérő NFP-szemantikát igényel,
- kell-e később `pipeline_version` mező a cache key-be.

Ha igen vagy unproven: pontos T09 follow-upot írj.

### 9) Spike report létrehozása

Hozd létre:

```text
tmp/phase1_spike_cache_path_discovery.md
```

Kötelező struktúra:

```markdown
# Phase 1.0 cache path discovery spike — output

## NFP call graph
...

## Per-kernel cache usage
...

## shape_id origin verification
...

## LRU vs clear_all decision input
...

## pipeline_version field need (audit answer)
...

## Phase 1 full audit revised estimate
...
```

### 10) T07 report és checklist

Hozd létre:

```text
codex/codex_checklist/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
```

A report tartalmazza:

- státusz: PASS / PASS_WITH_NOTES / FAIL / BLOCKED,
- előfeltétel ellenőrzés,
- rövid cache call graph kivonat,
- T08/T09/T10 handoff,
- DoD → Evidence Matrix,
- production-code-change check.

PASS_WITH_NOTES elfogadható, ha az `UNPROVEN` elemek konkrét következő taskhoz vannak kötve.

### 11) Gyors ellenőrzések

Futtasd:

```bash
cargo check -p nesting_engine
```

Majd a standard gate-et:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
```

A verify log kerüljön ide:

```text
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.verify.log
```

## Végső DoD

A T07 akkor kész, ha:

- `tmp/phase1_spike_cache_path_discovery.md` létezik és tartalmazza a 6 kötelező szekciót,
- a T07 report és checklist elkészült,
- minden NFP path kapott státuszt,
- OldConcave / cgal_reference / egyéb provider státusz dokumentált,
- shape_id origin kérdés megválaszolt vagy T09-re bontott,
- LRU vs clear_all döntési input megvan,
- pipeline_version szükségessége eldöntött vagy T09-re bontott,
- T08/T09/T10 konkrét handoff szerepel,
- production kód nem módosult,
- repo gate lefutott.
