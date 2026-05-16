# Report — lv8_density_t03_phase0_nfp_diag_gate

**Státusz:** PASS

A `./scripts/verify.sh` (repo gate) zöld: `check.sh` exit 0, 201s teljes
futási idő (2026-05-16T17:59:46 → 18:03:07). Tartalmazza: pytest 302 passed,
mypy clean, Sparrow IO smoketest + validator, DXF import/export + multisheet
+ valós DXF pipeline smokes, `vrs_solver` validator + determinisztika +
timeout/perf guard — mind PASS. A `[CONCAVE NFP DIAG]` env-gate és az új
`concave_nfp_diag_env_gate` unit teszt regressziómentes. Production diff
a canvas engedélyezett fehérlistájára szorítkozik
(`rust/nesting_engine/src/nfp/concave.rs`,
`scripts/experiments/lv8_2sheet_claude_search.py`). Minden T03 DoD pont PASS.

## 1) Meta

- **Task slug:** `lv8_density_t03_phase0_nfp_diag_gate`
- **Kapcsolódó canvas:** [canvases/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md](../../../canvases/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md)
- **Kapcsolódó goal YAML:** [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t03_phase0_nfp_diag_gate.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t03_phase0_nfp_diag_gate.yaml)
- **T00 index:** [canvases/nesting_engine/lv8_density_task_index.md](../../../canvases/nesting_engine/lv8_density_task_index.md)
- **T00 master runner:** [codex/prompts/nesting_engine/lv8_density_master_runner.md](../../prompts/nesting_engine/lv8_density_master_runner.md)
- **T01 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t01_phase0_fixture_inventory.md](lv8_density_t01_phase0_fixture_inventory.md) (PASS)
- **T02 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t02_phase0_quality_profile_shadow_switch.md](lv8_density_t02_phase0_quality_profile_shadow_switch.md) (PASS)
- **Forrásterv:** [codex/reports/nesting_engine/development_plan_packing_density_20260515.md](development_plan_packing_density_20260515.md) v2.2, Phase 0.2.
- **Futás dátuma:** 2026-05-16
- **Branch / commit:** `main` @ `a1253d5`
- **Fókusz terület:** Rust engine (NFP diag stderr env-gate) + benchmark harness komment

## 2) Scope

### 2.1 Cél

1. A `rust/nesting_engine/src/nfp/concave.rs` `[CONCAVE NFP DIAG]` `eprintln!`
   sorai default off állapotba kerülnek; opt-in `NESTING_ENGINE_NFP_DIAG=1`
   mellett változatlanul elérhetők.
2. Az env olvasás kikerül a beágyazott NFP-pár ciklusból (`diag_enabled`
   lokális bool a ciklus előtt).
3. Unit teszt a helper viselkedésére, env-state restore-ral.
4. `nfp_placer.rs` meglévő hot-path diag gate-jeinek audit reportolása,
   változtatás nélkül.
5. `scripts/experiments/lv8_2sheet_claude_search.py` stderr quiet policy
   auditja; legfeljebb komment/marker pontosítás.
6. T03 checklist + report a Report Standard v2 szerint.

### 2.2 Nem-cél (explicit)

1. NFP algoritmus módosítása.
2. Cache (`NfpCache`/`NfpCacheKey`) módosítása.
3. `nfp_placer.rs` hot-path viselkedésének módosítása.
4. `search/sa.rs` módosítása vagy törlése.
5. Phase 2+ scoring / lookahead / beam / LNS funkció.
6. Hosszú LV8 benchmark futtatása.
7. `LV8_HARNESS_QUIET` default policy érdemi megváltoztatása.
8. T06 shadow run hard-cut véglegesítése.

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

- **Rust engine (canvasban engedélyezett, production diff):**
  - [rust/nesting_engine/src/nfp/concave.rs](../../../rust/nesting_engine/src/nfp/concave.rs)
    — `is_concave_nfp_diag_enabled()` helper (`#[inline]`,
    [:23-30](../../../rust/nesting_engine/src/nfp/concave.rs#L23-L30));
    5 `[CONCAVE NFP DIAG]` `eprintln!` gate alá kerülve
    ([:234-243](../../../rust/nesting_engine/src/nfp/concave.rs#L234-L243) +
    [:279-326](../../../rust/nesting_engine/src/nfp/concave.rs#L279-L326));
    új `concave_nfp_diag_env_gate` unit teszt
    + `DIAG_ENV_LOCK` `Mutex<()>` szerializálás a test modulban.
- **Benchmark harness komment (canvasban engedélyezett, komment-only):**
  - [scripts/experiments/lv8_2sheet_claude_search.py](../../../scripts/experiments/lv8_2sheet_claude_search.py)
    — quiet-branch komment pontosítva (a `[CONCAVE NFP DIAG]` opt-in tényt
    rögzíti; a quiet policy magyarázata "general log-size guard"-ra módosul).
    A subprocess hívás és a default policy értéke változatlan.
- **Codex artefaktok:**
  - [codex/codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md](../../codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md) (új)
  - [codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md](lv8_density_t03_phase0_nfp_diag_gate.md) (új, ez a fájl)
  - `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log`
    (a `./scripts/verify.sh` írja a repo gate-ben).

Nem módosult, bár releváns: `rust/nesting_engine/src/placement/nfp_placer.rs`
— a meglévő gate-ek auditálva, nem nyúltunk hozzájuk.

### 3.2 Miért változtak?

- **`concave.rs` env-gate:** a default-on `eprintln!` sorok LV8 fixture-en
  megabyte-os stderr-t termelnek minden NFP-páron — ez blokkolta az
  engine-t, és a benchmark harness ezért dobta el stderr-t. Most a
  diagnosztika opt-in: a default mérés tiszta, de a hibakeresésre szánt
  formátum (ENTRY / decompose_done / partial_nfp* / union_done) bekapcsolva
  bitre azonos.
- **Loop-hot-path env olvasás:** a `compute_stable_concave_nfp()` a két
  konvex halmaz szorzatára iterál; az env-olvasás per iteráció felesleges
  rendszerhívás. A `diag_enabled` lokális bool a ciklus előtt kiszámolva
  default off esetben gyakorlatilag zero-overhead.
- **Unit teszt:** a flag parsernek 4 különböző env-állapotra
  determinisztikusan kell reagálnia. Az env process-global, ezért a cargo
  párhuzamos test runner alatt egy mutex szerializálja a teszt-execution-t,
  és az eredeti env-állapot teszt után visszaáll.
- **Harness komment:** a régi komment a `[CONCAVE NFP DIAG]` spam-ot
  említette mint a quiet policy elsődleges indokát. Az új komment ezt
  pontosítja: a diag mostantól opt-in, a quiet policy pedig általános
  log-size guard. A subprocess hívás logikája nem módosult.

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
  → eredmény az AUTO_VERIFY blokkban (4.4 alatt).
- Log: `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log`

### 4.2 Opcionális, feladatfüggő parancsok

- **Előfeltétel ellenőrzés:** 12/12 kötelező rule + T0x előzmény-anchor jelen.
  T02 status check: `T03 prerequisite T02 status PASS`.
- **Kiinduló audit:**
  - `concave.rs` 5 `[CONCAVE NFP DIAG]` sora (sorok 226, 275, 287, 298, 313
    a módosítás előtt) azonosítva.
  - `nfp_placer.rs` már tartalmaz 5 hot-path diag helper-t
    (`is_candidate_diag_enabled`, `is_hybrid_cfr_diag_enabled`,
    `is_active_set_diag_enabled`, `is_nfp_runtime_diag_enabled`,
    `is_cfr_diag_enabled`) — mind külön env flag mögött. T03 nem nyúl hozzájuk.
  - `lv8_2sheet_claude_search.py` `LV8_HARNESS_QUIET=1` default; quiet
    branch eldobta stderr-t a CONCAVE NFP DIAG spam miatt.
- **T03 grep sanity:** `T03 concave diag grep PASS` (a helper jelen, és
  minden `[CONCAVE NFP DIAG]` sor 8 sorral feljebb tartalmaz `diag_enabled`
  / `is_concave_nfp_diag_enabled` jelzést).
- **`cargo check --manifest-path rust/nesting_engine/Cargo.toml`** →
  `Finished dev profile [unoptimized + debuginfo] target(s) in 6.77s`;
  csak pre-existing warningok (`polygon_max_deviation_mm` dead code,
  `cfr_fallback_*` unused fields, `ACTIVE_SET_MAX_CANDIDATES_PER_LEVEL`
  unused konstans — egyik sem T03-tól származik).
- **`cargo test --manifest-path rust/nesting_engine/Cargo.toml concave_nfp_diag -- --nocapture`**
  → `1 passed; 0 failed; 0 ignored; 0 measured; 95 filtered out`. Az új
  `concave_nfp_diag_env_gate` zöld.
- **Production diff guard:** `T03 production diff guard PASS`. Production
  diff scope: `rust/nesting_engine/src/nfp/concave.rs` +
  `scripts/experiments/lv8_2sheet_claude_search.py` — mindkettő a canvas
  whitelistjén.

### 4.3 Ha valami kimaradt

Semmilyen kötelező ellenőrzés nem maradt ki. Hosszú LV8 benchmark explicit
tilos (T06 scope). A `nfp_placer.rs` érintése elkerülhető volt (a meglévő
gate-ek külön env flag-eken működnek), így csak audit történt.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-16T17:59:46+02:00 → 2026-05-16T18:03:07+02:00 (201s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log`
- git: `main@a1253d5`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 rust/nesting_engine/src/nfp/concave.rs          | 153 +++++++++++++++++-------
 scripts/experiments/lv8_2sheet_claude_search.py |  10 +-
 2 files changed, 120 insertions(+), 43 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/nesting_engine/src/nfp/concave.rs
 M scripts/experiments/lv8_2sheet_claude_search.py
?? canvases/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
?? codex/codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t03_phase0_nfp_diag_gate.yaml
?? codex/prompts/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate/
?? codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
?? codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log
```

<!-- AUTO_VERIFY_END -->

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| #1 `NESTING_ENGINE_NFP_DIAG` helper létezik a `concave.rs`-ben | PASS | [rust/nesting_engine/src/nfp/concave.rs:23-30](../../../rust/nesting_engine/src/nfp/concave.rs#L23-L30) | `#[inline] fn is_concave_nfp_diag_enabled() -> bool { std::env::var("NESTING_ENGINE_NFP_DIAG").as_deref() == Ok("1") }` — explicit env flag, nincs más név. | `T03 concave diag grep PASS` |
| #2 Minden `[CONCAVE NFP DIAG]` `eprintln!` gate mögött van | PASS | 5/5 sor gate alatt: `ENTRY` [:234-243](../../../rust/nesting_engine/src/nfp/concave.rs#L234-L243); `decompose_done`, `partial_nfp`, `partial_nfp_done`, `union_done` [:279-326](../../../rust/nesting_engine/src/nfp/concave.rs#L279-L326) | A ciklusbeli 2 sor `diag_enabled` lokális bool-lal (env olvasás egyszer, nem iterációnként). | `T03 concave diag grep PASS` |
| #3 Default off állapotban nincs concave diag stderr spam | PASS | A helper csak `"1"`-re ad true-t; a `cargo test concave_nfp_diag` `unset env → false` esete (helper false-t ad) bizonyítja, hogy default off | A `if is_concave_nfp_diag_enabled()` / `if diag_enabled` guardok blokkolják az `eprintln!`-eket. | `cargo test concave_nfp_diag` |
| #4 `NESTING_ENGINE_NFP_DIAG=1` mellett a diagnosztikai sorok elérhetőek | PASS | `cargo test` `set("1") → true` esete | A formázás és az `eprintln!` ágak változatlanok — csak gate alá kerültek. | `cargo test concave_nfp_diag` |
| #5 A változás nem befolyásol geometriát, NFP eredményt, cache-t, scoringot vagy placement döntést | PASS | `cargo check --manifest-path rust/nesting_engine/Cargo.toml` zöld; production diff guard csak `concave.rs`-t és a harness scriptet érinti | A gate-ek `if`-be csomagolt eprintln-ek; semmi adatáramlás vagy hot-path elágazás nem változott. | `cargo check` + production diff guard |
| #6 `nfp_placer.rs` meglévő hot-path diag gate-jei auditálva, módosítás nélkül | PASS | [rust/nesting_engine/src/placement/nfp_placer.rs:155-211](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L155-L211) — 5 helper függvény, mindegyik saját env flaggel | `is_candidate_diag_enabled` / `is_hybrid_cfr_diag_enabled` / `is_active_set_diag_enabled` / `is_nfp_runtime_diag_enabled` / `is_cfr_diag_enabled` — mind változatlanul ott; T03 git diff nem érinti a fájlt. | `git diff --name-only HEAD -- '*nfp_placer.rs'` → üres |
| #7 Benchmark harness stderr policy audit; ha módosult, csak komment szinten | PASS | [scripts/experiments/lv8_2sheet_claude_search.py:174-180](../../../scripts/experiments/lv8_2sheet_claude_search.py#L174-L180) | Csak komment szöveg módosult (`[harness] stderr discarded under LV8_HARNESS_QUIET=1 (log-size guard)`); a default `LV8_HARNESS_QUIET=1` és a subprocess.run logika érintetlen. | Production diff guard |
| #8 `cargo check -p nesting_engine` zöld | PASS | `Finished dev profile target(s) in 6.77s` | Csak pre-existing warningok (dead code, unused fields/konstans); nincs új error vagy warning. | `cargo check` |
| #9 Célzott diag helper teszt zöld | PASS | `cargo test concave_nfp_diag` → `1 passed; 0 failed` | `concave_nfp_diag_env_gate` 4 állapotra ellenőrzi a helper-t (unset / `0` / `1` / `true`); env-state restore + `DIAG_ENV_LOCK` mutex párhuzamos test-race ellen. | `cargo test concave_nfp_diag` |
| #10 `./scripts/verify.sh --report …` zöld | PASS | AUTO_VERIFY blokk a 4.4 alatt: `eredmény: PASS`, `check.sh exit 0`, 201s | A repo gate teljes `check.sh`-t futtatott (pytest + mypy + Sparrow + DXF + multisheet + `vrs_solver` + determinisztika + perf guard) — mind zöld. | `./scripts/verify.sh --report …` |
| #11 Checklist és report Report Standard v2 szerint | PASS | [Checklist](../../codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md) + ez a fájl (11 sor DoD bizonyítékkal) | A checklist pipálható DoD-listát ad, a report Report Standard v2 struktúrát követi minden ponthoz path + line / parancs bizonyítékkal. | `./scripts/verify.sh --report …` |

Minden DoD pont PASS.

## 6) IO contract / minták

Nem releváns: T03 nem módosította a Sparrow IO contractot, a POC mintákat
vagy a validator-t. A canonical NFP output bit-szintű azonos marad.

## 7) Doksi szinkron

- A canvas `NESTING_ENGINE_NFP_DIAG` flag-konvencióját 1:1 átvettük.
- A `docs/codex/yaml_schema.md` és `docs/codex/report_standard.md`
  szabályait a YAML és a report struktúrája tartja.
- A T00 master runner Files-and-fixtures szekciója a `concave.rs`-t mint
  `[CONCAVE NFP DIAG]` anchor-t hivatkozza; ezt a T03 most opt-in formába
  csatornázza.

## 8) Advisory notes (max 5)

- A Rust 2024 edition `env::set_var` / `env::remove_var` `unsafe`-jelölést
  kapott (multi-threaded env-modification veszélyei miatt). A T03 új
  unit tesztje `DIAG_ENV_LOCK: Mutex<()>` szerializálással biztonságos:
  egyetlen teszt sem futtat env-mutációt, amíg a lock-ot tartja egy másik.
  Más teszteknek a modulban nincs env függésük, így az interferencia
  esélye nulla.
- A `partial_nfp` és `partial_nfp_done` ciklusban a `diag_enabled`
  lokális bool a ciklus előtt egyszer kiszámítódik — opt-in állapotban
  is csak egy env-olvasás per NFP-páros (a teljes konvex-szorzat-ciklus
  nem érint env-et).
- A `LV8_HARNESS_QUIET=1` default policy szándékosan konzervatív marad:
  T06 a no-SA shadow run alatt fogja megmérni, hogy mekkora stderr
  marad (NFP_RUNTIME_DIAG default off, CFR_DIAG default off, CONCAVE
  NFP DIAG mostantól default off), és a policy lazítása ott dönthető el
  evidence-szel.
- Az `is_concave_nfp_diag_enabled()` szándékosan szigorú: csak az `"1"`
  string ad true-t. Bármi más (`"true"`, `"yes"`, üres string) false.
  Konzisztens a `nfp_placer.rs` meglévő helpereivel (`as_deref() == Ok("1")`).
- A 4. teszteset (`"true" → false`) jelzi a jövőbeli olvasónak, hogy ne
  feltételezzen lazább szemantikát. Ez a `nfp_placer.rs` flagjeivel
  hosszabb távon összhangban marad.

## 9) Follow-ups

1. **T04 / T05 packaging waveként** — Phase 0 wave lefedéshez (engine
   stats export + polygon-aware validation gate). A T03 lezárása után
   párhuzamosan indíthatók.
2. **T06 packaging** — Phase 0 baseline aggregálás; az LV8_HARNESS_QUIET
   default policy lazítását ezen kell mérési alapra helyezni.
3. **`nfp_placer.rs` diag helpers konszolidáció (opcionális, jövőbeli)** —
   jelenleg 5 különálló helper, mind ugyanazt a mintát követi (`std::env::var(…).as_deref() == Ok("1")`).
   Ha a Phase 1+ során újabb diag flagek kerülnek be, érdemes lehet egy
   közös `env_flag_eq_one(name: &str) -> bool` helper. Most ez nem T03
   scope.
4. **Static lock vs. `serial_test` crate** — ha a repó több modulban
   szüksége lesz env-touching tesztre, érdemes egy közös serializer
   crate (pl. `serial_test`) bevezetése. Most a `static Mutex<()>`
   elegendő, és nem növeli a függőségi gráfot.
5. **Engine-szintű "diag-off" smoke teszt (jövőbeli)** — egy gyors smoke,
   ami `compute_concave_nfp_default()` hívásnál biztosítja, hogy default
   env-ben nincs `[CONCAVE NFP DIAG]` stderr. Most a 4-állapotú helper
   teszt elegendő bizonyíték; teljes integration smoke érdemi lehet, ha
   később bárki bevezet egy közvetlen `eprintln!`-t.
