# LV8 Density T03 — Phase 0 NFP diagnostic stderr env-gate

## 🎯 Funkció

A feladat célja a Phase 0 mérési higiénia részeként a `rust/nesting_engine/src/nfp/concave.rs` fájlban található `[CONCAVE NFP DIAG]` diagnosztikai `eprintln!` sorok alapértelmezett kikapcsolása. A jelenlegi állapotban ezek a sorok hosszú LV8 futások alatt nagy stderr mennyiséget termelhetnek, és a benchmark harness emiatt külön `/dev/null` kerülőutat használ.

A T03 **nem algoritmusfejlesztés**, nem cache-refaktor, nem benchmark-run task. Kizárólag a diagnosztikai kimenet env-gate-elése, az ehhez kapcsolódó minimális teszt/report, és a harness-komment/policy audit a cél.

## Forrás és döntések

A T03 a végleges `codex/reports/nesting_engine/development_plan_packing_density_20260515.md` v2.2 terv Phase 0.2 pontjára épül. A terv tartalmát nem szabad módosítani.

A T03-ba beépített végleges döntések:

- A kapcsoló neve: `NESTING_ENGINE_NFP_DIAG`.
- Default állapot: off, vagyis a `[CONCAVE NFP DIAG]` sorok nem jelennek meg.
- Opt-in állapot: `NESTING_ENGINE_NFP_DIAG=1`, ilyenkor a jelenlegi diagnosztikai sorok továbbra is megjelenhetnek.
- A diagnosztika csak nyomtatást befolyásolhat, algoritmikus döntést, statisztikát, geometriát, NFP eredményt nem.
- A `nfp_placer.rs` már tartalmaz külön hot-path diag gate-eket, például `NESTING_ENGINE_NFP_RUNTIME_DIAG` és `NESTING_ENGINE_CFR_DIAG`; ezeket T03-ban nem szabad összemosni a concave diag flaggel.

## Valós repo-kiindulópontok a friss snapshot alapján

A T03 előtt ellenőrzött releváns állapot:

- `rust/nesting_engine/src/nfp/concave.rs`
  - `compute_concave_nfp_default()` elején közvetlen `[CONCAVE NFP DIAG] ENTRY` `eprintln!` található.
  - `compute_stable_concave_nfp()` több közvetlen `[CONCAVE NFP DIAG]` `eprintln!` sort tartalmaz:
    - `decompose_done`
    - `partial_nfp`
    - `partial_nfp_done`
    - `union_done`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
  - Már tartalmaz hot-path diagnosztikai gate-eket:
    - `is_nfp_runtime_diag_enabled()` → `NESTING_ENGINE_NFP_RUNTIME_DIAG=1`
    - `is_cfr_diag_enabled()` → `NESTING_ENGINE_CFR_DIAG=1`
    - `is_candidate_diag_enabled()` → `NESTING_ENGINE_CANDIDATE_DIAG=1`
    - `is_hybrid_cfr_diag_enabled()` → `NESTING_ENGINE_HYBRID_CFR_DIAG=1`
  - Ezeket T03-ban csak auditálni kell.
- `scripts/experiments/lv8_2sheet_claude_search.py`
  - `LV8_HARNESS_QUIET=1` esetén stderr-t `/dev/null`-ba dob, jelenlegi komment szerint a `[CONCAVE NFP DIAG]` spam miatt.
  - T03-ban ezt legfeljebb komment/policy szinten lehet pontosítani; a hosszú benchmark-harness viselkedésének érdemi átírása T06 feladata.
- T02 report státusza PASS, tehát a shadow profile előkészítés elkészült.

## T03 scope

### T03 feladata

1. `concave.rs`-ben létrehozni egy egyértelmű helper függvényt, például:

   ```rust
   fn is_concave_nfp_diag_enabled() -> bool {
       std::env::var("NESTING_ENGINE_NFP_DIAG").as_deref() == Ok("1")
   }
   ```

2. Minden `[CONCAVE NFP DIAG]` `eprintln!` sort ennek a helpernek a gate-je mögé tenni.
3. Ügyelni arra, hogy default off állapotban ne történjen felesleges formázás / többletmunka a hot pathon.
4. Unit vagy célzott Rust teszttel ellenőrizni, hogy a flag parser helyesen működik.
5. Auditálni és reportban rögzíteni, hogy a `nfp_placer.rs` egyéb diag flagjei már külön gate-ek alatt vannak, és T03 nem nyúlt hozzájuk.
6. Auditálni a benchmark harness stderr policy-t. Ha szükséges, csak kommentet vagy marker szöveget pontosítani; érdemi benchmark policy változás T06-ra marad.
7. T03 checklist és report létrehozása Report Standard v2 szerint.

### T03 nem célja

- Nem változtat NFP algoritmust.
- Nem módosít cache logikát.
- Nem módosít `NfpCache` vagy `NfpCacheKey` struktúrát.
- Nem implementál Phase 2 scoringot, Phase 3 lookaheadet, Phase 4 beamet vagy Phase 5 LNS-t.
- Nem futtat hosszú LV8 benchmarkot.
- Nem törli vagy refaktorálja a `search/sa.rs` modult.
- Nem vezeti be az engine stats exportot; az T04 feladata.
- Nem implementál polygon-aware validátort; az T05 feladata.
- Nem véglegesíti a T06 shadow run hard-cut döntést.

## Engedélyezett módosítások

A T03 futása legfeljebb ezeket a fájlokat hozhatja létre vagy módosíthatja:

- `rust/nesting_engine/src/nfp/concave.rs`
- `scripts/experiments/lv8_2sheet_claude_search.py` — csak komment / marker policy pontosítás, ha indokolt.
- `codex/codex_checklist/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
- `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md`
- `codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.verify.log`

Tilos más production fájl módosítása. Ha teszt hozzáadása csak új Rust integration test fájlban oldható meg, akkor a YAML-t előbb frissíteni kell, és a reportban indokolni kell, miért nem elég a `concave.rs` belső unit teszt.

## Implementációs irány

### 1) Helper hozzáadása

A `concave.rs` elején vagy a `compute_concave_nfp_default()` közelében add hozzá:

```rust
fn is_concave_nfp_diag_enabled() -> bool {
    std::env::var("NESTING_ENGINE_NFP_DIAG").as_deref() == Ok("1")
}
```

Ha a repo stílusa indokolja, a helper lehet `#[inline]`.

### 2) Eprintln gate-elés

Minden közvetlen `[CONCAVE NFP DIAG]` sor ilyen mintát kövessen:

```rust
let diag_enabled = is_concave_nfp_diag_enabled();
if diag_enabled {
    eprintln!("[CONCAVE NFP DIAG] ...", ...);
}
```

Ahol ciklusban sokszor fut, a `diag_enabled` lokális bool legyen a ciklus előtt kiszámolva, ne minden iterációban olvasson env-et.

### 3) Tesztelés

Ha a helper privát marad, tegyél `#[cfg(test)]` modult a `concave.rs` végére, amely legalább a flag parser viselkedését ellenőrzi.

Javasolt teszt-szemantika:

- Env unset → helper false.
- `NESTING_ENGINE_NFP_DIAG=0` → helper false.
- `NESTING_ENGINE_NFP_DIAG=1` → helper true.

A tesztnek vissza kell állítania az env állapotot, hogy ne szivárogjon más tesztekre.

### 4) Harness komment / marker audit

A `scripts/experiments/lv8_2sheet_claude_search.py` stderr policy-je jelenleg a diag spam miatt dobja el a stderr-t quiet módban. T03 után a spam default off, de a quiet policy maradhat konzervatív.

Elfogadott T03 megoldás:

- Vagy nem módosítod a scriptet, és reportban rögzíted, hogy T06 dönt majd a quiet policy lazításáról.
- Vagy csak a komment/marker szöveget pontosítod úgy, hogy a quiet policy általános log-size védelem, és a `[CONCAVE NFP DIAG]` mostantól opt-in.

Nem elfogadott:

- Hosszú benchmark policy átírása.
- Quiet default megváltoztatása bizonyító benchmark nélkül.

## Minimális célzott ellenőrzések

### Grep check: minden concave diag gate alatt

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('rust/nesting_engine/src/nfp/concave.rs')
text = p.read_text(encoding='utf-8')
assert 'fn is_concave_nfp_diag_enabled()' in text, 'missing diag helper'
assert 'NESTING_ENGINE_NFP_DIAG' in text, 'missing env flag'
# A durva grep csak azt ellenőrzi, hogy nem maradt nyers diag sor helper nélkül.
for idx, line in enumerate(text.splitlines(), start=1):
    if '[CONCAVE NFP DIAG]' in line:
        window = '\n'.join(text.splitlines()[max(0, idx-6):idx+2])
        assert 'diag_enabled' in window or 'is_concave_nfp_diag_enabled' in window, f'ungated diag near line {idx}'
print('T03 concave diag grep PASS')
PY
```

### Rust check

```bash
cargo check -p nesting_engine
```

### Célzott Rust test

Ha belső unit teszt készült `concave.rs` alatt:

```bash
cargo test -p nesting_engine concave_nfp_diag -- --nocapture
```

Ha más tesztnév készült, a reportban pontosan rögzíteni kell.

### Full repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md
```

## Definition of Done

A T03 akkor PASS, ha:

1. `NESTING_ENGINE_NFP_DIAG` helper létezik a `concave.rs`-ben.
2. Minden `[CONCAVE NFP DIAG]` `eprintln!` gate mögött van.
3. Default off állapotban nincs concave diag stderr spam.
4. `NESTING_ENGINE_NFP_DIAG=1` mellett a diagnosztikai sorok elérhetőek maradnak.
5. A változás nem befolyásol geometriát, NFP eredményt, cache-t, scoringot vagy placement döntést.
6. A `nfp_placer.rs` meglévő hot-path diag gate-jei auditálva és reportban rögzítve vannak, módosítás nélkül.
7. A benchmark harness stderr policy auditálva van; ha módosult, csak komment/marker szinten.
8. `cargo check -p nesting_engine` zöld.
9. Célzott diag helper teszt zöld, vagy a report indokolja, miért grep + cargo check a minimum.
10. `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t03_phase0_nfp_diag_gate.md` zöld.
11. Checklist és report elkészült Report Standard v2 szerint.

## Report elvárás

A reportban külön szerepeljen:

- Mely `[CONCAVE NFP DIAG]` sorokat gate-elted.
- A helper pontos neve és env flagje.
- A `nfp_placer.rs` meglévő diag gate audit eredménye.
- A harness stderr policy döntés: változott / nem változott, indokkal.
- Futott parancsok és eredmények.
- DoD → Evidence Matrix a fenti DoD pontokra 1:1-ben.

