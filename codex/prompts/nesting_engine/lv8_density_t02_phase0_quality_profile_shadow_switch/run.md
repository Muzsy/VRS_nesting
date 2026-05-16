# LV8 Density T02 — Phase 0 quality profile shadow switch
TASK_SLUG: lv8_density_t02_phase0_quality_profile_shadow_switch

## Szerep

Senior Python/config és repo-contract agent vagy. A feladatod a Phase 0 shadow run profile-előkészítése a valós repó alapján. Ez nem algoritmusfejlesztés és nem hard-cut.

## Cél

Készítsd elő a no-SA shadow profile párokat a későbbi T06 shadow runhoz:

1. `quality_default` és `quality_aggressive` maradjon T02 végén SA-alapú.
2. Jöjjön létre `quality_default_no_sa_shadow` és `quality_aggressive_no_sa_shadow`.
3. Legyen gépileg olvasható shadow pair mapping.
4. Legyen `tmp/lv8_density_phase0_shadow_profile_matrix.json` és `.md`.
5. Frissüljenek a szükséges smoke tesztek.
6. Készüljön T02 checklist és report.

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
10. `canvases/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
11. `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t02_phase0_quality_profile_shadow_switch.yaml`

Ha bármelyik kötelező szabályfájl hiányzik, állj meg, és a reportban FAIL/BLOCKED státuszként rögzítsd.

## Engedélyezett módosítások

Csak ezek a fájlok hozhatók létre vagy módosíthatók:

- `vrs_nesting/config/nesting_quality_profiles.py`
- `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`
- `tmp/lv8_density_phase0_shadow_profile_matrix.json`
- `tmp/lv8_density_phase0_shadow_profile_matrix.md`
- `codex/codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
- `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
- `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log`

## Szigorú tiltások

- Tilos `quality_default` vagy `quality_aggressive` profilt T02-ben `search=none`-ra átírni.
- Tilos a `DEFAULT_QUALITY_PROFILE` értékét megváltoztatni.
- Tilos `search/sa.rs`-t módosítani vagy törölni.
- Tilos `quality_cavity_prepack*` profilokat törölni.
- Tilos hosszú LV8 benchmarkot futtatni.
- Tilos polygon-aware validátort implementálni.
- Tilos Phase 2+ scoring/lookahead/beam/LNS funkciót implementálni.
- Tilos a végleges fejlesztési terv tartalmát megváltoztatni.
- Tilos nem engedélyezett production fájlt módosítani.

## Előfeltétel ellenőrzés

```bash
ls AGENTS.md || echo "STOP: AGENTS.md missing"
ls docs/codex/yaml_schema.md || echo "STOP: yaml schema missing"
ls docs/codex/report_standard.md || echo "STOP: report standard missing"
ls canvases/nesting_engine/lv8_density_task_index.md || echo "STOP: T00 task index missing"
ls codex/prompts/nesting_engine/lv8_density_master_runner.md || echo "STOP: master runner missing"
ls codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md || echo "STOP: T01 report missing"
ls canvases/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md || echo "STOP: T02 canvas missing"
ls codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t02_phase0_quality_profile_shadow_switch.yaml || echo "STOP: T02 YAML missing"
```

Ellenőrizd a T01 státuszát:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md')
text = p.read_text(encoding='utf-8')
head = text[:800]
assert '**Státusz:** PASS' in head or '**Státusz:** PASS_WITH_NOTES' in head, 'T01 is not PASS/PASS_WITH_NOTES'
print('T02 prerequisite T01 status PASS')
PY
```

## Kiinduló profile audit

```bash
python3 - <<'PY'
from vrs_nesting.config.nesting_quality_profiles import (
    VALID_QUALITY_PROFILE_NAMES,
    build_nesting_engine_cli_args_for_quality_profile,
    get_quality_profile_registry,
    runtime_policy_for_quality_profile,
)

print('VALID_QUALITY_PROFILE_NAMES=', VALID_QUALITY_PROFILE_NAMES)
for name in ['quality_default', 'quality_aggressive', 'quality_cavity_prepack', 'quality_cavity_prepack_cgal_reference']:
    policy = runtime_policy_for_quality_profile(name)
    args = build_nesting_engine_cli_args_for_quality_profile(name)
    print(name, policy, args)
PY
```

Rögzítsd az eredményt a reportban.

## Implementációs utasítás

### 1) Registry bővítése

A `vrs_nesting/config/nesting_quality_profiles.py` fájlban add hozzá:

```python
"quality_default_no_sa_shadow": {
    "placer": "nfp",
    "search": "none",
    "part_in_part": "auto",
    "compaction": "slide",
},
"quality_aggressive_no_sa_shadow": {
    "placer": "nfp",
    "search": "none",
    "part_in_part": "auto",
    "compaction": "slide",
},
```

Ne adj hozzá `sa_iters`, `sa_eval_budget_sec` vagy bármilyen `sa_*` mezőt no-SA profilhoz.

### 2) Shadow pair mapping

Adj hozzá gépileg olvasható mappinget. Javasolt:

```python
PHASE0_SHADOW_PROFILE_PAIRS: dict[str, str] = {
    "quality_default": "quality_default_no_sa_shadow",
    "quality_aggressive": "quality_aggressive_no_sa_shadow",
}


def get_phase0_shadow_profile_pairs() -> dict[str, str]:
    return dict(PHASE0_SHADOW_PROFILE_PAIRS)
```

Tedd be az `__all__` listába, ha a modul export-konvenciója ezt kívánja.

### 3) Smoke test frissítés

Frissítsd a szükséges smoke teszteket:

- `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
  - ne várjon fix 3 profilos listát, ha a registry már több profilt tartalmaz;
  - ellenőrizze explicit módon az eredeti három alap profilt;
  - ellenőrizze explicit módon a két új shadow profilt;
  - plan-only expected count számításnál ne hardcode-olja a 3-at, hanem a registryből jövő profilok számát használja, vagy explicit tartalmazza a shadow profilokat.
- `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`
  - csak akkor módosítsd, ha a registry-bővítés miatt szükséges;
  - továbbra is ellenőrizze, hogy `quality_default.search == "sa"` T02 végén.

## Shadow matrix artefakt előállítása

Hozd létre `tmp/lv8_density_phase0_shadow_profile_matrix.json` és `.md` fájlokat. A JSON-t a registryből generáld, ne kézzel gépeld a CLI args-okat.

Használható minta:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from vrs_nesting.config.nesting_quality_profiles import (
    build_nesting_engine_cli_args_for_quality_profile,
    get_phase0_shadow_profile_pairs,
    runtime_policy_for_quality_profile,
)

pairs = []
for legacy, shadow in get_phase0_shadow_profile_pairs().items():
    pairs.append({
        'legacy_profile': legacy,
        'shadow_profile': shadow,
        'legacy_search': runtime_policy_for_quality_profile(legacy)['search'],
        'shadow_search': runtime_policy_for_quality_profile(shadow)['search'],
        'legacy_cli_args': build_nesting_engine_cli_args_for_quality_profile(legacy),
        'shadow_cli_args': build_nesting_engine_cli_args_for_quality_profile(shadow),
    })

data = {
    'task_slug': 'lv8_density_t02_phase0_quality_profile_shadow_switch',
    'source_inventory_report': 'codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md',
    'pairs': pairs,
    'hard_cut_allowed_in_t02': False,
    'recommended_next_step': 'T03/T04/T05 in parallel, then T06 shadow run baseline',
}
Path('tmp').mkdir(exist_ok=True)
Path('tmp/lv8_density_phase0_shadow_profile_matrix.json').write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')

lines = ['# LV8 Density Phase 0 shadow profile matrix', '']
for item in pairs:
    lines.append(f"- `{item['legacy_profile']}` ({item['legacy_search']}) → `{item['shadow_profile']}` ({item['shadow_search']})")
    lines.append(f"  - shadow CLI: `{' '.join(item['shadow_cli_args'])}`")
lines.append('')
lines.append('Hard-cut allowed in T02: false. T06 owns the measured decision.')
Path('tmp/lv8_density_phase0_shadow_profile_matrix.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('wrote T02 shadow matrix')
PY
```

## Sanity checkek

### Profile sanity

```bash
python3 - <<'PY'
from vrs_nesting.config.nesting_quality_profiles import (
    build_nesting_engine_cli_args_for_quality_profile,
    get_quality_profile_registry,
    runtime_policy_for_quality_profile,
)

registry = get_quality_profile_registry()
for name in [
    "quality_default",
    "quality_aggressive",
    "quality_default_no_sa_shadow",
    "quality_aggressive_no_sa_shadow",
]:
    assert name in registry, f"missing profile: {name}"

assert runtime_policy_for_quality_profile("quality_default")["search"] == "sa"
assert runtime_policy_for_quality_profile("quality_aggressive")["search"] == "sa"
assert runtime_policy_for_quality_profile("quality_default_no_sa_shadow")["search"] == "none"
assert runtime_policy_for_quality_profile("quality_aggressive_no_sa_shadow")["search"] == "none"

for name in ["quality_default_no_sa_shadow", "quality_aggressive_no_sa_shadow"]:
    args = build_nesting_engine_cli_args_for_quality_profile(name)
    joined = " ".join(args)
    assert "--search none" in joined, (name, args)
    assert "--sa-" not in joined, (name, args)

print("T02 profile sanity PASS")
PY
```

### Shadow matrix sanity

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path('tmp/lv8_density_phase0_shadow_profile_matrix.json')
assert p.exists(), 'shadow profile matrix missing'
data = json.loads(p.read_text())
pairs = {(x['legacy_profile'], x['shadow_profile']) for x in data.get('pairs', [])}
assert ('quality_default', 'quality_default_no_sa_shadow') in pairs
assert ('quality_aggressive', 'quality_aggressive_no_sa_shadow') in pairs
assert data.get('hard_cut_allowed_in_t02') is False
print('T02 shadow matrix sanity PASS')
PY
```

### Python syntax és célzott smoke

```bash
python3 -m py_compile vrs_nesting/config/nesting_quality_profiles.py
python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py
```

Ha `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py` módosult, futtasd azt is:

```bash
python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py
```

### Production diff guard

```bash
python3 - <<'PY'
import subprocess
allowed = {
    'vrs_nesting/config/nesting_quality_profiles.py',
    'scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py',
    'scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py',
}
proc = subprocess.run(['git', 'diff', '--name-only', 'HEAD'], text=True, capture_output=True, check=False)
changed = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
production = {p for p in changed if p.endswith(('.rs', '.py', '.ts', '.tsx')) and not p.startswith(('codex/', 'canvases/')) and not p.startswith('tmp/')}
extra = production - allowed
assert not extra, f'unexpected production diffs: {sorted(extra)}'
print('T02 production diff guard PASS')
PY
```

## Checklist és report

Hozd létre:

- `codex/codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
- `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`

A report a `docs/codex/report_standard.md` struktúráját kövesse. A DoD → Evidence Matrix a canvas Definition of Done pontjait 1:1-ben tartalmazza.

## Repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md
```

Ha a verify piros, a report legyen FAIL, kivéve ha minden T02 DoD teljesült és a hiba bizonyítottan pre-existing / környezeti. Ilyenkor PASS_WITH_NOTES megengedett, de csak részletes indoklással.

## Végső elvárt állapot

A T02 akkor kész, ha T06 már pontosan tudja:

- melyik régi SA profile-t melyik no-SA shadow profile-lal kell párban mérni;
- a no-SA shadow profilok CLI argjai mik;
- T02-ben nem történt hard-cut;
- a registry és smoke tesztek zöldek;
- a shadow matrix JSON gépileg olvasható és a reportban hivatkozott.
