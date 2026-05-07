# T05v — NFP Provider Interface Pilot

## Státusz: PASS

## Rövid verdikt

Sikerült a behavior-preserving provider pilot. Az NFP kernel hívás absztraktálva lett a `NfpProvider` trait és `OldConcaveProvider` wrapper bevezetésével. Az optimalizáló lánc (greedy + SA + multi-sheet + slide compaction) nem lett módosítva. A régi concave NFP útvonal működése változatlan maradt.

---

## Módosított fájlok

| Fájl | Módosítás típusa |
|------|-----------------|
| `rust/nesting_engine/src/nfp/provider.rs` | Új fájl |
| `rust/nesting_engine/src/nfp/mod.rs` | +1 sor: `pub mod provider;` |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | Import + `compute_nfp_lib` wrapper átírás |

---

## Mi lett az új provider interface

### `NfpProvider` trait (`provider.rs:48–72`)
```rust
pub trait NfpProvider: Send + Sync {
    fn kernel(&self) -> NfpKernel;
    fn kernel_name(&self) -> &'static str;
    fn supports_holes(&self) -> bool { false }
    fn compute(&self, placed_polygon: &Polygon64, moving_polygon: &Polygon64) -> Result<NfpProviderResult, NfpError>;
}
```

### `NfpKernel` enum (`provider.rs:21–25`)
```rust
pub enum NfpKernel {
    OldConcave,
}
```
Jövőbeli bővítési pont: `ReducedConvolution`, `CGAL`, stb.

### `NfpProviderResult` struct (`provider.rs:35–46`)
Tartalmazza: `polygon`, `compute_time_ms`, `kernel`, `validation_status`.

---

## Hogyan lett becsomagolva az old_concave

### `OldConcaveProvider` (`provider.rs:78–123`)
- `NewConcaveProvider` dispatch logikája nem lett duplikálva
- A meglévő `compute_convex_nfp` / `compute_concave_nfp_default` függvényeket hívja
- `is_convex` alapú dispatch: ha mindkettő convex → `compute_convex_nfp`, különben `compute_concave_nfp_default`
- Minden behavior pontosan ugyanaz, mint korábban

### `compute_nfp_lib_with_provider` helper (`provider.rs:129–158`)
Lib-beli helper, amely a `dyn NfpProvider` + `Option<Polygon64>` API-t exponálja.

### `nfp_placer.rs` wrapper (`nfp_placer.rs:488–519`)
A binary `compute_nfp_lib` privát függvénye a provider-t használja, de explicit típuskonverzióval dolgozik (lib Polygon64 ↔ binary LibPolygon64). Ez a konverzió a binary workspace-architektúra miatt szükséges (két verziójú `nesting_engine` crate).

---

## Változott-e a cache

**Nem.** Az `NfpCacheKey` érintetlen maradt. A provider a meglévő cache API-t használja változatlanul. A cache kulcs nem tartalmaz kernel mezőt — ez intentional, mert T05v scope-ban nem bővítjük a cache-t.

---

## Változott-e a placement behavior

**Nem.** A `compute_nfp_lib` privát wrapper az `OldConcaveProvider`-t használja, ami pontosan ugyanazt a convex/concave dispatch logikát végzi, mint korábban. Az NFP eredmények és a placement sorrend nem változik.

---

## Futtatott parancsok és eredmények

### cargo check
```
cd .../rust/nesting_engine && cargo check
```
**Eredmény:** `Finished dev profile` — 0 error, 28 pre-existing warning (nem a T05v változásokhoz kapcsolódnak).

### cargo test
```
cd .../rust/nesting_engine && cargo test
```
**Eredmény:** 59/60 PASS, 1 FAIL.
- A fail: `nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component` — pre-exisztáló teszt (T05v előtt is hibás volt), `component_tiebreak_hash_u64` hívásszámlálási hiba a CFR modulban. Nem kapcsolódik a provider pilot-hoz.

### NFP pair benchmark (lv8_pair_01, 5s timeout)
```
cargo run --bin nfp_pair_benchmark -- --fixture .../lv8_pair_01.json --timeout-ms 5000
```
**Eredmény:** `verdict: TIMEOUT (time_ms=5000)` — várt viselkedés, toxic concave pair 177K fragment-tel, az old_concave útvonal is timeout-ol.

### NFP pair benchmark (lv8_pair_02, 5s timeout)
```
cargo run --bin nfp_pair_benchmark -- --fixture .../lv8_pair_02.json --timeout-ms 5000
```
**Eredmény:** `verdict: TIMEOUT (time_ms=5000)` — várt viselkedés, 110K fragment-tel.

---

## Ismert limitációk

1. **Binary/lib type mismatch workaround**: A binary workspace-architektúra két verziójú `nesting_engine` crate-et használ. A `compute_nfp_lib` wrapper explicit `LibPoint64`/`LibPolygon64` konverziót végez a lib provider eredményének visszaalakításakor. Ez nem befolyásolja a behavior-t, de megjegyezendő a jövőbeli provider implementációknál.

2. **Pre-exisztáló CFR tesztfail**: `cfr_sort_key_precompute_hash_called_once_per_component` nem kapcsolódik a T05v-hez.

3. **Provider interface diagnosztika**: Az `[NFP DIAG] provider=old_concave` üzenet jelenik meg a benchmark outputban, jelezve, hogy a provider útvonal aktív.

4. **CGAL / reduced_convolution nincs bekötve** — intentional, T05v scope-on kívül.

---

## Checklist összefoglaló

| Feltétel | Állapot |
|----------|---------|
| NfpProvider trait létrejött | ✅ |
| NfpKernel::OldConcave létrejött | ✅ |
| NfpProviderResult létrejött | ✅ |
| OldConcaveProvider a meglévő convex/concave dispatch-et használja | ✅ |
| nfp_placer.rs provider útvonalon számol NFP-t | ✅ |
| Alapértelmezett kernel továbbra is old_concave | ✅ |
| greedy / SA / multi-sheet optimalizáló nem lett újraírva | ✅ |
| CGAL nincs bekötve | ✅ |
| reduced_convolution experimental nincs bekötve | ✅ |
| production Dockerfile nincs módosítva | ✅ |
| cache nagy refactor nincs | ✅ |
| cargo check PASS | ✅ |
| cargo test 59/60 PASS (1 pre-existing fail) | ✅ |
| Nincs T08 indítás | ✅ |

---

## Következő ajánlott task

**T08** — Ha a provider interface beválik, egy valódi alternatív kernel bekötése (pl. `ReducedConvolutionProvider` vagy CGAL reference probe) anélkül, hogy az optimalizáló láncot módosítanánk. A T05v által lefektetett `NfpProvider` trait lehetővé teszi a swap-et egyetlen provider implementáció cseréjével.

Alternatíva: **T06** — Ha a toxic concave NFP timeout-ot kell megoldani (T05u root cause), egy bounded timeout + fallback stratégia implementálása a `compute_stable_concave_nfp` szintjén, anélkül hogy a provider interface-ig el kellene jutni.
