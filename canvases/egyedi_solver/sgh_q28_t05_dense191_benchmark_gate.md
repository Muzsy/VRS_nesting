# SGH-Q28-T05 — Dense 191 benchmark gate + Q28 validation suite

## 🎯 Funkció / Cél

- Mérési bizonyíték az inkrementális session gyorsításáról: iteráció/másodperc T04 előtt vs után.
- Python smoke script (`scripts/smoke_sgh_q28_dense191_benchmark.py`), amely:
  - futtatja a vrs_solver binárist a 191-darabos LV8 single-sheet fixture-rel (90 s budget)
  - kiolvassa a diagnosztikából az `iterations` és `time` értékeket
  - assertálja, hogy `iterations >= 10` (vs. a T04 előtti ~2 iteráció 90 s alatt)
  - assertálja, hogy `final_pairs < 55` (Q24R9 baseline 55 volt)
- Rust integration teszt bővítése: `sgh_q28_dense_191_incremental_session_speedup` — rögzíti,
  hogy a dense (≥100 instance) profil aktív és az iteráció szám magasabb az előző baseline-nál.
- Report rögzíti a mért session-build count-ot (diag.native_tracker_full_rebuilds proxy).

## Nem-cél (explicit)

- Nem cél 0 pár elérése (elfogadható PASS_WITH_NOTES, ha `final_pairs < 30`).
- Nem cél a 276-darabos full LV8 benchmark.
- Nem módosítja az algoritmust — csak mér és assertál.
- Nem változtat a Q26 teszteken.

## 🧠 Fejlesztési részletek

### Scope

**Benne van:**
- `scripts/smoke_sgh_q28_dense191_benchmark.py`:
  - Bináris: `rust/vrs_solver/target/release/vrs_solver` (meglévő)
  - Fixture: LV8 single-sheet JSON (191 instance, 90 s budget) — az `tests/fixtures/` alatt meglévő
    vagy a meglévő `scripts/smoke_real_dxf_sparrow_pipeline.py` mintájára generált
  - Assert: `iterations >= 10`, `final_pairs < 55`, `dense_real_run == true`
  - Output: stdout PASS/FAIL + diagnosztika

- `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs` bővítése:
  - Új teszt `q28_dense_191_incremental_session_speedup`: 191-instance fixture, 60 s,
    assertál: `dense_real_run == true`, `iterations >= 5` (konzervatív gate)

### Érintett fájlok

- Új: `scripts/smoke_sgh_q28_dense191_benchmark.py`
- Módosul: `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs`

### DoD (Definition of Done)

- [ ] `smoke_sgh_q28_dense191_benchmark.py` létezik és PASS-t ad.
- [ ] `iterations >= 10` (90 s, inkrementális session-nel) assertált.
- [ ] `final_pairs < 55` assertált.
- [ ] Q26 integration tesztek változatlanul PASS (8 db).
- [ ] `./scripts/verify.sh` PASS.

### Kockázatok + mitigáció + rollback

- **Kockázat:** 191-darabos LV8 fixture esetleg nem érhető el gyárilag.
  **Mitigáció:** A smoke script a meglévő `samples/real_work_dxf/0014-01H/lv8jav/*.dxf` alapján
  generál egy minimális JSON fixture-t runtime-ban, a Q26 LV8-derived smoke mintájára.
- **Kockázat:** Az iteráció gate (≥10) túl szigorú ha T03/T04 nem nyújt elvárt gyorsulást.
  **Mitigáció:** Ha az iteráció elmarad, a FAIL report részletezi a mért session build count-ot.

## 🧪 Tesztállapot

```bash
python3 scripts/smoke_sgh_q28_dense191_benchmark.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation \
  q28_dense_191_incremental_session_speedup -- --nocapture
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q28_t05_dense191_benchmark_gate.md
```

## 📎 Kapcsolódások

- Előző task: `canvases/egyedi_solver/sgh_q28_t04_tracker_session_reuse.md`
- Task index: `canvases/egyedi_solver/sgh_q28_incremental_cde_session_task_index.md`
- Érintett forrás: `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs`
- Mintaként: `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py`
