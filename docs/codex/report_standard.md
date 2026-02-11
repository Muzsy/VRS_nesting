# Report Standard v2 (Codex)

**Cél:** egységes, auditálható report minden canvas+yaml futás után, amelyből gyorsan ellenőrizhető:

* mi készült el,
* hogyan lett verifikálva (parancsok + eredmények),
* a DoD pontok hol teljesülnek a kódban (bizonyítékokkal),
* és milyen nem-blokkoló észrevételek merültek fel.

Ez a dokumentum a **kötelező** report struktúrát írja le. A Codex csak akkor adhat **PASS** státuszt, ha a **DoD → Evidence Matrix** minden pontja ki van töltve, és a kötelező verifikációs parancsok lefutottak.

---

## 0) Kötelező kimeneti státusz

A report elején pontosan egyet válassz ezek közül:

* **PASS** – minden DoD teljesült, verifikáció zöld.
* **FAIL** – legalább egy DoD nem teljesült VAGY verifikáció piros.
* **PASS_WITH_NOTES** – DoD teljesült és verifikáció zöld, de vannak nem-blokkoló megjegyzések.

---

## 1) Meta

* **Task slug:** `<pl. sparrow_io_contract_update>`
* **Kapcsolódó canvas:** `<canvases/...>`
* **Kapcsolódó goal YAML:** `<codex/goals/...>`
* **Futás dátuma:** `<YYYY-MM-DD>`
* **Branch / commit:** `<branch + commit hash>`
* **Fókusz terület:** `Scripts | IO Contract | Geometry | Docs | CI | Mixed`

---

## 2) Scope

### 2.1 Cél

1–5 bulletben foglald össze, mit kellett elérni.

### 2.2 Nem-cél (explicit)

1–5 bullet: mi **nem** része ennek a feladatnak.

---

## 3) Változások összefoglalója (Change summary)

### 3.1 Érintett fájlok

**Kötelező:** sorold fel a módosított/létrehozott fájlokat csoportosítva.

Példa:

* **Scripts:**
  * `scripts/check.sh`
  * `scripts/validate_sparrow_io.py`
* **CI:**
  * `.github/workflows/sparrow-smoketest.yml`
* **Docs:**
  * `docs/dxf_nesting_app_...md`

### 3.2 Miért változtak?

1–2 mondat / csoport (Scripts/IO/Docs/CI), ne legyen regény.

---

## 4) Verifikáció (How tested)

### 4.1 Kötelező parancs

* `./scripts/verify.sh --report codex/reports/[<AREA>/]<TASK_SLUG>.md` → `PASS|FAIL`
  * ez futtatja: `./scripts/check.sh`
  * menti: `codex/reports/[<AREA>/]<TASK_SLUG>.verify.log`
  * frissíti a report AUTO_VERIFY blokkot

### 4.2 Opcionális, feladatfüggő parancsok

Csak ha releváns:

* `./scripts/check.sh` (ha külön futott)
* `python3 scripts/validate_sparrow_io.py --help` / extra validator futtatások

### 4.3 Ha valami kimaradt

Ha bármely kötelező/elfogadott ellenőrzés nem futott:

* miért maradt ki,
* milyen kockázat,
* mi az elvárt pótlólagos ellenőrzés.

### 4.4 Automatikus blokk

A report tartalmazza a `verify.sh` által frissített blokkot:

```md
<!-- AUTO_VERIFY_START -->
... (ezt a részt a script generálja) ...
<!-- AUTO_VERIFY_END -->
```

Ennek a résznek a kézi szerkesztése tilos; a script mindig felülírja.

---

## 5) DoD → Evidence Matrix (kötelező)

**Ez a report legfontosabb része.**

### Szabályok

* A canvas DoD pontjait **1:1-ben** sorold fel.
* Minden ponthoz adj **bizonyítékot**:
  * fájlútvonal + sorsáv (pl. `scripts/check.sh:L10-L120`),
  * rövid magyarázat (1–3 mondat),
  * és ha van: kapcsolódó ellenőrzés.
* Ha nincs bizonyíték vagy a DoD nem teljesült: **FAIL**.

### Minta táblázat

| DoD pont |   Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
| -------- | --------: | ------------------------ | ---------- | --------------------------- |
| #1 …     | PASS/FAIL | `scripts/...:Lx-Ly`      | …          | `./scripts/verify.sh ...`   |
| #2 …     | PASS/FAIL | `...`                    | …          | `...`                       |

---

## 6) IO contract / minták (ha releváns)

Ha a Sparrow IO contract, a POC input/output, vagy a validator változott:

* Melyik minta frissült? (`poc/...`)
* Mi az elvárt új invariáns (röviden)?
* Lefedi-e a `scripts/check.sh` futás?

---

## 7) Doksi szinkron (ha releváns)

* Mely doksik frissültek?
* Hol lett linkelve (docs index, README)?

---

## 8) Advisory notes (nem blokkoló)

**Cél:** ide kerül minden olyan észrevétel, ami nem teszt/kapu hiba és nem DoD-sértés, hanem döntés vagy finomhangolás.

Szabályok:

* **Max 5 bullet.**
* Legyen tömör és döntés-orientált.

---

## 9) Follow-ups (opcionális)

Ha vannak javasolt következő lépések:

* 1–5 bullet
* mindegyikhez: miért, és milyen kockázat/nyereség.
