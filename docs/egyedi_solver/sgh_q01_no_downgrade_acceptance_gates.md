# SGH-Q01 No-Downgrade Acceptance Gates

## Cél

Ez a dokumentum rögzíti azokat a kötelező kapukat, amelyeket minden jövőbeli SGH task-nak teljesítenie kell. Egyetlen task sem kaphat PASS státuszt, ha ezek a kapuk nem zöldek.

A „no-downgrade" szabály: **egyetlen feature parity státusza sem csökkenhet** (FULL→PARTIAL, PARTIAL→PROXY, PROXY→MISSING tiltott). Emelkedés megengedett.

---

## G01 — Test suite gate (minden task kötelező)

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Elvárás: 0 failed
```

**Elfogadási küszöb:** 100% pass. A jelenlegi baseline: 140/140.

**Miért blokkoló:** Minden production kód változtatás visszavonhatatlanul ronthat meglévő operátorokon. A teljes suite zöld tartása biztosítja a scaffolding integritását (SGH-01..SGH-05).

---

## G02 — Verify gate (minden task kötelező)

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/<task_slug>.md
# Elvárás: exit 0, [DONE] smoketest OK
```

**Elfogadási küszöb:** exit 0.

**Miért blokkoló:** A verify.sh tartalmaz Sparrow IO smoketest-et, pytest suite-ot, és mypy type check-et. Bármelyik ág eltörése a teljes pipeline integritását veszélyezteti.

---

## G03 — No-violation gate (minden accepted output kötelező)

```rust
find_violations(&placements, &parts, &sheets).is_empty()
```

**Elfogadási küszöb:** 0 violation. Egyetlen accepted output sem hagyhatja el a commit gate-et violations-szal.

**Miért blokkoló:** Az SGH-01 `WorkingLayout` → commit gate architektúra garanciája. Ha ezt bármely task megsérti, az egész SGH-01..SGH-05 scaffolding biztonságát aláássa.

---

## G04 — Proxy annotáció gate (PROXY kódhelyek kötelező annotáció)

Minden kódban lévő PROXY implementáció tartalmaz `// QUALITY_RISK:` annotációt a következő formátumban:

```rust
// QUALITY_RISK: <ProxyName>
// Exact for: <when exact>
// Proxy for: <when not exact>
// Parity: <STATUS> (<F-number>, SGH-Q00)
```

**Elfogadási küszöb:** Minden új PROXY kódsor annotált. Meglévő, SGH-Q01 előtt bekerült PROXY-ok az SGH-Q01 scope-jában annotálódnak.

**Miért blokkoló:** P06 elv (SGH-Q00 modular architecture principles). Jelöletlen proxy = jövőbeli fejlesztő félreérti a korlátokat.

---

## G05 — Determinism gate (minden stochasztikus komponens kötelező)

```
Azonos seed → bit-identikus output
10 futás → 10/10 egyezés
```

**Elfogadási küszöb:** 100% egyezés. Teszt: `deterministic_smoke` pattern a meglévő tesztek alapján.

**Miért blokkoló:** A VRS `./scripts/verify.sh` determinizmus smoke-testje (`[OK] determinism smoke passed (10/10 full outputs are byte-identical)`) ezt ellenőrzi. Multi-worker és stochasztikus keresés bevezetésekor seedelhetőség kötelező.

---

## G06 — Parity non-regression gate (SGH-Q02+ kötelező)

Az SGH-Q00 gap matrix minden F-feature parity státusza legalább a korábbi szinten marad.

| Korábbi státusz | Megengedett változás |
|---|---|
| FULL | → FULL |
| PARTIAL | → PARTIAL, FULL |
| PROXY | → PROXY, PARTIAL, FULL |
| MISSING | → MISSING, PROXY, PARTIAL, FULL |

**Elfogadási küszöb:** A task report tartalmaz explicit parity státusz táblát, amelyből leolvasható, hogy egyetlen feature sem romlott.

**Miért blokkoló:** Az SGH-Q00 audit elvégzésének célja pontosan az volt, hogy a baseline rögzülve legyen. Ha egy task „optimalizálási" céllal visszaminősít valamit, az a jövőbeli quality kapukhoz vezető utat vágja le.

---

## G07 — No hardcoded proxy without quality gate (SGH-Q02+)

Egyetlen új PROXY bevezetése sem engedélyezett explicit `quality_risk` szinttel és benchmark gate-tel.

**Kötelező formátum minden új PROXY task esetén:**

```yaml
proxy_name: <ProxyName>
quality_risk: HIGH | MEDIUM | LOW
benchmark_gate: <leírás>
replacement_task: SGH-Q<n>
```

**Elfogadási küszöb:** Minden task YAML tartalmazza a fentieket, ha új PROXY kerül be.

**Miért blokkoló:** Az SGH-Q00 audit megmutatta, hogy jelöletlen PROXY-k felhalmozódnak — a VRS rectangular Phase 1 6 PROXY-ja mind annotáció nélkül volt. SGH-Q01 után ez nem ismétlődhet.

---

## G08 — Production scope gate (minden task kötelező)

Minden task csak az `allowed production files` listájában szereplő fájlokat módosítja.

**Elfogadási küszöb:** `git diff --name-only` nem mutat allowed-on kívüli production fájlt.

**Miért blokkoló:** AGENTS.md `Codex outputs szabály` — csak YAML step outputs listájában szereplő fájl módosítható.

---

## Összefoglalás: gate checklist per task

| Gate | Leírás | Kötelező? |
|---|---|---|
| G01 | `cargo test` 100% | MINDEN task |
| G02 | `verify.sh` exit 0 | MINDEN task |
| G03 | `find_violations` == [] minden accepted output-on | MINDEN task |
| G04 | Proxy annotáció P06 szerint | MINDEN PROXY kódhelynél |
| G05 | Determinism: seed → bit-identical output | Stochasztikus komponenseknél |
| G06 | Parity non-regression vs. SGH-Q00 gap matrix | SGH-Q02+ |
| G07 | Hardcoded proxy csak explicit quality gate-tel | SGH-Q02+ |
| G08 | Production scope: csak allowed files módosítva | MINDEN task |
