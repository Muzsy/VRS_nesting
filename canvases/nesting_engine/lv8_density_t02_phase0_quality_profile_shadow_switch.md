# LV8 Density T02 — Phase 0 quality profile shadow switch

## 🎯 Funkció

A feladat célja a Phase 0 shadow run előkészítése a quality profile registry szintjén. A végleges LV8 packing density terv szerint a `quality_default` és `quality_aggressive` SA-alapú útvonalát össze kell hasonlítani egy `search=none` variánssal a Phase 0 shadow runban, mielőtt bármilyen hard-cut történne.

A T02 **nem futtat hosszú shadow benchmarkot** és **nem véglegesíti a hard-cutot**. A T02 csak azt biztosítja, hogy a régi SA-alapú profilok és az új no-SA shadow profilok ugyanazon registryből, determinisztikusan, mérhetően elérhetők legyenek a későbbi T06 baseline/shadow futtatáshoz.

## Forrás és döntések

A T02 a végleges `codex/reports/nesting_engine/development_plan_packing_density_20260515.md` v2.2 tervre, a T00 task indexre és a T01 fixture inventory reportra épül. A terv tartalmát nem szabad módosítani.

A T02-be beépített végleges döntések:

- A Phase 0 shadow run célja az SA-alapú és no-SA útvonal összehasonlítása.
- A hard-cut csak későbbi shadow evidence alapján történhet, nem ebben a taskban.
- A `search/sa.rs` nem törölhető.
- A `quality_cavity_prepack*` profilok nem törölhetők.
- A T02-ben létrejövő no-SA shadow profilok csak mérés-előkészítő profilok.
- A T01 report szerint a Phase 0 fixture-családok PRESENT / használhatók, de a T02 nem futtatja a hosszú benchmark-mátrixot.

## Valós repo-kiindulópontok a friss snapshot alapján

A T02 előtt a friss repo-snapshotban ellenőrzött fontos kiindulópontok:

- `vrs_nesting/config/nesting_quality_profiles.py`
  - `DEFAULT_QUALITY_PROFILE = "quality_default"`
  - `VALID_SEARCH_MODES = ("none", "sa")`
  - `quality_default.search == "sa"`
  - `quality_aggressive.search == "sa"`
  - `quality_aggressive` SA override-okat tartalmaz: `sa_iters`, `sa_eval_budget_sec`
  - `validate_runtime_policy()` tiltja az SA override mezőket, ha `search != "sa"`
- `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
  - explicit ellenőrzi a registry preseteket és több helyen a quality profile listát.
  - várhatóan frissíteni kell, ha új shadow profilok bekerülnek a registrybe.
- `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`
  - explicit ellenőrzi a `quality_default` jelenlegi SA-alapú viselkedését.
  - T02-ben ez a régi viselkedés maradjon zöld, mert nincs hard-cut.
- `scripts/experiments/lv8_2sheet_claude_search.py`
  - később, T06-ban használható a shadow runhoz, de T02-ben nem kell hosszú futtatást indítani.
- `codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md`
  - T01 PASS report; T02 ennek fixture-döntéseire hivatkozik.

## T02 scope

### T02 feladata

1. A quality profile registry kiegészítése no-SA shadow profilokkal:
   - `quality_default_no_sa_shadow`
   - `quality_aggressive_no_sa_shadow`
2. A régi profilok megtartása változatlanul:
   - `quality_default` továbbra is SA-alapú legyen T02 végén.
   - `quality_aggressive` továbbra is SA-alapú legyen T02 végén.
3. Egy gépileg olvasható Phase 0 shadow profile mapping biztosítása, például:
   - `quality_default` → `quality_default_no_sa_shadow`
   - `quality_aggressive` → `quality_aggressive_no_sa_shadow`
4. A no-SA shadow profilok CLI arg generálásának ellenőrzése:
   - `--search none`
   - nincs `--sa-*` argumentum
   - `part_in_part` és `compaction` megegyezik a régi párprofil releváns mezőivel.
5. A meglévő smoke / profile-list tesztek frissítése úgy, hogy ne törjön el az új registry-bővítéstől.
6. Shadow profile matrix artefakt létrehozása T06 számára:
   - `tmp/lv8_density_phase0_shadow_profile_matrix.json`
   - `tmp/lv8_density_phase0_shadow_profile_matrix.md`
7. T02 checklist és report létrehozása.

### T02 nem célja

- Nem futtat hosszú LV8 benchmarkot.
- Nem futtatja az 1 hetes shadow run mátrixot.
- Nem változtatja át a `quality_default` profilt `search=none`-ra.
- Nem változtatja át a `quality_aggressive` profilt `search=none`-ra.
- Nem törli a `quality_cavity_prepack*` profilokat.
- Nem törli vagy refaktorálja a `search/sa.rs` modult.
- Nem implementál polygon-aware validátort.
- Nem implementál Phase 2+ scoring / lookahead / beam / LNS funkciót.

## Létrehozandó / módosítható fájlok

A T02 futása legfeljebb ezeket a fájlokat hozhatja létre vagy módosíthatja:

- `vrs_nesting/config/nesting_quality_profiles.py`
- `scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py` — csak ha a registry-bővítés miatt szükséges, de a `quality_default` SA-viselkedését nem szabad átírni.
- `tmp/lv8_density_phase0_shadow_profile_matrix.json`
- `tmp/lv8_density_phase0_shadow_profile_matrix.md`
- `codex/codex_checklist/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
- `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md`
- `codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.verify.log`

Tilos más production vagy config fájl módosítása. Ha bármilyen további production output szükségesnek tűnik, a taskot `FAIL` vagy `STOP` státusszal kell zárni, és külön canvas szükséges.

## Kötelező shadow profil szemantika

### Régi profilok T02 végén

```python
runtime_policy_for_quality_profile("quality_default")["search"] == "sa"
runtime_policy_for_quality_profile("quality_aggressive")["search"] == "sa"
```

Ezek T02-ben változatlanok maradnak, mert a hard-cut csak T06 evidence után történhet.

### Új shadow profilok

```python
"quality_default_no_sa_shadow": {
    "placer": "nfp",
    "search": "none",
    "part_in_part": "auto",
    "compaction": "slide",
}

"quality_aggressive_no_sa_shadow": {
    "placer": "nfp",
    "search": "none",
    "part_in_part": "auto",
    "compaction": "slide",
}
```

Fontos: `quality_aggressive_no_sa_shadow` nem tartalmazhat `sa_iters`, `sa_eval_budget_sec`, vagy más `sa_*` mezőt, mert `validate_runtime_policy()` helyesen tiltja az SA override-okat `search != "sa"` esetén.

### Shadow pair helper

Javasolt, de a meglévő kódhoz igazítható formában:

```python
PHASE0_SHADOW_PROFILE_PAIRS = {
    "quality_default": "quality_default_no_sa_shadow",
    "quality_aggressive": "quality_aggressive_no_sa_shadow",
}

def get_phase0_shadow_profile_pairs() -> dict[str, str]:
    return dict(PHASE0_SHADOW_PROFILE_PAIRS)
```

Ha a repo stílusa más helper-nevet kíván, eltérhetsz, de a T06 számára legyen gépileg olvasható mapping.

## Shadow profile matrix artefakt

A `tmp/lv8_density_phase0_shadow_profile_matrix.json` legalább ezt tartalmazza:

```json
{
  "task_slug": "lv8_density_t02_phase0_quality_profile_shadow_switch",
  "source_inventory_report": "codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md",
  "pairs": [
    {
      "legacy_profile": "quality_default",
      "shadow_profile": "quality_default_no_sa_shadow",
      "legacy_search": "sa",
      "shadow_search": "none",
      "shadow_cli_args": ["--placer", "nfp", "--search", "none", "--part-in-part", "auto", "--compaction", "slide"]
    },
    {
      "legacy_profile": "quality_aggressive",
      "shadow_profile": "quality_aggressive_no_sa_shadow",
      "legacy_search": "sa",
      "shadow_search": "none",
      "shadow_cli_args": ["--placer", "nfp", "--search", "none", "--part-in-part", "auto", "--compaction", "slide"]
    }
  ],
  "hard_cut_allowed_in_t02": false,
  "recommended_next_step": "T03/T04/T05 in parallel, then T06 shadow run baseline"
}
```

A `.md` párja emberileg olvasható összefoglaló legyen.

## Minimális ellenőrzések

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

### Production diff guard

T02 várhatóan módosít production Python configot és esetleg smoke tesztet. Más production terület nem módosulhat.

```bash
python3 - <<'PY'
from pathlib import Path
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

## Rollback terv

Ha T02-t vissza kell vonni:

1. Távolítsd el a no-SA shadow profilokat és shadow pair helper-t a `vrs_nesting/config/nesting_quality_profiles.py` fájlból.
2. Állítsd vissza a smoke test módosításokat.
3. Töröld a `tmp/lv8_density_phase0_shadow_profile_matrix.*` artefaktokat.
4. Töröld a T02 checklist/report/verify log fájlokat.

A régi `quality_default`, `quality_aggressive`, `quality_cavity_prepack*` profiloknak rollback után is pontosan a T02 előtti állapotban kell maradniuk.

## Definition of Done

- [ ] Repo szabályfájlok, T00 index/master runner és T01 report elolvasva.
- [ ] `quality_default` és `quality_aggressive` T02 végén változatlanul SA-alapú.
- [ ] `quality_default_no_sa_shadow` létezik, validálható, `search=none`, nincs `sa_*` override.
- [ ] `quality_aggressive_no_sa_shadow` létezik, validálható, `search=none`, nincs `sa_*` override.
- [ ] Gépileg olvasható shadow pair mapping létezik Python helperként vagy dokumentált registry-konstansként.
- [ ] `tmp/lv8_density_phase0_shadow_profile_matrix.json` létrejött és valid JSON.
- [ ] `tmp/lv8_density_phase0_shadow_profile_matrix.md` létrejött.
- [ ] A profile-list / smoke tesztek frissítve, ha az új registry kulcsok miatt szükséges.
- [ ] Nincs hard-cut: `DEFAULT_QUALITY_PROFILE` továbbra is `quality_default`, és a régi profilok nem lettek átírva `search=none`-ra.
- [ ] `search/sa.rs` érintetlen.
- [ ] T02 checklist létrejött és ki van töltve.
- [ ] T02 report a Report Standard v2 szerint elkészült, DoD → Evidence Matrix-szal.
- [ ] T02 sanity ellenőrzések zöldek.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md` lefutott, vagy ha környezeti okból nem futott, a report FAIL/PASS_WITH_NOTES módon dokumentálja.

## Stop feltételek

A taskot `FAIL` vagy `BLOCKED` státusszal kell zárni, ha:

- A T01 report hiányzik vagy nem PASS / PASS_WITH_NOTES státuszú.
- A no-SA shadow profilok validálása csak a régi profilok hard-cut átírásával lenne megoldható.
- A `validate_runtime_policy()` átalakítása szükséges lenne az SA override mezők no-SA profilon tartásához.
- Az új shadow profilok miatt szétesik az API / UI profile-list contract, és ezt nem lehet a meglévő smoke tesztek célzott frissítésével kezelni.
- A task csak `search/sa.rs` módosításával lenne lezárható.
