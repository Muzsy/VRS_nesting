# Cavity v2 T02 — quality_cavity_prepack UI/API elérhetővé tétele
TASK_SLUG: cavity_v2_t02_ui_api_quality_prepack

## Szerep
Senior frontend/TypeScript coding agent vagy. Minimális, célzott változtatásokat végzel: TypeScript union bővítés és egy option hozzáadása.

## Cél
A `quality_cavity_prepack` profil legyen kiválasztható a New Run UI-ban. A `QualityProfileName` union bővítése és a `cavity_prepack_summary` típus frissítése.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t02_ui_api_quality_prepack.yaml`
- `frontend/src/lib/types.ts` (TELJES fájl — QualityProfileName ~sor 372, cavity_prepack_summary ~sor 355)
- `frontend/src/pages/NewRunPage.tsx` (TELJES fájl — quality select ~sor 793-798)
- `vrs_nesting/config/nesting_quality_profiles.py` (registry ellenőrzés)

## Engedélyezett módosítás
Csak a YAML `outputs` listájában szereplő fájlok:
- `frontend/src/lib/types.ts`
- `frontend/src/pages/NewRunPage.tsx`

## Szigorú tiltások
- Tilos a backend API-t módosítani.
- Tilos a worker-logikát módosítani.
- Tilos a meglévő `quality_default` és `quality_aggressive` option-öket érinteni.
- Tilos új komponenst vagy fájlt létrehozni (csak a két meglévő fájl módosítandó).
- Tilos speculative kódot írni — csak a canvas-ban leírt minimális változtatás.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Olvasd el a types.ts-t és a NewRunPage.tsx-t. Azonosítsd pontosan:
- `QualityProfileName` union pontos sorait
- `cavity_prepack_summary` típus jelenlegi állapotát
- A quality select element pontos sorait a NewRunPage.tsx-ben

### Step 2: types.ts módosítása
```typescript
// QualityProfileName union bővítése:
export type QualityProfileName = "fast_preview" | "quality_default" | "quality_aggressive" | "quality_cavity_prepack";
```
`cavity_prepack_summary` típus bővítése a canvas spec alapján.

### Step 3: NewRunPage.tsx módosítása
Adj hozzá az option-t:
```tsx
<option value="quality_cavity_prepack">Quality cavity prepack</option>
```
A meglévő quality_aggressive option után.

### Step 4: TypeScript build
```bash
cd frontend && npx tsc --noEmit
```
Ha hiba van, javítsd a types.ts-ben. Build csak hibátlanul fogadható el.

### Step 5: Checklist és report
### Step 6: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md
```

## Tesztelési parancsok
```bash
cd frontend && npx tsc --noEmit
```

## Ellenőrzési pontok
- [ ] QualityProfileName union tartalmazza "quality_cavity_prepack"-et (sor referenciával)
- [ ] cavity_prepack_summary típus frissítve
- [ ] NewRunPage.tsx option hozzáadva
- [ ] TypeScript build hibátlan
- [ ] Meglévő quality_default, quality_aggressive érintetlen

## Elvárt végső jelentés formátuma
Magyar nyelvű report. Tartalmazza a módosított sorok referenciáit (fájl:sor formátum), TypeScript build kimenetet.

## Hiba esetén
Ha `npx tsc` nem elérhető, rögzítsd és folytasd — a types.ts módosítás önmagában is értékes.

## Csak valós kód alapján
Ne adj hozzá mezőket a cavity_prepack_summary típushoz, amelyek nem szerepelnek a canvas spec-ben vagy a meglévő types.ts-ben.
