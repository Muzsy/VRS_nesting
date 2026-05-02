# Cavity v2 T10 — LV8 benchmark run
TASK_SLUG: cavity_v2_t10_lv8_benchmark

## Szerep
Senior integrációs benchmark agent vagy. Elkészíted a benchmark szkriptet és futtatod az összes megelőző task eredményének end-to-end ellenőrzésére.

## Cél
`scripts/benchmark_cavity_v2_lv8.py` létrehozása. Futtatás elérhető fixture-rel. Minimum kritériumok ellenőrzése és JSON artefaktum mentése.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t10_lv8_benchmark.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t10_lv8_benchmark.yaml`
- `worker/cavity_prepack.py` (build_cavity_prepacked_engine_input_v2 API)
- `worker/cavity_validation.py` (validate_cavity_plan_v2, T08)
- `worker/result_normalizer.py`
- `vrs_nesting/config/nesting_quality_profiles.py` (build_nesting_engine_cli_args_for_quality_profile)
- T01–T09 összes artefaktum

## Fixture keresés (FUTTATANDÓ)
```bash
find . -name "*lv8*" -o -name "*LV8*" 2>/dev/null | grep -v __pycache__ | head -20
find tests/ -name "*.json" 2>/dev/null | head -20
find poc/ -name "*.json" 2>/dev/null | head -20
find scripts/ -name "benchmark*" 2>/dev/null | head -20
```

## Engedélyezett módosítás
- `scripts/benchmark_cavity_v2_lv8.py` (ÚJ fájl)
- `codex/codex_checklist/nesting_engine/cavity_v2_t10_lv8_benchmark.md` (ÚJ)
- `codex/reports/nesting_engine/cavity_v2_t10_lv8_benchmark.md` (ÚJ)

## Szigorú tiltások
- **Tilos bármely termelési kódfájlt módosítani.**
- Tilos fixture-t módosítani vagy létrehozni.
- Tilos a benchmark eredményt hamis "PASSED"-re állítani ha feltételek nem teljesülnek.
- Tilos a minimum kritériumokat gyengíteni.
- Tilos `tmp/benchmark_results/`-en kívülre írni artefaktumot.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Fixture keresés és kontextus
Futtasd a fixture kereső parancsokat. Azonosítsd a legjobb elérhető fixture-t.

### Step 2: scripts/benchmark_cavity_v2_lv8.py elkészítése
A canvas spec alapján. Kötelező mért metrikák:
- `top_level_holes_count_before_prepack` és `after_prepack`
- `guard_passed` (validate_prepack_solver_input_hole_free)
- `virtual_parent_count`, `usable_cavity_count`
- `holed_child_proxy_count`
- `quantity_delta_parts`, `quantity_mismatch_count`
- `engine_cli_args` (--part-in-part off ellenőrzés)
- `nfp_fallback_occurred`
- `validation_issues`, `overlap_count`, `bounds_violation_count`

Minimum kritérium assertion-ök:
- `holes_after == 0`
- `qty_mismatches == 0`
- `guard_ok == True`

Exit code: 0 siker, 1 failure.

### Step 3: Futtatás
```bash
python3 scripts/benchmark_cavity_v2_lv8.py
```
vagy ha szükséges:
```bash
python3 scripts/benchmark_cavity_v2_lv8.py --fixture <path>
```

Ha nincs fixture, szintaktikai ellenőrzés:
```bash
python3 scripts/benchmark_cavity_v2_lv8.py --help
```

### Step 4: Szintaktikai ellenőrzés
```bash
python3 -c "import ast; ast.parse(open('scripts/benchmark_cavity_v2_lv8.py').read()); print('OK')"
```

### Step 5: Checklist és report
### Step 6: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t10_lv8_benchmark.md
```

## Tesztelési parancsok
```bash
python3 scripts/benchmark_cavity_v2_lv8.py --help
python3 -c "import ast; ast.parse(open('scripts/benchmark_cavity_v2_lv8.py').read()); print('syntax OK')"
```

## Ellenőrzési pontok
- [ ] scripts/benchmark_cavity_v2_lv8.py létezik
- [ ] --help fut hibátlanul
- [ ] Szintaxis helyes (ast.parse)
- [ ] Ha volt futtatás: top_level_holes_after=0, qty_mismatch=0, guard_passed=True
- [ ] JSON artefaktum mentve tmp/benchmark_results/ mappába
- [ ] Exit code 0 minimum criteria PASSED esetén

## Elvárt végső jelentés
Magyar nyelvű report. Ha benchmark futott: a JSON artefaktum tartalma a reportban (minimum kritériumok teljesültek-e). Ha nem futott (nincs fixture): a keresett fixture útvonal és a szintaktikai ellenőrzés eredménye.

## Hiba esetén
Ha `build_cavity_prepacked_engine_input_v2` ImportError-t dob: ellenőrizd, hogy T06 tényleg implementálva van-e (`grep -n "build_cavity_prepacked_engine_input_v2" worker/cavity_prepack.py`). Ha fixture JSON struktúrája eltér a várt `snapshot_row` / `base_engine_input` formátumtól, adaptáld a benchmark szkriptet a valós kulcsokhoz.
