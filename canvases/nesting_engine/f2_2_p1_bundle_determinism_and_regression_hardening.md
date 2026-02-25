# canvases/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md

> **TASK_SLUG:** `f2_2_p1_bundle_determinism_and_regression_hardening`  
> **AREA:** `nesting_engine`

## 🎯 Funkció

Az F2-2 full audit P1 kategóriájú 4 javítását egy taskban lezárjuk:

1) **Lib canonical JSON byte-level teszt**: a `determinism_hash` alapjául szolgáló *hash-view canonical JSON* legyen explicit, byte-azonos teszttel védve.  
2) **Spec drift megszüntetése**: `docs/nesting_engine/json_canonicalization.md` normatív leírása egyezzen a tényleges implementációval (Rust: `serde_json::to_string` + `BTreeMap`, Python: `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`), és mondja ki a “JCS-szubszet” keretet.  
3) **CLI 50× canonical determinism smoke bekötése a gate-be**: `scripts/check.sh` futtassa a `scripts/smoke_nesting_engine_determinism.sh`-t. Defaultban kisebb futásszám (idő), env-ből emelhető 50-re.  
4) **Quarantine acceptance workflow formalizálása**: `poc/nfp_regression/README.md` tartalmazza a `quarantine_generated_*.json` kezelését és az “accept” lépéseket.

Nem cél:
- F2-2 core algoritmus módosítása (concave/orbit)
- új dependency (Rust/Python) hozzáadása

## 🧠 Fejlesztési részletek

### Horgonyok (létező fájlok)
- P1 lista forrás: `codex/reports/nesting_engine/f2_2_full_audit.md` (P1: 4 pont)
- Canonical doc: `docs/nesting_engine/json_canonicalization.md`
- Python canonicalizer: `scripts/canonicalize_json.py`
- CLI smoke: `scripts/smoke_nesting_engine_determinism.sh`
- Gate: `scripts/check.sh`, `scripts/verify.sh`
- Rust determinism hash: `rust/nesting_engine/src/export/output_v2.rs`
- Quarantine fixtures: `scripts/fuzz_nfp_regressions.py`, `poc/nfp_regression/README.md`

### F2-2 audit P1 pontok (forrás: `f2_2_full_audit.md`)

1. Lib oldalon hiányzik az explicit canonical JSON bytes teszt (`rust/nesting_engine/src/export/output_v2.rs`).
2. A canonicalization doksi túl általános RFC/JCS leírást ad, implementáció-kötött normatív rész pontosítása kell (`docs/nesting_engine/json_canonicalization.md`).
3. A CLI determinism smoke nincs bekötve a kötelező gate-be (`scripts/check.sh` + `scripts/smoke_nesting_engine_determinism.sh`).
4. A quarantine fixture acceptance workflow nincs formalizálva repo szinten (`poc/nfp_regression/README.md`).

### Konkrét változtatások

**P1-1: Rust byte-level canonical JSON teszt**
- `rust/nesting_engine/src/export/output_v2.rs`:
  - refaktor: a hash-view canonical string előállítása kerüljön egy belső helperbe (hogy tesztelhető legyen),
  - új unit teszt: `assert_eq!(canonical_string, "<exact expected bytes>")`.

**P1-2: json_canonicalization.md pontosítás**
- A doc ne követeljen “teljes RFC8785 implementációt”, hanem mondja ki:
  - hash_view_v1 esetén a megengedett értékkészlet miatt elég a JCS-kompatibilis szubszet:
    - kulcsok lexikografikusan rendezve,
    - nincs whitespace,
    - UTF-8,
    - integer számok,
    - stringek JSON-escape szabály szerint.
  - Normatívan rögzítse a referencia serializációs szabályokat Rustra és Pythonra.

**P1-3: determinism smoke gate integráció**
- `scripts/check.sh` nesting_engine blokk végén:
  - hozzon létre `/tmp` fast inputot (time_limit_sec=1) a `poc/nesting_engine/sample_input_v2.json` alapján,
  - futtassa: `RUNS=${NESTING_ENGINE_DETERMINISM_RUNS:-10} INPUT_JSON=/tmp/... ./scripts/smoke_nesting_engine_determinism.sh`
  - dokumentálja env override-ot (pl. CI-ben 50).

**P1-4: quarantine acceptance workflow**
- `poc/nfp_regression/README.md` új szekció:
  - mi a quarantine (fuzz generál),
  - mikor maradhat quarantine,
  - hogyan “accept”: átnevezés + description tisztítás + stabil expected megerősítés + teszt PASS,
  - mit tegyünk, ha később törik (repro, döntés: javítunk vagy kidobjuk).

## 🧪 Tesztállapot

### DoD
- [x] `cargo test -p nesting_engine` PASS (különösen az új byte-level canonical teszt)
- [x] `./scripts/check.sh` PASS (benne a determinism smoke fut)
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- Audit: `codex/reports/nesting_engine/f2_2_full_audit.md` (P1: 4 pont)
- Canonical: `docs/nesting_engine/json_canonicalization.md`, `scripts/canonicalize_json.py`, `rust/nesting_engine/src/export/output_v2.rs`
- Gate: `scripts/check.sh`, `scripts/verify.sh`
- Quarantine: `scripts/fuzz_nfp_regressions.py`, `poc/nfp_regression/README.md`
