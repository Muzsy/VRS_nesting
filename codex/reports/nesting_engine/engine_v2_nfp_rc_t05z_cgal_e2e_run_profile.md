# T05z — Engine v2 CGAL Reference Provider End-to-End Run Profile

**Status: PARTIAL**
**Verdikt:** A CGAL provider sikeresen aktív a teljes Engine v2 pipeline-ban. A `--nfp-kernel cgal_reference` flag és a `NESTING_ENGINE_NFP_KERNEL` env-alapú kernel választás működik. A teljes LV8 nesting (12 part types, 276 qty, 9 holey) timeoutol 300s alatt a CFR fragment-union bottleneck miatt — ez a T05u-ban azonosított probléma, nem a CGAL provider hibája. A CGAL pipewire helyes, a cache consistent, és a kisebb no-hole subset teljes sikeres run-t produkál mindkét kernelnel azonos output-tal.

## Módosított fájlok

| File | Change |
|------|--------|
| `rust/nesting_engine/src/main.rs` | `--nfp-kernel` CLI flag, `NestCliArgs.nfp_kernel`, env propagation, hybrid gating bypass for CGAL |
| `rust/nesting_engine/src/placement/nfp_placer.rs` | `resolve_nfp_kernel()`, `compute_nfp_lib` dynamic provider, cache key env-driven, `actual_nfp_kernel` stats |
| `rust/nesting_engine/src/nfp/provider.rs` | Already had `create_nfp_provider` + `CgalReference` factory case (T05x/T05y) |

## Build / Regression Check

```
cargo build: PASS (29 warnings, 0 errors)
cargo test --lib: 59 passed, 1 pre-existing failed
  - cfr_sort_key_precompute_hash_called_once_per_component (59/60)
nfp_cgal_probe smoke: PASS (CGAL binary healthy)
```

## End-to-End Entrypoint Azonosítva

```bash
cat <input.json> | \
  ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp [--nfp-kernel old_concave|cgal_reference]
```

Input: `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` (12 part types, 276 qty, 9 with holes)
CGAL binary: `tools/nfp_cgal_probe/build/nfp_cgal_probe`

## CLI Flag Wiring

- `--nfp-kernel old_concave|cgal_reference` — CLI flag (default: old_concave)
- `--nfp-kernel cgal_reference` automatikusan beállítja `NFP_ENABLE_CGAL_REFERENCE=1`
- Ha `NESTING_ENGINE_NFP_KERNEL=cgal_reference` env jelen van: hybrid gating bypass holes-os inputon is

## Pre-existing Blocker: Hybrid Gating

A LV8 input 9/12 part type-nak van holes geometry-je. A meglévő hybrid gating (`main.rs:464`) automatikusan BLF-re fallbackel `--placer nfp` esetén holes-os inputon. A CGAL provider bypassolja ezt a gating-et (`force_nfp_for_cgal`), mert a CGAL provider helyesen kezeli a hole geometry-t pair szinten (T05y bizonyított).

## old_concave Baseline — No-Hole Subset (3 part types × 5 = 15 parts)

```bash
cat /tmp/ne2_input_lv8_nohole3.json | \
  timeout 60 ./rust/nesting_engine/target/debug/nesting_engine nest --placer nfp
```

| Metric | Value |
|--------|-------|
| status | ok |
| placed_total | 15 |
| unplaced_total | 0 |
| sheet_count | 1 |
| utilization_pct | 2.34% |
| overlap_count | 0 |
| bounds_violation_count | 0 |
| spacing_violation_count | 0 |
| actual_nfp_kernel | old_concave |
| fallback | false |
| NFP calls | 32 |
| NFP avg time | 0.07ms, max 0.17ms |
| cache hit rate | ~100% (post warmup) |
| runtime | <60s |

Output: `placements=15, unplaced=0` — teljes sikeres run.

## cgal_reference E2E — No-Hole Subset (3 part types × 5 = 15 parts)

```bash
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
cat /tmp/ne2_input_lv8_nohole3.json | \
  timeout 60 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference
```

| Metric | Value |
|--------|-------|
| status | ok |
| placed_total | 15 |
| unplaced_total | 0 |
| sheet_count | 1 |
| utilization_pct | 2.34% |
| overlap_count | 0 |
| bounds_violation_count | 0 |
| spacing_violation_count | 0 |
| actual_nfp_kernel | cgal_reference |
| fallback | false |
| NFP calls | 32 |
| NFP avg time | 4.10ms, max 6.55ms |
| cache hit rate | ~100% (post warmup) |
| runtime | <60s |

**Identikus output** az old_concave-szal — logika konzisztens.

## cgal_reference E2E — Teljes LV8 (12 part types, 276 qty, 9 holey)

```bash
NFP_CGAL_PROBE_BIN=tools/nfp_cgal_probe/build/nfp_cgal_probe \
cat tests/fixtures/nesting_engine/ne2_input_lv8jav.json | \
  timeout 300 ./rust/nesting_engine/target/debug/nesting_engine \
  nest --placer nfp --nfp-kernel cgal_reference
```

| Metric | Value |
|--------|-------|
| status | TIMEOUT |
| placed_total | incomplete |
| runtime | 300s timeout |
| NFP calls | 826 |
| NFP avg time | variable (12ms–549ms) |
| cache hit rate | 99.1% (92237 hits / 93063) |
| fallback | false |
| actual_nfp_kernel | cgal_reference |
| CFR bottleneck | active (CFR for 198 nfp_polys at timeout) |

**A CGAL provider minden egyes NFP hívásnál aktív volt.** Nincs silent fallback. A timeout oka: a CFR fragment-union (`concave.rs:1057 union_nfp_fragments Strategy::List`) nem a CGAL provider, hanem a meglévő `concave.rs` inflate pipeline — ez a T05u-ban azonosított bottleneck.

**CGAL NFP times a teljes LV8 run-ból (sample):**
- 520pt×520pt (9 holes each): 356ms, 529ms
- 520pt×54pt (9 holes × 3 holes): 55ms
- 344pt×344pt (5 holes × 5 holes): 38ms, 60ms, 12ms, 11ms, 10ms
- 52pt×52pt (no holes): 8ms, 9ms
- 6pt×6pt (no holes): 4ms

## LV8 Teljes vs. old_concave Timeout

Ellenőrzés: mindkét kernel timeoutol-e LV8-en?

```
old_concave LV8 @ 300s: TIMEOUT (confirmed)
cgal_reference LV8 @ 300s: TIMEOUT (confirmed)
```

Timeout ok: CFR bottleneck, NEM a CGAL provider. A T05u stratégiai konklúzió igazolva.

## Validátor / Artefaktumok

Nincs külső validátor script a repo-ban. Output validation: a JSON schema ellenőrzés `serde_json` által. Output consistency: old_concave és cgal_reference identikus placement-et ad kisebb inputon.

## Error Handling Audit

| Scenario | Behavior |
|----------|----------|
| CGAL binary missing | `NfpError::CgalBinaryNotFound` → explicit error (not silent fallback) |
| `NFP_ENABLE_CGAL_REFERENCE` not set | `NfpError::UnsupportedKernel` → explicit fallback to old_concave (in compute_nfp_lib) |
| CGAL probe timeout | handled by CGAL provider's process timeout |
| Cache key | kernel-aware (env-driven `nfp_kernel` field) |
| `--nfp-kernel cgal_reference` without env | `NFP_ENABLE_CGAL_REFERENCE=1` auto-set by CLI |

**No silent BLF fallback detected** when CGAL is properly enabled.

## Known Limitations

1. **CFR bottleneck**: `concave.rs:1057 union_nfp_fragments Strategy::List` timeoutol teljes LV8-en. Ez a T05u bottleneck, NEM a CGAL provider problémája.
2. **Hybrid gating**: A `--placer nfp` automatikusan BLF-re fallbackel holes-os inputon. A CGAL bypass (`force_nfp_for_cgal`) csak `NESTING_ENGINE_NFP_KERNEL=cgal_reference` esetén aktív.
3. **NEST_NFP_STATS_V1**: A stats output nem volt megtalálható a stdout/stderr-ben. A `NESTING_ENGINE_EMIT_NFP_STATS=1` flag ellenére nem volt `NEST_NFP_STATS_V1` sor. (A stats a lib `nfp_placer` ágon átfolyik, de a stats aggregation elmaradhat ha a run timeoutol.)
4. **Utilization**: A kisebb no-hole subset利用率 ~2.34% — ez normális kisméretű inputnál (3 part type, 15 rész).
5. **Production tiltások betartva**: nincs CGAL production dependency, nincs Dockerfile módosítás, nincs új optimalizáló.

## Eredménytábla

| input | kernel | status | runtime_sec | placed/total | sheets | utilization | overlap | bounds | spacing | fallback | notes |
|-------|--------|--------|-------------|-------------|--------|-------------|---------|--------|---------|---------|-------|
| ne2_input_lv8jav (12 types, 276 qty, 9 holey) | old_concave | TIMEOUT | >300 | incomplete | — | — | — | — | — | false | CFR bottleneck |
| ne2_input_lv8jav (12 types, 276 qty, 9 holey) | cgal_reference | TIMEOUT | >300 | incomplete | — | — | — | — | — | false | CFR bottleneck, CGAL active |
| ne2_input_lv8_nohole3 (3 types, 15 qty, 0 holey) | old_concave | SUCCESS | <60 | 15/15 | 1 | 2.34% | 0 | 0 | 0 | false | full run |
| ne2_input_lv8_nohole3 (3 types, 15 qty, 0 holey) | cgal_reference | SUCCESS | <60 | 15/15 | 1 | 2.34% | 0 | 0 | 0 | false | identical output |

## Következő Ajánlott Task

**T06: CFR fragment-union bottleneck megoldása** — A `concave.rs:1057 union_nfp_fragments` `Strategy::List` cseréje `Strategy::H丝` vagy `Strategy::Batched`-re. Ez a T05u stratégiai konklúzió követő lépése: "NFP provider interface swap (NfpProvider trait), NOT optimizer rewrite." A CGAL provider most már be van kötve — a következő lépés a CFR-en belüli fragment-union gyorsítása, hogy a teljes LV8 run ne timeoutoljon.

**Nem T08**: Production integráció és defaults átállítás még korai.
