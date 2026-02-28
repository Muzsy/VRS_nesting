# canvases/nesting_engine/nesting_engine_f2_3_bootstrap_placer_flag_gating.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_f2_3_bootstrap_placer_flag_gating.md`
> **TASK_SLUG:** `nesting_engine_f2_3_bootstrap_placer_flag_gating`
> **Terület (AREA):** `nesting_engine`

---

# F2-3 bootstrap: placer flag + hybrid gating + hole-mentes fixture + gate smoke

## 🎯 Funkció

Az F2-3 tényleges fejlesztésének előkészítése “wiring” szinten:

1) `nesting_engine nest` kapjon runtime kapcsolót:
   - `--placer blf|nfp` (default: blf)

2) Hybrid gating F2-3 spec szerint:
   - ha `--placer nfp`, de **bármely part holes-os** (nominal holes) → automatikus fallback BLF
   - ha `--placer nfp`, de bármely part `status == hole_collapsed` → automatikus fallback BLF
   - fallback esetén determinisztikus módon **ugyanaz** a kimenet, mint BLF (csak stderr warning megengedett)

3) Adjunk hozzá egy **hole-mentes** v2 input fixture-t, hogy legyen olyan input, amin az `--placer nfp` útvonal
   “elő tud állni” (gating nem dobja vissza azonnal BLF-re).

4) Gate smoke bővítés:
   - `--placer nfp` + holes-os input → output hash egyezzen a baseline BLF hash-sel
   - `--placer nfp` + hole-mentes input → JSON valid + determinisztikus hash két futás közt

Megjegyzés: ebben a bootstrap taskban az “NFP placer” még lehet átmenetileg BLF-delegált (stub),
a cél most a **bekötés, szerződés és gate**.

## Nem cél
- IFP/CFR boolean pipeline megírása (külön task, a valódi F2-3).
- NFP minőségjavulás mérése (külön task, amikor már CFR van).

---

## 🧠 Fejlesztési részletek

### Felderítési jegyzet (2026-02-28)
- `rust/nesting_engine/src/main.rs`: a `nest` útvonal jelenleg fixen `run_nest()` hívás, nincs placer flag parsing; itt kell a `--placer blf|nfp` bekötés és a hybrid gating döntés.
- `rust/nesting_engine/src/multi_bin/greedy.rs`: a wrapper körben közvetlenül `blf_place(...)` fut; ide kell a placerválasztó kapcsoló (BLF/NFP).
- `rust/nesting_engine/src/placement/mod.rs`: jelenleg csak `blf` export van; ide kell az `nfp_placer` modul exportálása.
- `scripts/check.sh` (`[NEST] Baseline nesting_engine smoke` blokk): megvan a baseline hash + determinism ellenőrzés; ide illeszthető a `--placer nfp` fallback/hash-egyezés és a noholes dupla futás hash-egyezés smoke.

### Bekötési pontok
- `rust/nesting_engine/src/main.rs`: argumentum parsing + gating + placer választás
- `rust/nesting_engine/src/multi_bin/greedy.rs`: a wrapper tudjon placert választani (BLF/NFP)
- `rust/nesting_engine/src/placement/mod.rs`: új NFP placer export
- `rust/nesting_engine/src/placement/nfp_placer.rs`: ideiglenes stub (BLF delegálás) + későbbi CFR TODO

### Fixture
- új input: `poc/nesting_engine/f2_3_noholes_input_v2.json`
  - minden part `holes_points_mm: []`
  - `spacing_mm` legyen explicit (ne legacy kerf útvonal)
  - margin legyen > spacing/2, hogy a meglévő smoke “placement below margin” guard ne legyen bizonytalan

### Gate smoke kiterjesztés
- `scripts/check.sh` nesting_engine részében:
  - futtass `nest --placer nfp` a `sample_input_v2.json`-on és ellenőrizd, hogy a determinism_hash egyezik a baseline BLF hash-sel (gating miatt)
  - futtass `nest --placer nfp` a `f2_3_noholes_input_v2.json`-on kétszer, és a hash-ek egyezzenek

---

## 🧪 Tesztállapot

### DoD
- [ ] `nesting_engine nest --placer blf|nfp` működik (default: blf)
- [ ] Hybrid gating megvan: holes vagy hole_collapsed esetén `--placer nfp` → BLF fallback (determinism hash egyezik baseline-nal)
- [ ] Új hole-mentes fixture valid JSON és lefut rajta a `nest --placer nfp`
- [ ] Gate smoke bővítve a két új ellenőrzéssel
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_bootstrap_placer_flag_gating.md`

---

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `docs/nesting_engine/f2_3_nfp_placer_spec.md` (placer flag + hybrid gating)
- `scripts/check.sh`
- `poc/nesting_engine/sample_input_v2.json`
- `AGENTS.md`, `docs/codex/yaml_schema.md`
