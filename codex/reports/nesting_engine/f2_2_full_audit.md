# F2-2 Full Compliance Audit (Concave NFP)

**Audit type:** code + functionality + determinism + evidence (audit-only)  
**Date:** 2026-02-25  
**Overall verdict:** **FAIL** (P0 hianyossagok vannak)

## Scope & Inputs

### Anchor inputs (requested)

- EXISTS `canvases/nesting_engine/nesting_engine_backlog.md`
- EXISTS `canvases/nesting_engine/nfp_computation_concave.md`
- EXISTS `canvases/nesting_engine/nfp_concave_integer_union.md`
- EXISTS `canvases/nesting_engine/nfp_concave_orbit_next_event.md`
- EXISTS `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`
- EXISTS `rust/nesting_engine/src/nfp/concave.rs`
- EXISTS `rust/nesting_engine/src/nfp/boundary_clean.rs`
- EXISTS `rust/nesting_engine/src/nfp/mod.rs`
- EXISTS `rust/nesting_engine/src/nfp/convex.rs`
- EXISTS `rust/nesting_engine/src/nfp/cache.rs`
- EXISTS `rust/nesting_engine/src/geometry/types.rs`
- EXISTS `poc/nfp_regression/README.md`
- EXISTS `rust/nesting_engine/tests/nfp_regression.rs`
- EXISTS `rust/nesting_engine/tests/nfp_no_float_overlay.rs`
- EXISTS `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs`
- EXISTS `docs/nesting_engine/json_canonicalization.md`
- EXISTS `rust/nesting_engine/src/main.rs`
- EXISTS `poc/nesting_engine/sample_input_v2.json`
- EXISTS `scripts/smoke_nesting_engine_determinism.sh`
- EXISTS `scripts/check.sh`
- EXISTS `scripts/verify.sh`
- EXISTS `docs/codex/report_standard.md`

**Hianyzo horgonyfajl:** **NINCS**

### F2-2 relevans reportok (codex/reports/nesting_engine)

- `codex/reports/nesting_engine/nfp_computation_concave.md` - `PASS_WITH_NOTES`, AUTO_VERIFY PASS (`:91`)
- `codex/reports/nesting_engine/nfp_concave_integer_union.md` - `PASS_WITH_NOTES`, AUTO_VERIFY PASS (`:81`)
- `codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` - `PASS_WITH_NOTES`, AUTO_VERIFY PASS (`:88`)
- `codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md` - `PASS_WITH_NOTES`, AUTO_VERIFY PASS (`:93`)
- `codex/reports/nesting_engine/bcd_orbit_determinism_fuzz.md` - `PASS_WITH_NOTES`, AUTO_VERIFY PASS (`:77`)
- `codex/reports/nesting_engine/nfp_fixture_expansion.md` - `PASS_WITH_NOTES`, AUTO_VERIFY PASS (`:101`)
- tamogato baseline reportok: `nfp_computation_convex.md`, `nfp_convex_edge_merge_fastpath.md`

### Audit futasok (ebben a korben)

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression --test nfp_no_float_overlay --test orbit_next_event_trace_smoke` -> PASS
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml` -> PASS
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml determinism_hash_is_stable` -> PASS
- `./scripts/check.sh` -> PASS
- `RUNS=50 INPUT_JSON=/tmp/sample_input_v2_fast_audit.json ./scripts/smoke_nesting_engine_determinism.sh` -> PASS (`50/50 byte-identical`)

---

## Backlog DoD megfeleloseg (F2-2)

| DoD pont | Status | Evidence | Auditor megjegyzes |
|---|---|---|---|
| >=5 concave fixture PASS (touching/slit/hole/interlock/multi-contact) | PASS | `poc/nfp_regression/concave_touching_group.json:1`, `poc/nfp_regression/concave_slit.json:1`, `poc/nfp_regression/concave_hole_pocket.json:1`, `poc/nfp_regression/concave_interlock_c.json:1`, `poc/nfp_regression/concave_multi_contact.json:1`; teszt: `rust/nesting_engine/tests/nfp_regression.rs:96`, min. darabszam assert `rust/nesting_engine/tests/nfp_regression.rs:109-113` | A 5 kovetelt tema konkret fixture-rel bent van es futott tesztben PASS. |
| NFP boundary valid (nincs self-intersection, nincs degeneralt el) | PASS | `rust/nesting_engine/src/nfp/boundary_clean.rs:15-35`, `rust/nesting_engine/src/nfp/boundary_clean.rs:38-66`, `rust/nesting_engine/src/nfp/boundary_clean.rs:101-145`; regresszio check: `rust/nesting_engine/tests/nfp_regression.rs:175-178` | `clean_polygon_boundary` canonicalizal + self-intersection tiltast ad; regresszio explicit ellenorzi. |
| 3 valos DXF parra helyes NFP | **FAIL** | Elvart parok csak dokumentalva: `canvases/nesting_engine/nfp_computation_concave.md:178-182`; DXF smoke-ok NFP-validacio nelkul: `scripts/check.sh:146-150`; NFP regression fixture source csak `poc/nfp_regression`: `rust/nesting_engine/tests/nfp_regression.rs:343-356` | Automatizalt, NFP-helyesseget bizonyito DXF->NFP proof nem talalhato. Ez backlog-DoD gap. |
| Regresszios keszlet `poc/nfp_regression/` alatt | PASS | `poc/nfp_regression/README.md:1-35`, fixture loader `rust/nesting_engine/tests/nfp_regression.rs:349-356` | Keszlet letezik, teszt futtatja. |
| verify wrapper PASS (log evidence) | PASS | AUTO_VERIFY blokkok: `nfp_computation_concave.md:91`, `nfp_concave_integer_union.md:81`, `nfp_concave_orbit_next_event.md:88`, `nfp_concave_orbit_no_silent_fallback.md:93` | F2-2 task reportok verify PASS allapotban vannak. |

---

## Kotelezo elvek megfelelosege

| Elv | Status | Evidence | Auditor megjegyzes |
|---|---|---|---|
| Stable baseline = decomposition + convex Minkowski + union + clean (default) | PASS | default branch: `rust/nesting_engine/src/nfp/concave.rs:213-221`, stable pipeline: `rust/nesting_engine/src/nfp/concave.rs:254-278`; convex Minkowski: `rust/nesting_engine/src/nfp/convex.rs:5-102` | A default utvonal stabil baseline-ra megy. |
| Orbit exact felulrol, nem csak konstans fallback | PASS_WITH_NOTES | Exact mode branch: `rust/nesting_engine/src/nfp/concave.rs:280-290`; outcome tipusok: `rust/nesting_engine/src/nfp/concave.rs:197-211`; legalabb egy prefer_exact ExactClosed fixture: `poc/nfp_regression/concave_interlock_c.json:9-11`, tesztag `rust/nesting_engine/tests/nfp_regression.rs:209-258` | Nem "always fallback". Viszont prefer_exact coverage minosegi hiany (lasd P0-2). |
| Touching-group multi-contact stabilitas | PASS | `rust/nesting_engine/src/nfp/concave.rs:1216-1285` (komponens-epites + determinisztikus valasztas), trace smoke multi-contact: `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs:60-102` | Multi-contact stabilitast kod + golden trace vedi. |
| i128 orientacio/cross dontesek | PASS | `rust/nesting_engine/src/geometry/types.rs:24-30`; `rust/nesting_engine/src/nfp/concave.rs:583-585`, `rust/nesting_engine/src/nfp/concave.rs:852-858`, `rust/nesting_engine/src/nfp/concave.rs:903-911`, `rust/nesting_engine/src/nfp/concave.rs:1429-1434`, `rust/nesting_engine/src/nfp/concave.rs:1527`, `rust/nesting_engine/src/nfp/concave.rs:1619-1637`; `rust/nesting_engine/src/nfp/boundary_clean.rs:122-129`, `rust/nesting_engine/src/nfp/boundary_clean.rs:175-183` | Core geometriai predikatumok i128-on futnak. |
| f64 PIP elkerulese core dontesekben | PASS | `rg` alapjan nincs `f64` a core nfp modulban; integer PIP: `rust/nesting_engine/src/nfp/concave.rs:1146-1181`, strict PIP: `rust/nesting_engine/src/nfp/concave.rs:1599-1643`; float overlay tiltas teszt: `rust/nesting_engine/tests/nfp_no_float_overlay.rs:1-12` | Core NFP dontesek integeresek. |
| boundary_clean kotelezo + canonical output | PASS | stable return: `rust/nesting_engine/src/nfp/concave.rs:277`; exact-closed return elott clean: `rust/nesting_engine/src/nfp/concave.rs:385-388`; boundary canonical rules: `rust/nesting_engine/src/nfp/boundary_clean.rs:5-14`, `rust/nesting_engine/src/nfp/boundary_clean.rs:22-29`, `rust/nesting_engine/src/nfp/boundary_clean.rs:148-159` | Visszaadott polygonok canonicalized-ek (success pathon). |
| SVGNest-bol csak allapotgep-logika (code-port tiltas) | PASS_WITH_NOTES | nincs code reference: `rg` talalat 0 `SVGNest|Deepnest` a `rust/nesting_engine/src` es `tests` alatt | Forraseredet nem bizonyithato, de direkt kodport nyoma nem talalhato. |

---

## Orbit next-event audit

| Kerdes | Status | Evidence | Auditor valasz |
|---|---|---|---|
| Van-e tenyleges next-event szamitas (`t>0`, event kind, tie-break)? | PASS | `rust/nesting_engine/src/nfp/concave.rs:473-564` (next event), `rust/nesting_engine/src/nfp/concave.rs:585` (`Fraction::positive`), `rust/nesting_engine/src/nfp/concave.rs:719-724` (event tie-break), `rust/nesting_engine/src/nfp/concave.rs:1422-1443` (direction tie-break) | Igen, explicit rational event engine van. |
| Van-e deterministic trace smoke (1-3 dontes)? | PASS | trace API: `rust/nesting_engine/src/nfp/concave.rs:228-244`, trace mezok: `rust/nesting_engine/src/nfp/concave.rs:55-63`; smoke teszt: `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs:17-103`, assert mezok: `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs:146-180` | Igen, ket fixture-en 3 lepeses golden prefix ellenorzes van. |
| Visszacsuszas unit-step/gcd botorkalasra? | PASS | gcd csak irany-normalizalas: `rust/nesting_engine/src/nfp/concave.rs:1411-1419`; lepeshossz event-t alapjan: `rust/nesting_engine/src/nfp/concave.rs:647-665` | Nem unit-step; a lepes `v*t` szerint megy. |
| no-silent-fallback teljesul? | PASS | no-fallback hiba-visszaadas: `rust/nesting_engine/src/nfp/concave.rs:287-290`, `rust/nesting_engine/src/nfp/concave.rs:423-431`; teszt: `rust/nesting_engine/src/nfp/concave.rs:1731-1756` | `enable_fallback=false` eseten explicit Err, nem stable `Ok`. |
| prefer_exact fixture-ek legalabb 3 esetben `ExactClosed`-ot adnak? | **FAIL** | DoD elvaras: `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md:130-132`; fixture policy: `poc/nfp_regression/concave_touching_group.json:9-11`, `poc/nfp_regression/concave_hole_pocket.json:9-11`, `poc/nfp_regression/concave_interlock_c.json:9-11`; tesztag: `rust/nesting_engine/tests/nfp_regression.rs:192-258` | Jelenleg 3 prefer_exact fixture-bol 2 explicit `expect_exact_error=true`, csak 1 `ExactClosed`. A canvas DoD szigoran nem teljesul. |

Prefer_exact allapot (objektiv):

- `concave_touching_group.json`: `expect_exact_error=true` (`poc/nfp_regression/concave_touching_group.json:9-11`)
- `concave_hole_pocket.json`: `expect_exact_error=true` (`poc/nfp_regression/concave_hole_pocket.json:9-11`)
- `concave_interlock_c.json`: `expect_exact_error=false` (`poc/nfp_regression/concave_interlock_c.json:9-11`)

---

## Determinizmus audit (lib + CLI)

| Terulet | Status | Evidence | Auditor valasz |
|---|---|---|---|
| Lib: canonical ring byte-azonos osszehasonlitas teszttel vedve | PASS | `rust/nesting_engine/tests/nfp_regression.rs:168-173`, `rust/nesting_engine/tests/nfp_regression.rs:233-241`, canonical ring helper `rust/nesting_engine/tests/nfp_regression.rs:378-400` | Van explicit 2x futasos canonical ring egyezes ellenorzes stable es exact agban. |
| Lib: canonical JSON byte-azonos osszehasonlitas teszttel vedve | PASS_WITH_NOTES | van hash stabilitas teszt: `rust/nesting_engine/src/export/output_v2.rs:136-160`; canonical bytes explicit compare nincs | Kozvetlen canonical JSON string-byte unit teszt nem talalhato, csak hash-stabilitas ellenorzes. |
| CLI: 50x canonical JSON smoke letezik | PASS | script: `scripts/smoke_nesting_engine_determinism.sh:8`, `:52-67`, `:70`; canonicalizer: `scripts/canonicalize_json.py:96-120` | Igen, byte-szintu `cmp` alapu smoke megvan. |
| CLI: 50x smoke audit futas | PASS | audit run output: `[OK] determinism smoke passed (50/50 canonical outputs are byte-identical)` (RUNS=50, `INPUT_JSON=/tmp/sample_input_v2_fast_audit.json`) | Ebben az auditban 50/50 pass lefutott (gyorsitott input idokorlattal). |
| CLI 50x smoke gate-be integralva (`check.sh`/`verify.sh`) | PASS_WITH_NOTES | `rg` talalat 0 `smoke_nesting_engine_determinism` a `scripts/check.sh`, `scripts/verify.sh` fajlokban | A smoke script letezik, de nem kotelezo gate lepese. |

**P0 trigger ellenorzes (user rule):** 50x canonical smoke **letezik**, ezert itt **nem** keletkezik P0 hianyossag.

---

## Fuzz / fixtures audit

| Kerdes | Status | Evidence | Auditor valasz |
|---|---|---|---|
| Van-e celzott fuzz script (stdlib-only)? | PASS | `scripts/fuzz_nfp_regressions.py:1-5`, parser + generation: `:126-178` | Igen, stdlib-only script. |
| Van-e quarantine flow? | PASS_WITH_NOTES | quarantine naming: `scripts/fuzz_nfp_regressions.py:160-173`; policy leiras: `codex/reports/nesting_engine/bcd_orbit_determinism_fuzz.md:67-72` | Quarantine naming es policy megvan, de acceptance formalizalasa report-szintu. |
| Hany uj fixture + tipus | PASS | `poc/nfp_regression/quarantine_generated_20260225_20260225_near_parallel.json`, `..._sliver_gap.json`, `..._collinear_dense.json` | 3 uj "boss-fight" fixture bent van (near_parallel, sliver_gap, collinear_dense). |
| Suite stabilan fut-e? | PASS | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` PASS (audit run); loader minden `.json`-t vesz: `rust/nesting_engine/tests/nfp_regression.rs:349-356` | A jelenlegi fixture halmazzal regresszio PASS. |

**Megjegyzes (audit-only szabaly):** a fuzz script futtatasa uj/valtozo fixture fajlokat irna, ezert ebben a korben nem futtattam.

---

## Kockazatlista es prioritas

### P0 - Kotelezo javitando

1. **F2-2 DoD gap: nincs automatizalt proof 3 valos DXF par NFP-helyessegere.**
   - Evidence: `nfp_computation_concave` csak dokumentalt parlistat ad (`canvases/nesting_engine/nfp_computation_concave.md:178-182`), nincs dedikalt DXF->NFP expected check a tesztekben (`rust/nesting_engine/tests/nfp_regression.rs:343-356`).
   - Mi romlik, ha nem javitjuk: F2-2 DoD allitas nem objektiven bizonyithato, valos geometrian regresszio rejtve maradhat.
   - Minimalis, dependency-mentes potlas (uj P0 task): 3 fix DXF-parbol exportalt integer polygon fixture (`.json`) + dedikalt Rust integration teszt, ami canonical ringet hasonlit expected-del.

2. **ExactOrbit quality gap: prefer_exact >=3 `ExactClosed` elvaras nem teljesul.**
   - Evidence: canvas elvaras `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md:130-132`; jelen fixture policy 2 hibara van allitva (`poc/nfp_regression/concave_touching_group.json:11`, `poc/nfp_regression/concave_hole_pocket.json:11`), csak 1 sikeres `ExactClosed` marad.
   - Mi romlik, ha nem javitjuk: az "ExactOrbit" gyakorlati quality target nem igazolhato, nehez megbizhato exact modra epiteni.
   - Minimalis, dependency-mentes potlas (uj P0 task): legalabb 3 prefer_exact fixture-en kotelezo `ExactClosed` assert (hiba-elfogadas nelkul), es tesztpolicy visszaallitasa erre.

### P1 - Erosen ajanlott

1. **Lib canonical JSON byte-level teszt hianya.**
   - Evidence: `output_v2` teszt hash-egyezest nez (`rust/nesting_engine/src/export/output_v2.rs:136-160`), de canonical JSON bytes explicit assert nincs.
   - Mi romlik, ha nem javitjuk: canonicalization regresszio hash-szinten nehezebben lokalizalhato.

2. **Spec drift kockazat: RFC8785 (JCS) dokumentalt, de implementacio "sorted json".**
   - Evidence: normativ doc `docs/nesting_engine/json_canonicalization.md:28-31`; Python canonicalizer `json.dumps(... sort_keys=True ...)` (`scripts/canonicalize_json.py:119`); Rust hash-view `serde_json::to_string` (`rust/nesting_engine/src/export/output_v2.rs:124`).
   - Mi romlik, ha nem javitjuk: cross-language hash kompatibilitas bizonytalan lehet.

3. **50x CLI determinism smoke nincs a kotelezo gate-ben.**
   - Evidence: `scripts/check.sh`/`verify.sh` nem hivja a scriptet.
   - Mi romlik, ha nem javitjuk: manual futtatas hianya eseten determinism drift keson derul ki.

4. **Quarantine acceptance folyamat nincs repo-levelen formalizalva README-ben.**
   - Evidence: `poc/nfp_regression/README.md` nem tartalmaz acceptance workflow-t; policy inkabb reportban van (`bcd_orbit_determinism_fuzz.md:67-72`).
   - Mi romlik, ha nem javitjuk: fixture allapotkezeles (quarantine -> accepted) inkonzisztens lehet.

### P2 - Ajanlott

1. **NFP modulhoz kapcsolodo dead_code warningok a bin targetben.**
   - Evidence: audit futasok warning outputja (`cross_product_i128`, `signed_area2_i128`, `is_ccw`, `is_convex`).
   - Mi romlik, ha nem javitjuk: zajos build output, de funkcionalis blokkolo hatas nincs.

---

## Futtathato parancsok (audit reprodukcio)

### A) Core F2-2 tesztek

```bash
cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression --test nfp_no_float_overlay --test orbit_next_event_trace_smoke
cargo test --manifest-path rust/nesting_engine/Cargo.toml
cargo test --manifest-path rust/nesting_engine/Cargo.toml determinism_hash_is_stable
```

### B) Repo gate

```bash
./scripts/check.sh
```

### C) Verify log ellenorzes (meglevo F2-2 reportokra)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md
```

### D) CLI determinism smoke (canonical JSON)

```bash
./scripts/smoke_nesting_engine_determinism.sh
```

Gyors audit varians (repo fajlmodositas nelkul, /tmp input):

```bash
python3 - <<'PY'
import json
from pathlib import Path
src=Path('poc/nesting_engine/sample_input_v2.json')
out=Path('/tmp/sample_input_v2_fast_audit.json')
data=json.loads(src.read_text())
data['time_limit_sec']=1
out.write_text(json.dumps(data), encoding='utf-8')
print(out)
PY
RUNS=50 INPUT_JSON=/tmp/sample_input_v2_fast_audit.json ./scripts/smoke_nesting_engine_determinism.sh
```

### E) Fuzz / quarantine flow (figyelem: fixture fajlokat ir)

```bash
python3 scripts/fuzz_nfp_regressions.py --seed 20260225 --count 3
cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression
```

---

## Audit zaro osszegzes

- **A (concave core):** nagyreszt stabil es tesztelt, integer baseline + boundary clean rendben.
- **B (orbit next-event):** implementalt es trace-smoke bizonyitott, de a prefer_exact `ExactClosed` coverage a canvas-kovetelmenyt nem eri el.
- **C (determinism):** canonical ring determinisztika jo; CLI canonical JSON 50x smoke letezik es futtathato; lib canonical JSON byte-level teszt hianyos.
- **D (fuzz/fixtures):** celzott stdlib fuzz + quarantine jelen van, 3 boss-fight fixture bent, regresszio suite jelen allapotban stabil.

**Kovetkeztetes:** F2-2 csomag jelenleg **nem tekintheto teljeskoruen megfelelonek** a ket P0 tetel miatt.
