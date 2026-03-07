# canvases/nesting_engine/part_in_part_pipeline.md

## 🎯 Funkció

F3-2 cél: **determinista, opt-in part-in-part pipeline** bevezetése a jelenlegi `nesting_engine` állapothoz igazítva.

A jelenlegi repó-helyzet:
- `--placer nfp` lyukas vagy `hole_collapsed` partoknál továbbra is **BLF fallback**-ra vált (`main.rs` hybrid gating).
- A teljes **hole-aware NFP/CFR** továbbra is külön, nagyobb feladat lenne; ez **nem** része ennek a tasknak.
- A `HOLE_COLLAPSED` policy már rögzített: ilyen partból nesting szempontból **nem** lehet cavity/part-in-part forrás, mert a placer felé `holes=[]` megy.

Ennek megfelelően az F3-2 ebben a repóban ne teljes NFP-újraírás legyen, hanem:
- a meglévő **BLF placer** kapjon **cavity-aware jelöltgenerálást**,
- a feature legyen **kapcsolható**,
- a validálás maradjon a meglévő, bevált `can_place()` narrow-phase-on,
- a default működés ne törjön.

## 🧠 Fejlesztési részletek

### 1) Aktiválás: új, minimál-invazív CLI flag

A `nest` subcommand kapjon új opciót:
- `--part-in-part off|auto`
- default: `off`

Miért `off` a default?
- repo-szabály szerint minimal-invazív változás kell,
- az F3-2 első célja a stabil, bizonyítható pipeline,
- ha zöld és stabil, későbbi külön taskban lehet dönteni a default `auto`-ra emelésről.

### 2) Scope-határ (fontos)

Ez a task **nem** csinálja meg:
- hole-aware NFP/CFR-t,
- rekurzív / többszintű part-in-part nestinget,
- IO contract bővítését,
- exporter módosítást,
- remnant scoringot.

Ez a task **csak** ezt teszi:
- BLF candidate generation bővítése,
- cavity jelöltek gyártása a már elhelyezett partok **használható hole**-jaiból,
- validálás meglévő `can_place()`-szel,
- fallback a meglévő globális BLF rács-scanre.

### 3) Cavity-forrás szabály

Cavity jelölt **csak** olyan már elhelyezett partból származhat, amelynek a placerben tárolt `inflated_polygon.holes` listája **nem üres**.

Következmény:
- `status == hole_collapsed` part automatikusan kiesik, mert a már lezárt policy szerint `holes=[]` kerül a placerbe.
- Nem kell külön új státuszmező vagy contract-bővítés.

### 4) Candidate generation stratégia (determinista)

A jelenlegi globális BLF scan rács-alapú. Ez néhány cavity-esetben véletlenül találhat lyukbeli helyet, de nem megbízható és a nem egész mm-es / szűk toleranciás hole-geometriákat könnyen elvéti.

Ezért az `auto` mód cavity-jelöltjei legyenek **hole-anchor alapúak**, nem teljes bin-scan ismétlések.

#### 4.1 Jelöltforrások sorrendje

Minden part instance elhelyezésénél, minden rotációra:
1. már elhelyezett partok a placement sorrendben,
2. azon belül a hole-ok determinisztikus sorrendben:
   - hole bbox `min_x`,
   - majd `min_y`,
   - majd bbox area,
   - majd hole index,
3. azon belül determinisztikus anchor lista.

#### 4.2 Anchor lista

Az anchorok a hole geometriából származzanak, hogy a globális 1 mm-es scan által kihagyott, de érvényes pozíciók is elérhetők legyenek.

Ajánlott minimál készlet:
- hole bbox bal-alsó sarok + kis belső nudge,
- hole bbox közép környéke,
- hole ring vertex-alapú anchorok + kis determinisztikus nudge készlet.

Követelmény:
- minden anchor `i64` mm-scale koordinátán legyen előállítva,
- a generálás teljesen determinisztikus legyen,
- ne kelljen új random vagy floating tie-break.

#### 4.3 Validálás

Minden cavity-anchor candidate ugyanazzal a meglévő úttal validálódjon:
- `can_place(candidate, bin_polygon, placed_state)`

Vagyis:
- containment marad,
- overlap/touch tiltás marad,
- touching továbbra is infeasible.

#### 4.4 Fallback

Ha cavity-anchor candidate nem talál érvényes helyet:
- a jelenlegi globális BLF scan fusson le változatlanul.

Ez garantálja, hogy az `auto` mód csak bővít, nem vesz el a meglévő működésből.

### 5) Miért kell külön fixture?

A DoD egyik kritikus pontja, hogy legyen **legalább 1 fixture**, ahol a part-in-part **demonstrálhatóan javít**.

Ehhez a fixture legyen szándékosan olyan, hogy:
- a külső szabad terület ne legyen elég a kis partnak,
- a használható cavity igen,
- a cavity-feasible pozíció **ne essen rá** a globális 1 mm-es BLF scan tipikus rácspontjaira,
  így az `off` és az `auto` mód közt valódi, reprodukálható különbség jöjjön ki.

#### Javasolt fixture
`poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json`

Elv:
- Sheet kicsit nagyobb, mint a frame outer bbox.
- Frame outer majdnem kitölti a sheetet.
- A frame hole elég nagy egy kis partnak, de a hole koordinátái **off-grid** jellegűek.
- `--part-in-part off` esetén baseline: `sheets_used = 2`
- `--part-in-part auto` esetén: `sheets_used = 1`

### 6) Tesztek / gate

#### 6.1 Rust unit tesztek (`blf_part_in_part_` prefix)
A `rust/nesting_engine/src/placement/blf.rs` tesztmoduljába kerüljenek új tesztek.

Minimum:
- `blf_part_in_part_off_mode_preserves_baseline`
  - `PartInPartMode::Off` mellett a meglévő BLF viselkedés marad.
- `blf_part_in_part_offgrid_hole_improves_sheet_count`
  - az off-grid cavity fixture geometriájával `Off` rosszabb, `Auto` jobb eredményt ad.
- `blf_part_in_part_hole_collapsed_like_outer_only_source_is_ignored`
  - ha a placed polygon `holes=[]`, nem lesz cavity candidate, nincs crash, nincs tiltott beágyazás.

#### 6.2 CLI smoke
Új smoke script:
- `scripts/smoke_part_in_part_pipeline.py`

A script futtassa ugyanarra a fixture-re:
- baseline: `nest --placer blf --part-in-part off`
- cavity mód: `nest --placer blf --part-in-part auto`

A script assertjei:
- baseline `sheets_used == 2`
- auto `sheets_used == 1`
- mindkét outputban van `meta.determinism_hash`
- a cavity mód ismételt futásban hash-stabil ugyanazzal a seed-del

#### 6.3 check.sh integráció
A gate-be kerüljön be:
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml blf_part_in_part_`
- `python3 scripts/smoke_part_in_part_pipeline.py --bin ... --input ...`

### 7) Dokumentáció

Frissítendő:
- `docs/nesting_engine/architecture.md`
- `docs/nesting_engine/tolerance_policy.md`

Rögzíteni kell benne:
- az F3-2 jelenlegi scope-ja BLF cavity-candidate pipeline,
- `--placer nfp` holes esetben továbbra is BLF fallback lehet,
- `HOLE_COLLAPSED` soha nem cavity-forrás,
- `--part-in-part off|auto` jelentése,
- hogy a validálás ugyanaz a `can_place()` narrow-phase.

## 🧪 Tesztállapot

### DoD
- [ ] Új CLI kapcsoló van: `--part-in-part off|auto`, default `off`.
- [ ] `PartInPartMode::Off` mellett a jelenlegi baseline működés változatlan marad.
- [ ] `PartInPartMode::Auto` módban a BLF cavity-aware jelölteket generál már elhelyezett partok használható hole-jaiból.
- [ ] `hole_collapsed` / outer-only forrásból nem lesz cavity candidate (graceful degradation, nincs crash).
- [ ] Van legalább 1 repo fixture (`poc/nesting_engine/f3_2_part_in_part_offgrid_fixture_v2.json`), ahol `auto` demonstrálhatóan jobb (`sheets_used` csökken).
- [ ] Rust unit tesztek (`blf_part_in_part_` prefix) PASS.
- [ ] Új CLI smoke PASS és bekerül a `scripts/check.sh` gate-be.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/part_in_part_pipeline.md` PASS.
- [ ] Checklist + report elkészül Report Standard v2 szerint.

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md`
- `canvases/nesting_engine/nesting_engine_backlog.md` (F3-2)
- `docs/nesting_engine/f2_3_nfp_placer_spec.md`
- `docs/nesting_engine/tolerance_policy.md`
- `docs/nesting_engine/architecture.md`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `scripts/check.sh`
