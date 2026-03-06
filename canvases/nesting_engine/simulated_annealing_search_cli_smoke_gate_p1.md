# simulated_annealing_search_cli_smoke_gate_p1

## Funkcio

P1 hardening feladat: keruljon be a merge gate-be egy valodi, end-to-end SA CLI smoke,
ami a `nesting_engine nest --search sa` utvonalat futtatja valos fixture-rel.

A gate bizonyitsa, hogy:

- stdout valos JSON,
- `meta.determinism_hash` jelen van,
- ugyanazzal az inputtal az SA futas determinisztikus,
- a quality fixture-en teljesul a minimum quality kuszob (`sheets_used <= 1`).

Ez a task nem uj SA feature, hanem F2-4 allapot gate-szintu bizonyitasa.

## Miert kell

A jelenlegi gate mar futtatja:

- `cargo test ... sa_`,
- SA unit determinisztika teszteket,
- SA quality unit tesztet.

Gap: nincs olyan check, ami a valos binaris CLI utvonalat (`nesting_engine nest --search sa`)
futtatja es gate szinten ellenorzi.

## Nem cel

- SA algoritmus ujratervezese vagy quality tuning.
- Python `nest-v2` SA flag pass-through bovites.
- IO contract mezobovites.
- Altalanos docs refactor.

## Erintett valos fajlok

- `scripts/smoke_nesting_engine_sa_cli.py` (uj)
- `scripts/check.sh`
- `codex/codex_checklist/nesting_engine/simulated_annealing_search_cli_smoke_gate_p1.md`
- `codex/reports/nesting_engine/simulated_annealing_search_cli_smoke_gate_p1.md`

Csak olvasott fixture:

- `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`

## Megoldasi elv

1. Keszul kulon Python smoke script (`scripts/smoke_nesting_engine_sa_cli.py`), ami:
   - kap explicit `--bin` es `--input` argumentumot,
   - a binarist `nest --search sa` modban futtatja stdin fixture-rel,
   - tobb egymas utani futasban ellenorzi a JSON contractot es a hash stabilitast,
   - ellenorzi a quality kuszobot (`sheets_used <= 1`),
   - hiba eseten egyertelmu, action-oriented stderr uzenettel all le.
2. A script bekerul a `scripts/check.sh` nesting_engine blokkjaba a `cargo test ... sa_` utan.
3. A gate a mar meglevo `NESTING_ENGINE_BIN_PATH` binarisra fut.

## DoD

- [ ] Van kulon smoke script: `scripts/smoke_nesting_engine_sa_cli.py`.
- [ ] Script ellenorzi: JSON parse, `version == nesting_engine_v2`, nem ures `meta.determinism_hash`.
- [ ] Script legalabb 2 futas hash-et hasonlit, es mismatch-re non-zero exit.
- [ ] Script quality fixture-en ellenorzi: `sheets_used <= 1`.
- [ ] `scripts/check.sh` meghivja a scriptet a `cargo test ... sa_` utan, a `NESTING_ENGINE_BIN_PATH` valtozoval.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_cli_smoke_gate_p1.md` PASS.

## Kockazat es rollback

- Kockazat: ha a smoke fixture tul lassu vagy instabil kornyezetbe fut, a gate zajossaga nohet.
- Mitigacio: a smoke fix fixture-rel dolgozik, kulon scriptben, minimalis ellenorzesi korrel.
- Rollback terv: ha regressziot okoz, a `scripts/check.sh` SA CLI smoke hivasanak ideiglenes kivezetese
  visszaallitja az elozo gate viselkedest, mikozben az SA unit tesztek tovabb futnak.

## Teszteles

Elvart lokalis smoke futas:

```bash
python3 scripts/smoke_nesting_engine_sa_cli.py \
  --bin "$NESTING_ENGINE_BIN_PATH" \
  --input "poc/nesting_engine/f2_4_sa_quality_fixture_v2.json"
```
