# Runner — lv8_density_t09_phase1_shape_id_cache_key_verification

## Feladat

Végrehajtandó task: **T09 — Phase 1 shape_id / spacing / kernel cache-key verification**.

Ez elsősorban Rust integration-test + audit report feladat. A cél nem cache-architektúra módosítása, hanem annak formális bizonyítása, hogy a jelenlegi `NfpCacheKey` és `shape_id()` védi a spacing/geometry változást, a kernel-választást, a rotációt, a holes tartalmat és az NFP irányát.

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
canvases/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t09_phase1_shape_id_cache_key_verification.yaml
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
```

T07 `PASS_WITH_NOTES` és T08 `PASS` elfogadható. Ha bármelyik report hiányzik vagy FAIL/BLOCKED, állj meg és írj T09 BLOCKED reportot.

## Scope

Alapesetben csak új teszt + report/checklist készül.

Engedélyezett fájlok:

```text
rust/nesting_engine/tests/nfp_cache_key_invariants.rs
codex/codex_checklist/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.verify.log
```

Csak bizonyított failing invariant esetén módosítható:

```text
rust/nesting_engine/src/nfp/cache.rs
rust/nesting_engine/src/placement/nfp_placer.rs
```

Tilos:

```text
- LRU implementáció
- cache usage benchmark
- LV8 hosszú futtatás
- CGAL binary build vagy external nfp_cgal_probe futtatás
- candidate scoring / lookahead / beam / LNS módosítás
- quality profile módosítás
- SA hard-cut vagy SA module módosítás
```

## Végrehajtási lépések

### 1) Előfeltétel ellenőrzés

```bash
python3 - <<'PY'
from pathlib import Path
for name in [
    'codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md',
    'codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md',
]:
    p = Path(name)
    print(name, 'OK' if p.is_file() else 'MISSING')
    if p.is_file():
        text = p.read_text(encoding='utf-8', errors='replace')
        print('\n'.join(text.splitlines()[:20]))
PY
```

Ha nincs elfogadható státusz, ne menj tovább implementációra.

### 2) Cache-key invariáns tesztek

Hozd létre:

```text
rust/nesting_engine/tests/nfp_cache_key_invariants.rs
```

Kötelező tesztnevek vagy azonos értelmű tesztek:

```text
shape_id_changes_when_polygon_coordinates_change
shape_id_stable_for_equivalent_polygon_boundary_external
shape_id_includes_holes
shape_id_is_stable_for_equivalent_holes
cache_key_separates_nfp_kernel
cache_key_separates_rotation_steps
cache_key_is_order_sensitive_external
```

Használj egyszerű `Polygon64` helper-eket. A „spacing-like” tesztben nem kell a teljes offset pipeline-t meghívni; egy nominal square és egy nagyobb inflated-like square koordinátaváltozása elég annak bizonyítására, hogy a shape-hash védi a spacingből adódó geometriaváltozást.

Javasolt import:

```rust
use nesting_engine::geometry::types::{Point64, Polygon64};
use nesting_engine::nfp::cache::{shape_id, NfpCache, NfpCacheKey, NfpKernel};
```

### 3) Célzott tesztfuttatás

```bash
cargo check -p nesting_engine
cargo test -p nesting_engine --test nfp_cache_key_invariants -- --nocapture
cargo test -p nesting_engine nfp::cache -- --nocapture
```

Ha minden zöld: ne módosíts production cache-key kódot.

Ha valamely invariáns bukik: javíts minimálisan `cache.rs` / `nfp_placer.rs` alatt, majd futtasd újra a fenti teszteket. A production diffet indokold a reportban.

### 4) Report és checklist

Készítsd el:

```text
codex/codex_checklist/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
```

A reportban kötelező külön szekció:

```markdown
## Cache-key decision matrix

| Invariant | Result | Evidence | Decision impact |
|---|---|---|---|
...

pipeline_version_required: YES | NO | DEFERRED
reason: ...
```

Elvárt alapdöntés: `pipeline_version_required: NO`, ha minden invariáns zöld és nincs bizonyított aliasolási bug.

### 5) Repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
```

A végén a report státusza legyen PASS vagy PASS_WITH_NOTES. FAIL/BLOCKED csak akkor elfogadható, ha konkrét blocker van dokumentálva.

## Kimeneti elvárás

A task végén röviden add meg:

```text
status: PASS | PASS_WITH_NOTES | FAIL | BLOCKED
pipeline_version_required: YES | NO | DEFERRED
production_cache_key_changed: true | false
new_tests: rust/nesting_engine/tests/nfp_cache_key_invariants.rs
verify: PASS | FAIL
next_task_recommendation: T10 indulhat / T09 follow-up kell
```
