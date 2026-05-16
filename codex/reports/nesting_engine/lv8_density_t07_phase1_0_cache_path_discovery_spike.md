# Report — lv8_density_t07_phase1_0_cache_path_discovery_spike

**Státusz:** PASS_WITH_NOTES

A T07 read-only cache path discovery spike elkészült. A meglévő `NfpCache` valós
hívási útjai feltérképezve, per-kernel státuszok dokumentálva, shape_id origin audit
kész. Nem történt production Rust/Python kódmódosítás. Több kérdéshez konkrét T08/T09/T10
follow-up lett rendelve.

## 1) Meta

- **Task slug:** `lv8_density_t07_phase1_0_cache_path_discovery_spike`
- **Kapcsolódó canvas:** `canvases/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t07_phase1_0_cache_path_discovery_spike.yaml`
- **Futás dátuma:** 2026-05-17
- **Branch / commit:** `main@9ec54d4`
- **Fókusz terület:** Geometry / Audit

## 2) Scope

### 2.1 Cél

1. T06 előfeltétel-állapot ellenőrzése T07 indulhatósághoz.
2. NFP cache hívási utak és cache-bypass lehetőségek feltérképezése.
3. Per-kernel cache-út audit (old_concave, cgal_reference, reduced_convolution státusz).
4. `shape_id` kulcsképzés eredetének auditja.
5. `LRU vs clear_all` döntési input és `pipeline_version` szükségesség előkészítése.

### 2.2 Nem-cél (explicit)

1. Nincs cache-implementációs változtatás.
2. Nincs LRU bevezetés.
3. Nincs Rust/Python production fix.
4. Nincs új teszt T07-ben.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `tmp/phase1_spike_cache_path_discovery.md` (új)
- `codex/codex_checklist/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md` (új)
- `codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md` (új)
- `codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.verify.log` (verify fogja írni)

### 3.2 Miért változtak?

- A spike output rögzíti a cache call graphot és a phase handoff döntési inputokat.
- A checklist és a report auditálható formában lezárja a T07 DoD pontokat.

## 4) Előfeltétel és audit eredmények

- T06 report létezik és státusz `PASS_WITH_NOTES`: `codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md`.
- T06 alias report létezik: `codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md`.
- `hard_cut_decision=DEFER_HARD_CUT` nem blokkoló T07-hez.
- Kötelező cache/NFP audit fájlok mind jelen vannak (`cache.rs`, `nfp_placer.rs`, `greedy.rs`, `provider.rs`, `concave.rs`, `cgal_reference_provider.rs`).

Rövid cache call-graph kivonat:
- Cache létrehozás lifecycle root: `rust/nesting_engine/src/multi_bin/greedy.rs:646`.
- Cache használat (`get/insert`) mindhárom placer útban: `rust/nesting_engine/src/placement/nfp_placer.rs:917-935`, `1155-1176`, `1277-1328`, `2063-2085`.
- NFP dispatch: `rust/nesting_engine/src/placement/nfp_placer.rs:1786-1842`.
- Helper provider API (`compute_nfp_lib_with_provider`) jelenleg inaktív (`rust/nesting_engine/src/nfp/provider.rs:215`).

## 5) Verifikáció (How tested)

### 5.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md` → PASS.

### 5.2 Opcionális / feladatfüggő parancsok

- T06 előfeltétel python ellenőrzés futtatva (létezés + header).
- Kötelező inventory python ellenőrzés futtatva.
- Szimbólum scan futtatva:
  - `grep -R "compute_nfp_lib\|compute_stable_concave_nfp\|compute_nfp_lib_with_provider\|NfpCache\|NfpCacheKey\|shape_id\|cache.get\|cache.insert" -n rust/nesting_engine/src > tmp/t07_cache_symbol_scan.txt`

### 5.3 Ha valami kimaradt

- Nem maradt ki kötelező ellenőrzés.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-17T01:26:30+02:00 → 2026-05-17T01:29:46+02:00 (196s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.verify.log`
- git: `main@9ec54d4`
- módosított fájlok (git status): 6

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
?? codex/codex_checklist/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t07_phase1_0_cache_path_discovery_spike.yaml
?? codex/prompts/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike/
?? codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
?? codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.verify.log
```

<!-- AUTO_VERIFY_END -->

## 6) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat | Kapcsolódó ellenőrzés |
|---|---|---|---|---|
| T06 report létezik és PASS/PASS_WITH_NOTES | PASS | `codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md` | Státusz `PASS_WITH_NOTES`, T07 indulhat. | python precheck |
| Spike report elkészült a kötelező 6 szekcióval | PASS | `tmp/phase1_spike_cache_path_discovery.md` | Minden kért fejezet szerepel. | manuális ellenőrzés |
| NFP pathok cache/bypass státusza dokumentált | PASS | `rust/nesting_engine/src/placement/nfp_placer.rs:917-935`, `1155-1176`, `1277-1328`, `2063-2085` | A fő compute pathok `get/insert` párossal futnak. | symbol scan + code audit |
| OldConcave / cgal_reference / reduced_convolution per-kernel státusz dokumentált | PASS_WITH_NOTES | `rust/nesting_engine/src/placement/nfp_placer.rs:1746-1762`; `rust/nesting_engine/src/nfp/provider.rs:131-146` | old/cgal út igazolt; reduced_convolution jelenleg inaktív/unreachable. | code audit |
| `shape_id` origin audit (inflated vs nominal) | PASS_WITH_NOTES | `rust/nesting_engine/src/nfp/cache.rs:101-135`; `rust/nesting_engine/src/placement/nfp_placer.rs:718-719`, `1271`, `2061-2065` | Inflated polygonból képzett hash igazolt; spacing-hatás formális bizonyítása T09 follow-up. | code audit |
| LRU vs `clear_all` döntési input megvan | PASS | `rust/nesting_engine/src/nfp/cache.rs:16`, `64-67`, `72-76`, `79-85`; `codex/reports/nesting_engine/lv8_density_t04_phase0_engine_stats_export.md` | MAX_ENTRIES + clear_all reset és stat-gap dokumentált. | code audit + T04 report |
| `pipeline_version` szükségesség eldöntve vagy bontva | PASS_WITH_NOTES | `rust/nesting_engine/src/nfp/cache.rs:24-31`; `rust/nesting_engine/src/placement/nfp_placer.rs:1794-1810` | `UNPROVEN`, konkrét T09 tesztfeladatra bontva. | code audit |
| T08/T09/T10 handoff konkrét | PASS | `tmp/phase1_spike_cache_path_discovery.md` | Mindhárom follow-up scope rögzítve. | report review |
| Production kód nem módosult | PASS | `git status` diff alapján nincs Rust/Python production file módosítás T07 által | Csak T07 output fájlok készültek. | git status |
| Repo gate lefutott | PASS | AUTO_VERIFY blokk | A verify PASS, a log mentve. | `./scripts/verify.sh --report ...` |

## 7) Production-code-change check

- T07-ben production file módosítás nem történt (`rust/nesting_engine/src/**`, `scripts/experiments/**`, `vrs_nesting/**`, `worker/**`, `tests/**` érintetlen).

## 8) Advisory notes

- `compute_nfp_lib()` provider fallback (`cgal_reference` -> `old_concave`) miatt a runtime-környezet befolyásolhatja a tényleges szemantikát; ezt T09-ben explicit matrix-szal kell lefedni.
- `clear_all()` hit/miss reset miatt hosszabb futásoknál nehéz történeti cache-trendet mérni; T08 observability mezők priorizálandók.

## 9) Follow-ups (T08/T09/T10 handoff)

1. **T08:** `nfp_cache_clear_all_events` és `nfp_cache_peak_entries` mezők bevezetése, plusz clear-all esemény számláló export.
2. **T09:** shape_id/cache-key invariáns tesztek spacing- és pipeline-szemantika ellenőrzéshez; külön fókusz a cgal fallback szcenáriókra.
3. **T10:** cache usage benchmark és hit/miss trend értékelés T08 stat-bővítésre építve; LRU szükségességi döntés benchmark-alapon.
