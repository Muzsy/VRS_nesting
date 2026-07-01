# SGH-Q77 Report - Nagy-darab 3/tábla interlock (NFP-probing + beam)

## 0) Statusz

**PENDING** - ez a terv-váz. A verdict a Phase 0 (feasibility lock-in) + implementáció + A/B + verify
után állítható. **ACCEPT** csak akkor PASS, ha a skeleton+NFP-beam **3 nagy/táblát** ér el Full276-on,
valid (final_pairs=0), a darabszámot > 274-re emeli (cél 276) és 2. csomagon nincs regresszió;
egyébként **őszinte EXIT** a Phase 0 célponttal + gap-elemzéssel (nem proxy-PASS).

## 1) Meta

- **Task slug:** `sgh_q77_big_interlock_nfp_beam`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q77_big_interlock_nfp_beam.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q77_big_interlock_nfp_beam.yaml`
- **Futas datuma:** `<YYYY-MM-DD>` (meg nem futott)
- **Branch / commit:** `main@<commit>`
- **Fokusz terulet:** `Solver core (skeleton big-part interlock: NFP-probing candidates + beam search)`

## 2) Scope

### 2.1 Cel
- A nagy ismétlődő típust **3/táblára mélyen interlockolni** (referencia 6/2-tábla), a 274/65% ceiling
  áttörésére (util ~78%+), generikusan.
- **NFP-jelölt CDE-probing** (decimált kontúr, cache) + **beam-lánc keresés** (3-test egyidejű).

### 2.2 Nem-cel
- Teljes 276² NFP; NFP-poligon; spacing/margin csökkentés; hardcode; geometriai lehetetlenség-kijelentés;
  default production változás (gate OFF = byte-azonos).

## 3) Valtozasok osszefoglaloja (tervezett)

- **nfp_probe.rs (ÚJ):** `nfp_touch_candidates` (CDE-probing, deepest-clear, decimált) + relatív-szög cache.
- **bpp_reduction.rs:** `interlock_beam` (K-beam, mélység 3, largest_contiguous_useful + lookahead) + bekötés
  a seedbe (gate) + pin + graceful fallback.
- **io.rs:** Q77 diagnosztikák.
- **tests + scripts:** NFP + beam unit/integrációs teszt; Phase 0 feasibility harness + A/B runner.

## 4) Verifikacio (terv)

- Phase 0: offline 3-body kereső → konkrét 3-pose (`artifacts/benchmarks/sgh_q77/phase0_feasibility.json`).
- `cargo test --release --lib` + `--test sparrow_sheet_builder` (NFP + beam + integrációs, gate-OFF byte-azonos).
- `python3 scripts/bench_sgh_q77_big_interlock_nfp_beam.py` (Full276 + 2. csomag, default vs skeleton+NFP-beam).
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q77_big_interlock_nfp_beam.md`.

### 4.4 Automatikus blokk
<!-- AUTO_VERIFY_START -->
(A `verify.sh` futaskor generalja.)
<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| 0. Phase 0 feasibility (3-pose) | PENDING | - | offline CDE/polygon-tiszta 3-nagy pose 1500x3000-on | phase0_feasibility.json |
| 1. NFP-probing motor (decimált, cache) | PENDING | - | deepest-clear érintő-pozíciók NFP-poligon nélkül | NFP unit teszt |
| 2. Beam 3-lánc | PENDING | - | K-beam + lookahead, ahol a páros greedy csak 2-t | beam unit teszt |
| 3. Integráció + pin + refine | PENDING | - | seed-bekötés, q74_locked, exploration túléli | F integrációs teszt |
| 4. A/B: 3/tábla + darabszám-emelés | PENDING | - | placed >274 (cél 276), util ~78%+, final_pairs=0 | Q77 benchmark |
| 5. Generikussag (2. csomag) | PENDING | - | nincs regresszió | Q77 benchmark |
| 6. Gate OFF byte-azonos + tesztek | PENDING | - | default production változatlan | verify.sh |
| 7. verify.sh PASS | PENDING | - | repo gate | verify.sh |

## 6) Finding

A Q76/A/B′ mérések után a kép egyértelmű: a **2-test mély interlock elérhető** (B′ 2D-scan: 503k mm²
átfedés, 11mm hézag), de a **3/tábla 3-test EGYIDEJŰ** kényszer-kielégítést igényel (szélesség ≤1495 ÉS
magasság ≤2990 ÉS páronként CDE-tiszta) — a geometriai kulcs: **≥50% x-átfedés** kell a 3-lánchoz, amit
a kompakt páros greedy (~38%) nem ér el. A referencia/deepnest ezt **NFP + globális kereséssel** oldja;
a mi CDE-first architektúránkban ez **NFP-jelölt CDE-probinggal (decimált, cache) + korlátozott beammel**
skálázható — **sub-second** a seed-időben (a 276-darabos szeparáció drága része változatlan). Az F1
(Q76) él-horgony + useful-objektív + a B′ 2-test interlock a helyes alap; a Q77 a 3-test lépés.
