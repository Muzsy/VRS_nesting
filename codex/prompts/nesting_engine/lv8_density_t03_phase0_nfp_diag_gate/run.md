# LV8 Density T03 — Phase 0 NFP diagnostic stderr env-gate
TASK_SLUG: lv8_density_t03_phase0_nfp_diag_gate

## Szerep

Senior Rust / benchmark hygiene agent vagy. A feladatod a Phase 0 mérési higiénia egyik kis, célzott javítása: a `concave.rs` `[CONCAVE NFP DIAG]` stderr spamjének env-gate-elése. Ez nem algoritmusfejlesztés.

## Cél

A `rust/nesting_engine/src/nfp/concave.rs` közvetlen `[CONCAVE NFP DIAG]` `eprintln!` sorai default off állapotban ne írjanak stderr-t. Opt-in módban, `NESTING_ENGINE_NFP_DIAG=1` mellett a diagnosztika maradjon elérhető.

## Kötelező olvasnivaló prioritási sorrendben

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/qa/testing_guidelines.md`
6. `codex/reports/nesting_engine/development_plan_packing_density_20260515.md`
7. `canvases/nesting_engine/lv8_density_task_index.md`
8. `codex/prompts/nesting_engine/lv8_density_master_runner.md`
9. `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
10. `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
11. `canvases/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
12. `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t03_phase0_nfp_diag_gate.yaml`

Ha bármelyik kötelező szabályfájl hiányzik, állj meg, és a reportban FAIL/BLOCKED státuszként rögzítsd.

## Engedélyezett módosítások

Csak ezek a fájlok hozhatók létre vagy módosíthatók:

- `rust/nesting_engine/src/nfp/concave.rs`
- `scripts/experiments/lv8_2sheet_claude_search.py` — csak komment / marker policy pontosítás, ha indokolt.
- `codex/codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
- `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
- `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log`

Ha bármilyen további fájl módosítása szükségesnek tűnik, állj meg és írd le a reportban, miért kellene külön task vagy YAML-bővítés.

## Szigorú tiltások

- Tilos NFP algoritmust módosítani.
- Tilos cache logikát módosítani.
- Tilos `nfp_placer.rs` hot-path diag gate-jeit átírni, hacsak nem bizonyítottan szükséges és nincs más megoldás.
- Tilos `search/sa.rs`-t módosítani.
- Tilos Phase 2+ scoring/lookahead/beam/LNS funkciót implementálni.
- Tilos hosszú LV8 benchmarkot futtatni.
- Tilos a `LV8_HARNESS_QUIET` default policyt bizonyító benchmark nélkül megváltoztatni.
- Tilos a végleges fejlesztési terv tartalmát megváltoztatni.

## Előfeltétel ellenőrzés

```bash
ls AGENTS.md || echo "STOP: AGENTS.md missing"
ls docs/codex/yaml_schema.md || echo "STOP: yaml schema missing"
ls docs/codex/report_standard.md || echo "STOP: report standard missing"
ls canvases/nesting_engine/lv8_density_task_index.md || echo "STOP: T00 task index missing"
ls codex/prompts/nesting_engine/lv8_density_master_runner.md || echo "STOP: master runner missing"
ls codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md || echo "STOP: T01 report missing"
ls codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md || echo "STOP: T02 report missing"
ls canvases/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md || echo "STOP: T03 canvas missing"
ls codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t03_phase0_nfp_diag_gate.yaml || echo "STOP: T03 YAML missing"
```

Ellenőrizd a T02 státuszát:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md')
text = p.read_text(encoding='utf-8')
head = text[:1000]
assert '**Státusz:** PASS' in head or '**Státusz:** PASS_WITH_NOTES' in head, 'T02 is not PASS/PASS_WITH_NOTES'
print('T03 prerequisite T02 status PASS')
PY
```

## Kiinduló audit parancsok

```bash
grep -R "CONCAVE NFP DIAG" -n rust/nesting_engine/src/nfp/concave.rs

grep -R "NESTING_ENGINE_NFP_RUNTIME_DIAG\|NESTING_ENGINE_CFR_DIAG\|NESTING_ENGINE_CANDIDATE_DIAG\|NESTING_ENGINE_HYBRID_CFR_DIAG" -n rust/nesting_engine/src/placement/nfp_placer.rs

grep -n "stderr\|CONCAVE NFP DIAG\|LV8_HARNESS_QUIET" scripts/experiments/lv8_2sheet_claude_search.py
```

Rögzítsd az eredményt a reportban.

## Implementációs utasítás

### 1) Helper hozzáadása

A `rust/nesting_engine/src/nfp/concave.rs` fájlban adj hozzá helper függvényt:

```rust
fn is_concave_nfp_diag_enabled() -> bool {
    std::env::var("NESTING_ENGINE_NFP_DIAG").as_deref() == Ok("1")
}
```

Ha a compiler vagy style indokolja, használhatsz `#[inline]` attribútumot.

### 2) Minden CONCAVE NFP DIAG gate-elése

Minden ilyen sort gate-elj:

```rust
eprintln!("[CONCAVE NFP DIAG] ...")
```

A ciklusban lévő `partial_nfp` és `partial_nfp_done` soroknál ne olvass env-et minden iterációban; legyen lokális:

```rust
let diag_enabled = is_concave_nfp_diag_enabled();
if diag_enabled {
    eprintln!(...);
}
```

### 3) Teszt

Adj hozzá `#[cfg(test)]` unit tesztet a `concave.rs`-be, például:

- unset env → false
- `NESTING_ENGINE_NFP_DIAG=0` → false
- `NESTING_ENGINE_NFP_DIAG=1` → true

Fontos: a teszt mentse és állítsa vissza az env eredeti állapotát.

### 4) Harness policy

Auditáld `scripts/experiments/lv8_2sheet_claude_search.py` stderr kezelését. Ha módosítasz, csak komment/marker pontosítás lehet. A quiet default maradjon változatlan.

## Sanity checkek

### Grep sanity

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('rust/nesting_engine/src/nfp/concave.rs')
lines = p.read_text(encoding='utf-8').splitlines()
text = '\n'.join(lines)
assert 'fn is_concave_nfp_diag_enabled()' in text, 'missing diag helper'
assert 'NESTING_ENGINE_NFP_DIAG' in text, 'missing env flag'
for idx, line in enumerate(lines, start=1):
    if '[CONCAVE NFP DIAG]' in line:
        window = '\n'.join(lines[max(0, idx-8):idx+3])
        assert 'diag_enabled' in window or 'is_concave_nfp_diag_enabled' in window, f'ungated diag near line {idx}'
print('T03 concave diag grep PASS')
PY
```

### Rust build

```bash
cargo check -p nesting_engine
```

### Célzott teszt

A tesztnév az implementációtól függ. Példa:

```bash
cargo test -p nesting_engine concave_nfp_diag -- --nocapture
```

Ha más néven készült, a pontos parancsot rögzítsd a reportban.

### Full repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
```

## Report és checklist

Hozd létre:

- `codex/codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
- `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`

A report a Report Standard v2-t kövesse. A DoD → Evidence Matrix minden pontja legyen kitöltve.

## Definition of Done röviden

- `NESTING_ENGINE_NFP_DIAG` helper létezik.
- Minden `[CONCAVE NFP DIAG]` sor gate alatt van.
- Default off: nincs concave diag spam.
- Opt-in: `NESTING_ENGINE_NFP_DIAG=1` mellett diag elérhető.
- Nem változik algoritmus / NFP output / cache / placement döntés.
- `nfp_placer.rs` diag gate audit reportolva.
- Harness stderr policy audit reportolva.
- `cargo check -p nesting_engine` zöld.
- Célzott diag teszt zöld.
- Full `verify.sh` zöld.
