# SGH-Q42 - Full276 LV8 continuous rotation benchmark

## Cel

Full276 LV8 benchmark futtatasa az aktualis repo allapotabol, Q41 artefaktum mintaval:

- max. 3 db 1500x3000 mm sheet;
- cel: valid nesting legfeljebb 2 sheeten;
- `margin_mm = 5.0`, `spacing_mm = 8.0`, `kerf_mm = 0.0`;
- `rotation_policy = continuous`;
- Run A: `time_limit_s = 1200`;
- Run B: `time_limit_s = 2400`, csak ha Run A nem eri el a 2 sheetes celt.

## Nem-cel

- Solverlogika, IO contract vagy validacios contract refaktoralasa.
- Celkriterium lazitasa 3 sheetre.
- Q41 input kezi atirasa; Q42 sajat inputot general.

## Felderitett forrasok

- `artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json` - kanonikus full276 LV8 input (12 part, 276 instance).
- `scripts/bench_sgh_q41_full276_m5_s10_visuals.py` - Q41 runner es render minta.
- `artifacts/benchmarks/sgh_q41/inputs/Q41_B_3L_full276_3x1500x3000_m5_s10.json` - Q41 input minta; part-level `allowed_rotations_deg` listakkal.
- `rust/vrs_solver/src/item.rs` - rotation precedence: part `rotation_policy`, majd non-empty `allowed_rotations_deg`, majd global `rotation_policy`.
- `rust/vrs_solver/src/rotation_policy.rs` - continuous policy 16 egyenletes mintaval, canonical szogekkel.

## Feladatlista

- [ ] Q42 runner letrehozasa Q41 render/report mintaval.
- [ ] Q42 input generalasa ugy, hogy a global `rotation_policy = continuous` tenylegesen ervenyesuljon.
- [ ] Run A 1200 sec futtatasa.
- [ ] Run B 2400 sec futtatasa, ha Run A nem teljesiti a 2 sheetes acceptance-et.
- [ ] Q42 summary es markdown report kitoltese a futasi eredmenyekkel.
- [ ] Render evidence eloallitasa sheetenkent es overview szinten.
- [ ] Repo gate futtatasa `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md` paranccsal.

## DoD

1. A Q42 input a kanonikus full276 LV8 csomagbol keszul, 3 db 1500x3000 stockkal.
2. Az input `margin_mm = 5.0`, `spacing_mm = 8.0`, `kerf_mm = 0.0`, `rotation_policy = continuous` ertekeket tartalmaz.
3. A Q42 input nem tartalmaz part-level `allowed_rotations_deg` listat, amely felulirna a global continuous policyt.
4. Run A 1200 sec lefut es output JSON keletkezik.
5. Run B 2400 sec csak akkor fut, ha Run A nem eri el a valid 2-sheet celt.
6. A summary riportolja: status, placed/unplaced, used sheet count/indexek, utilization, final pairs, boundary/margin/spacing violations, runtime, wall time.
7. A continuous rotation bizonyitek riportolja: input policy, part-level listakezeles, unique rotation count, non-orthogonal count, min/max es peldak.
8. A margin/spacing ellenorzes riportolja az alkalmazott technologiai mezoket es violation countokat.
9. Render evidence keszul a hasznalt sheetekhez SVG es PNG formatumban, plusz overview.
10. A Codex report nem ad teljes PASS-t, ha 2400 sec utan sincs valid legfeljebb 2 sheetes full276 layout.

## Kockazatok es rollback

- A 2 sheetes cel keresesi vagy geometriai okbol nem teljesulhet 2400 sec alatt. Ilyenkor a benchmark eredmeny FAIL/NOT ACHIEVED, de az artefaktumok es a legjobb valid eredmeny dokumentaltak.
- A continuous output szogei lehetnek csak canonical szogek, meg akkor is, ha a policy aktiv. Ilyenkor a report nem allit bizonyitott continuous elhelyezest; a bemenetet es solver policy utat kell dokumentalni.
- Rollback: a Q42-re hozzaadott `scripts/bench_sgh_q42_full276_lv8_continuous.py`, `artifacts/benchmarks/sgh_q42/`, canvas/YAML/checklist/report fajlok torlese visszaallitja a repo benchmark elozo allapotat.

## Teszt terv

- `python3 scripts/bench_sgh_q42_full276_lv8_continuous.py`
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q42_full276_lv8_continuous_benchmark.md`
