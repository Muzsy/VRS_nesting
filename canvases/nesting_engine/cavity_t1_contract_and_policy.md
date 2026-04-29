# Cavity T1 - Contract es policy dokumentacio

## Cel
Dokumentald a cavity-first composite nesting szerzodest: `cavity_plan_v1`,
`part_in_part=prepack`, worker-side prepack es engine-side legacy part-in-part
elvalasztasa. Ez dokumentacios es contract task; geometriai packer es runtime
bekotes nem keszul.

## Nem-celok
- Nem `worker/cavity_prepack.py` implementacio.
- Nem result normalizer expansion.
- Nem Rust engine modositas.
- Nem UI vagy export task.
- Nem `quality_default` atallitasa.

## Repo-kontekstus
- `docs/nesting_engine/io_contract_v2.md` rogziti a jelenlegi
  `nesting_engine_v2` input/output szerzodest.
- `vrs_nesting/config/nesting_quality_profiles.py` mar tartalmaz quality profile
  registryt, de `VALID_PART_IN_PART_MODES` jelenleg csak `off` es `auto`.
- A Rust CLI csak `--part-in-part off|auto` erteket ismer; `prepack` nem
  kuldheto a Rustnak.
- A root-cause report szerint a holed top-level input globalis NFP->BLF
  fallbacket okozhat.

## Erintett fajlok
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `canvases/nesting_engine/cavity_t1_contract_and_policy.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t1_contract_and_policy.yaml`
- `codex/prompts/nesting_engine/cavity_t1_contract_and_policy/run.md`

## Implementacios lepesek
1. Olvasd el a fejlesztesi tervet es a root-cause reportot.
2. Ellenorizd a valos IO contract, quality profile es runner CLI allapotot.
3. Hozd letre a `cavity_plan_v1` dokumentumot a minimalis schema,
   invariansok, instance accounting es virtual part ID szabalyok leirasaval.
4. Dokumentald, hogy `part_in_part=prepack` Python worker policy, nem Rust CLI
   ertek.
5. Dokumentald, hogy prepack modban a legacy BLF runtime part-in-part nem
   futhat egyszerre.

## Checklist
- [ ] `cavity_plan_v1` schema dokumentalt.
- [ ] `part_in_part=prepack` jelentese dokumentalt.
- [ ] Rust engine input tovabbra is `nesting_engine_v2`.
- [ ] Parent outer-only collision shape v1 korlat dokumentalt.
- [ ] Cut-order nem-cel es manufacturing follow-up dokumentalt.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- Dokumentacio review: linkek es pathok valosak.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t1_contract_and_policy.md`

## Elfogadasi kriteriumok
- Egy kovetkezo agent a doksikbol megerti, hogy nem full hole-aware NFP-t kell
  irni.
- A szerzodes egyertelmu a virtual parent, internal child, quantity delta es
  normalizer expansion temakban.
- A dokumentacio nem allitja, hogy a Rust engine hole-aware NFP kepes.

## Rollback
Csak dokumentacio valtozik; a docs diff visszavonhato futasi kockazat nelkul.

## Kockazatok
- Ha a schema tul koran tul reszletes, kesobb implementacio kozben modosulhat.
- Ha a policy es contract nincs kulonvalasztva, T2/T3 scope osszecsuszhat.

## Vegso reportban kotelezo bizonyitek
- Doksik path/line hivatkozasa a schemahoz es policy mappinghez.
- Explicit kijelentes, hogy nincs implementacios kod.
