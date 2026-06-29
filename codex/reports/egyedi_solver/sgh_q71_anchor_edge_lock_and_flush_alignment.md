# SGH-Q71 Anchor edge-lock and flush alignment

## Meta

- Task slug: `sgh_q71_anchor_edge_lock_and_flush_alignment`
- Canvas: `canvases/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q71_anchor_edge_lock_and_flush_alignment.yaml`
- Fokusz: `forced-latest anchor edge-lock + flush alignment`

## Statusz

PARTIAL, nem elfogadhato kesz allapot.

## Kiindulasi problema

- A Q70 ugyan jobb diagnosztikat adott, de a render alapjan a nagy Anchor elemek nem maradtak
  eleg eros authorityval a tabla szeleihez zarva.
- A lenyegi problema az, hogy a jo seedelt edge/corner jelolt a separation vagy a fallback utan
  el tud sodrodni a tabla kozepe fele, ettol pedig a hasznos maradekter minosege is romlik.

## Tervezett bizonyitekok

- path+line evidence az edge-lock / drift-aware anchor scoringrol
- regresszios teszt forced-latest Anchor fallback visszaeses ellen
- uj Q71 Full276 benchmark renderrel es edge-gap summaryval

## Aktualis eredmeny

- A solver oldalon mar valos, forgatott spacing-kontur alapjan megy az anchor edge-gap meres
  es a flush-repair kiserlet.
- A large-anchor catalog/feature authority mar nem tud hangtalanul visszaesni a korabbi
  center-default logikara.
- A Full276 futasban a vizualisan fontos nagy darabok edge-lockja javult, de ez jelenleg
  tul nagy kihasznaltsagi aron tortenik.
- A jelenlegi legfrissebb Q71 artifact:
  - `placed_count = 215`
  - `utilization_pct = 53.8161`
  - `largest-part edge_locked_count = 7`
  - `largest-part avg_min_edge_gap_mm = 65.609`
- Ez a vizualis minoseget javitja a Q70-hez kepest, de a teljes nesting minoseg meg mindig nem eleg jo.

## Fo megallapitas

A feladat szakmai lenyege most mar tiszta: a problema nem pusztan az elso anchor-seed valasztasa,
hanem az, hogy a kesobbi admission/separation korok alatt hogyan maradnak stabilan a tabla-szelhez
kotve a nagy darabok anelkul, hogy a fennmarado hely kitolthetosége osszeomlana. A mostani iteracio
mar jobb edge authorityt ad, de meg nem talalta meg azt az egyensulyt, ahol a vizualis edge-lock es
a darabszam egyszerre eros.

## DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| Anchor edge-lock authority megerositve | PARTIAL | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:234`, `:238`, `:491`, `:523`, `:587`, `:635`, `:3113` | A forced-latest anchor scoring, a true-contour edge-gap meres es a center-path szigoritas bekerult, de az eredmeny meg nem eleg jo a teljes benchmarkon. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_sheet_builder forced_latest -- --nocapture` |
| Forced-latest Anchor fallback regresszio vedett | DONE | `rust/vrs_solver/tests/sparrow_sheet_builder.rs:121` | A regresszios teszt ellenorzi, hogy a forced-latest anchor policy mar ne legyen csendes center-default. | ugyanaz a teszt |
| Q71 benchmark artifactcsomag letrehozva | DONE | `scripts/bench_sgh_q71_anchor_edge_lock_and_flush_alignment.py`, `artifacts/benchmarks/sgh_q71/` | A runner ujrafutott, a Q71 summary/report/output/render artifactok frissultek. | `python3 scripts/bench_sgh_q71_anchor_edge_lock_and_flush_alignment.py` |
| Vizualis audit es edge-gap eredmeny rogzitve | DONE | `artifacts/benchmarks/sgh_q71/q71_summary.json`, `artifacts/benchmarks/sgh_q71/q71_report.md` | A summary mar mutat javult edge-lockot, de a render meg mindig kompromisszumos. | manual render audit (`sheet_00.png`, `sheet_01.png`) |
| `./scripts/verify.sh --report ...` lefutott | PENDING | - | Tudatosan nincs meg lefuttatva PASS lezarassal, mert a task szakmai minosege nincs keszen. | `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md` |
