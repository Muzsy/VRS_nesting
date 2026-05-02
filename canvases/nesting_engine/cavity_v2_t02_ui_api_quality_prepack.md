# Cavity v2 T02 — quality_cavity_prepack UI/API elérhetővé tétele

## Cél

A `quality_cavity_prepack` profil jelenleg be van jegyezve a backend registrybe (`vrs_nesting/config/nesting_quality_profiles.py`), de a frontend TypeScript típusokból és a NewRunPage UI-ból hiányzik. Ez a task bekötést végez: a profil kiválasztható legyen a New Run varázslóban.

---

## Miért szükséges

A v2 fejlesztési lánc minden következő taskja igényli, hogy a `quality_cavity_prepack` profilt valódi run-ban lehessen indítani. A UI bekötés nélkül a prepack mód csak direkt API-n tesztelható, ami megnehezíti a végfelhasználói validációt.

---

## Érintett valós fájlok

### Módosítandó:
- `frontend/src/lib/types.ts` — `QualityProfileName` type union, `cavity_prepack_summary` type
- `frontend/src/pages/NewRunPage.tsx` — minőségi profil `<select>` elem

### Olvasandó (kontextus):
- `vrs_nesting/config/nesting_quality_profiles.py` — a backend registry (nem módosítandó)
- `docs/nesting_quality/cavity_prepack_quality_policy.md`

---

## Nem célok / scope határok

- Nem kell az API backend endpoint-ot módosítani — a profil neve már átmegy a rendszeren.
- Nem kell a worker-logikát módosítani.
- Nem kell e2e tesztet írni (csak smoke).
- Nem kell a profil leírásához külön backend enpoint.
- A cavity_prepack_summary típust csak kibővítjük, nem módosítjuk meglévő mezőit.

---

## Részletes implementációs lépések

### 1. `frontend/src/lib/types.ts` módosítása

**Jelenlegi állapot (sor ~372):**
```typescript
export type QualityProfileName = "fast_preview" | "quality_default" | "quality_aggressive";
```

**Várt állapot:**
```typescript
export type QualityProfileName = "fast_preview" | "quality_default" | "quality_aggressive" | "quality_cavity_prepack";
```

**cavity_prepack_summary típus (sor ~355):**
Ellenőrizd, hogy a meglévő `cavity_prepack_summary?` mező struktúrája illeszkedik-e az alábbihoz. Ha nem, bővítsd:
```typescript
cavity_prepack_summary?: {
  enabled: boolean;
  version?: string;
  virtual_parent_count?: number;
  internal_placement_count?: number;
  nested_internal_placement_count?: number;
  used_cavity_count?: number;
  usable_cavity_count?: number;
  top_level_holes_removed_count?: number;
  holed_child_proxy_count?: number;
  quantity_delta?: Record<string, { original_required_qty: number; internal_qty: number; top_level_qty: number }>;
};
```

### 2. `frontend/src/pages/NewRunPage.tsx` módosítása

**Jelenlegi állapot (sor ~795-796):**
```tsx
<option value="quality_default">Quality default</option>
<option value="quality_aggressive">Quality aggressive</option>
```

**Várt állapot:**
```tsx
<option value="quality_default">Quality default</option>
<option value="quality_aggressive">Quality aggressive</option>
<option value="quality_cavity_prepack">Quality cavity prepack</option>
```

Ha van tooltip, description, vagy help szöveg a profil mellé, adjuk hozzá:
> _"Cavity prepack: worker-side lyukfelismerés. A lyukas alkatrészek cavityjeibe kisebb részek kerülnek előre. A fő solver csak lyuk nélküli formákat lát."_

### 3. Ellenőrzés

```bash
cd frontend && npx tsc --noEmit
```

Ha TypeScript error → fixeld a types.ts-ben.

---

## Adatmodell / contract változások

- `QualityProfileName` union kibővül — backward compatible (új lit érték adódik)
- `cavity_prepack_summary` mező csak optional bővítés — backward compatible

---

## Backward compatibility szempontok

- A meglévő `quality_default` és `quality_aggressive` profilek változatlanok.
- A `QualityProfileName` union bővítése nem töri a meglévő kódot.
- A `cavity_prepack_summary` optional mező — ha nincs jelen, a meglévő UI nem omlik össze.

---

## Hibakódok / diagnosztikák

Ha a TypeScript build hibát dob:
- `Type '"quality_cavity_prepack"' is not assignable to type 'QualityProfileName'` → a union frissítés nem lett alkalmazva
- `Object literal may only specify known properties` → a cavity_prepack_summary mező típusa nem stimmel

---

## Tesztelési terv

1. TypeScript build: `cd frontend && npx tsc --noEmit`
2. Frontend smoke: az option megjelenik a select-ben
3. Kiválasztás után a run request body tartalmazza `"quality_profile": "quality_cavity_prepack"` értéket

---

## Elfogadási feltételek

- `QualityProfileName` tartalmazza `"quality_cavity_prepack"` literált
- A NewRunPage select-ben megjelenik az opció
- TypeScript build hibamentes
- `cavity_prepack_summary` típus a fenti mezőket tartalmazza (legalább: `enabled`, `version`, `virtual_parent_count`, `internal_placement_count`)

---

## Rollback / safety notes

Minimális kockázat — csak TypeScript típusbővítés és egy UI option hozzáadása. Rollback: a két sor törlése.

---

## Dependency

- T01 auditot nem szükséges megvárni; T02 párhuzamosan futtatható.
