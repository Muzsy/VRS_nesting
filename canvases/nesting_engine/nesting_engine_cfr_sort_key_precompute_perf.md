# canvases/nesting_engine/nesting_engine_cfr_sort_key_precompute_perf.md

> Mentés: `canvases/nesting_engine/nesting_engine_cfr_sort_key_precompute_perf.md`  
> TASK_SLUG: `nesting_engine_cfr_sort_key_precompute_perf`  
> AREA: `nesting_engine`

# CFR sort key precompute (perf): ring_hash ne comparatorban fusson

## 🎯 Funkció

A cél: a `CFR` komponensek stabil rendezésénél a sort kulcs (különösen a `ring_hash` tie-break) **ne a comparatorban számolódjon újra**, hanem **komponensenként egyszer**, “decorated sort” mintával.

Miért:
- comparatorban hash-elni tipikusan O(N log N) * hash_költség, ami sok komponensnél látványos perf büntetés,
- a determinisztika nem változik, csak a számítási helye és gyakorisága.

Nem cél:
- CFR logika, canonicalize logika, sort kulcs szemantikájának változtatása.
- új tie-break bevezetése (marad: `min_point`, `abs_area`, `vertex_count`, `ring_hash`).

---

## 🧠 Fejlesztési részletek

### 1) Érintett hely
- `rust/nesting_engine/src/nfp/cfr.rs`
  - jelenlegi komponensrendezés: `sort_components(...)` / `compare_sort_keys(...)` / `build_sort_key(...)`
  - `ring_hash_u64(...)` (vagy ekvivalens tie-break) jelenleg comparatorból is futhat.
- `docs/nesting_engine/f2_3_nfp_placer_spec.md`
  - CFR sort kulcs: `min_point`, `abs_area`, `vertex_count`, `ring_hash`
- `scripts/check.sh`
  - van célzott `can_place_` futás, de a `cfr_sort_key_` tesztfilter még nincs bekötve.

Felderítés snapshot (2026-02-28):
- A kulcsmezők jelenleg is a fenti 4 elemre épülnek (`min_point`, `abs_area`, `vertex_count`, `ring_hash`).
- A tie-break hash (`ring_hash`) jelenleg `ring_hash_u64` néven él, és a rendezési kulcs építéséhez tartozik.
- Perf kockázat: ha hash számítás comparator-útvonalba kerül, az O(N log N) összehasonlítások miatt feleslegesen többször futna ugyanarra a komponensre.

### 2) Implementációs terv (perf hardening, szemantika változtatás nélkül)

#### 2.1 Új “precomputed” kulcs típus
Vezess be egy belső sort-key típust, ami már tartalmazza az előre kiszámolt tie-breaket:

- `struct CfrComponentSortKeyV1 { min_x, min_y, abs_area, vertex_count, tiebreak_hash }`
- `Ord` / `PartialOrd` totális lexicographic rendezéssel (ugyanaz a sorrend, mint eddig).

#### 2.2 Decorated sort
Ahelyett, hogy `components.sort_by(|a,b| ...)` comparatoron belül kulcsot/hash-t számolsz:

- építs `Vec<(CfrComponentSortKeyV1, Polygon64)>` listát
- `sort_by(|(ka,_),(kb,_)| ka.cmp(kb))`
- majd visszaalakítás `Vec<Polygon64>`-ra

#### 2.3 Hash számítás “komponensenként egyszer”
Vezess be egy komponens-szintű hash függvényt (a ring_hash szemantikáját megtartva):

- `fn component_tiebreak_hash_u64(poly: &Polygon64) -> u64`
  - outer ring + holes stabil kombinációja (ugyanaz, mint eddig)
- `build_sort_key_precomputed(...)` ezt hívja **egyszer**.

### 3) Teszt: “nem számoljuk újra comparatorban”
Mivel ez perf jellegű, kell egy célzott regresszió teszt, ami bizonyítja, hogy a tie-break hash **nem N log N-szer** fut.

`#[cfg(test)]` alatt:
- vezess be egy számlálót csak tesztben: `COMPONENT_HASH_CALLS`
- a `component_tiebreak_hash_u64` (csak teszt buildben) növelje
- teszt:
  - hozz létre N darab CFR-komponenst (pl. azonos `min_point`/`abs_area`/`vertex_count`, hogy a tie-break mindenkinél “releváns” legyen)
  - hívd `sort_components(...)`
  - ellenőrzés: `component_hash_calls == N` (vagy legfeljebb N), tehát komponensenként egyszer

### 4) Gate: gyors célzott cargo test
A `scripts/check.sh` nesting_engine blokkban (ahol már van célzott teszt hívás a can_place-hez):
- adj hozzá egy új célzott futást:
  - `cargo test --manifest-path rust/nesting_engine/Cargo.toml cfr_sort_key_`

### 5) Doksi (opcionális, kicsi)
A `docs/nesting_engine/f2_3_nfp_placer_spec.md` CFR rendezés részébe egy félmondat:
- “A `ring_hash` tie-break dekorált rendezéssel előre számolódik (komponensenként egyszer), nem comparatorban.”

---

## 🧪 Tesztállapot

### DoD
- [ ] `sort_components(...)` decorated sortot használ, és a tie-break hash komponensenként egyszer készül
- [ ] Új unit teszt megvan és zöld: `cfr_sort_key_precompute_*`
- [ ] `scripts/check.sh` futtatja: `cargo test ... cfr_sort_key_`
- [ ] `./scripts/check.sh` PASS
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_cfr_sort_key_precompute_perf.md` PASS

---

## 🌍 Lokalizáció
Nem releváns.

---

## 📎 Kapcsolódások
- `rust/nesting_engine/src/nfp/cfr.rs` (komponens canonicalize + sort)
- `docs/nesting_engine/f2_3_nfp_placer_spec.md` (CFR komponens rendezés fejezet)
- `scripts/check.sh`
- F2-3 F4 determinism fixture: `poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json`
