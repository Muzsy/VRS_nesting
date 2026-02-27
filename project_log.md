# Projekt napló - Flutter átültetés prototípus

**Dátum:** 2026-02-27  
**Koordinátor:** Jack (OpenClaw)  
**Cél:** Az `app_card.dart` komponens átültetése a tippmixapp-ből a tipsterino projektbe, a feature‑first szabályok szerint.

---

## 1. Feladatbontás

- **Analyst:** Kikeresi és elemzi az `app_card.dart` fájlt a tippmixapp‑ből.
- **Architect:** Megtervezi az új helyét és struktúráját a tipsterino projektben.
- **Developer:** Elkészíti az új fájlt a tervek alapján.

---

## 2. Folyamat naplója

### 2.1. Analyst ügynök indítása
- **Idő:** 23:16
- **Feladat:** "Elemezd a `/home/muszy/projects/tippmixapp/lib/widgets/components/app_card.dart` fájlt. Írd le a függőségeit, működését, és milyen tulajdonságai vannak. A kimenetet írd a project_log.md fájlba a '## Analyst jelentés' szakasz alá."

### 2.2. Architect ügynök indítása
- **Idő:** 23:17  
- **Feladat:** "A tipsterino projekt feature‑first struktúráját követve (ld. `docs/architect/project_structure.md`) tervezd meg, hová kerüljön az `AppCard` komponens. Melyik feature alá tartozna? Milyen elnevezést és mappaszerkezetet javasolsz? Írd a naplóba a '## Architect terv' részbe."

### 2.3. Developer ügynök indítása
- **Idő:** 23:18  
- **Feladat:** "Az analyst és architect kimenete alapján írd át az `AppCard` komponenst a tipsterino szabályai szerint. Használd a tipsterino design tokenjeit (`AppTheme`), helyezd el a megfelelő feature mappában, és ellenőrizd, hogy nincs-e deep import más feature‑be. A generált fájlt a tipsterino projektben hozd létre, és írd a naplóba a '## Developer eredmény' részbe."

---

## 3. Eredmények

### Analyst jelentés (23:17)
- **Fájl:** `/home/muszy/projects/tippmixapp/lib/widgets/components/app_card.dart`
- **Függőségek:** `import 'package:flutter/material.dart';`
- **Komponens típus:** Stateless
- **Tulajdonságok:** 
  - `key` (optional)
  - `leading` (Widget?, optional)
  - `title` (Widget?, optional)
  - `subtitle` (Widget?, optional)
  - `trailing` (Widget?, optional)
  - `padding` (EdgeInsetsGeometry, default: EdgeInsets.all(16))
  - `onTap` (VoidCallback?, optional)
  - `child` (Widget?, optional)
- **Működés:** Általános, újrahasználható kártya widget Material Design alapokon. A widget egy `Material` konténert használ, amely `InkWell`-t tartalmaz kattintáskezeléssel. Ha nincs megadva `child`, akkor egy alapértelmezett tartalmat épít fel (`_buildDefaultContent`), amely a `leading`, `title`, `subtitle` és `trailing` widgeteket elrendezve jeleníti meg. A kártya a témából (`Theme.of(context)`) származtatja a színeket, a keretet és az árnyékot, így konzisztens a designrendszerrel.
- **Megjegyzések:** 
  - A kártya alakja lekerekített sarkú (`borderRadius: 16`) és vékony kerettel (`outlineVariant`).
  - A `child` paraméter felülírja az alapértelmezett tartalmat, teljesen egyedi widgetek megjelenítésére lehet használni.
  - Az `InkWell` a teljes kártyán érzékeli a kattintást, ha meg van adva `onTap`.
  - A `padding` paraméterrel a kártya belső margója szabályozható.

### Architect terv (23:21)
- **Javasolt hely:** `lib/src/shared/widgets/app_card.dart`
- **Indoklás:** A komponens egy általános kártya widget, amely kizárólag a Flutter Material library-tól függ, és nem tartalmaz feature‑specifikus logikát. A tipsterino projektben a kártya widget várhatóan több feature által is felhasználható lesz (pl. `bets`, `events`, `rewards`). A dokumentáció szerint, ha egy UI elem legalább 2 feature által használatos, a `shared/` mappába kerülhet. Mivel a komponens általános és a design tokeneket fogja használni, a `shared/widgets` a legmegfelelőbb hely – így elkerüljük a központi gyűjtőmappák (pl. `lib/src/widgets/`) létrehozását is.
- **Átnevezés szükséges?:** Nem, a widget neve `AppCard` maradhat. A fájlnév `app_card.dart` (snake_case) lesz, ami megfelel a projekt konvenciójának.
- **Design tokenek:** Az AppCard a tipsterino `AppTheme` osztályából származó design tokeneket használja:
  - Háttérszín: `Theme.of(context).colorScheme.surface` vagy `Theme.of(context).cardColor`
  - Árnyék, eleváció: `Theme.of(context).shadowColor`, `Theme.of(context).elevation`
  - Kerekítés, alak: `Theme.of(context).cardTheme.shape` (pl. `RoundedRectangleBorder`)
  - Padding/margin: `Theme.of(context).cardTheme.margin`/`padding`
  - A tippmixapp‑beli egyedi paraméterek (pl. elevation, color) opcionális paraméterekként maradnak, de a theme alapértékeit veszik fel.
- **Függőségek kezelése:** 
  - Import: `import 'package:flutter/material.dart';`
  - A `shared/theme/app_theme.dart` közvetlen importálása jelenleg nem szükséges, mivel a `Theme.of(context)` eléri a theme adatokat. Ha a jövőben a tipsterino saját design tokeneket ad hozzá (pl. `AppTheme.cardBorderRadius`), akkor az import szükséges lesz.
  - A `shared/widgets` mappa létrehozása után érdemes létrehozni egy barrel fájlt (`shared/widgets/widgets.dart`), amely exportálja az összes shared widgetet (köztük az `app_card.dart`‑t) a könnyű importálás érdekében.

### Developer eredmény (23:26)
- **Célfájl:** `/home/muszy/projects/tipsterino/app/lib/src/shared/widgets/app_card.dart`
- **Generált kód:**
```dart
import 'package:flutter/material.dart';

class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    this.leading,
    this.title,
    this.subtitle,
    this.trailing,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
    this.child,
  });

  final Widget? leading;
  final Widget? title;
  final Widget? subtitle;
  final Widget? trailing;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final cardTheme = theme.cardTheme;

    // Determine shape: use cardTheme.shape if provided, otherwise default with side
    final shape = cardTheme.shape ??
        RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: colorScheme.outlineVariant, width: 1),
        );

    // Determine borderRadius for InkWell (extract from shape if possible)
    final borderRadius = shape is RoundedRectangleBorder
        ? shape.borderRadius
        : const BorderRadius.all(Radius.circular(16));

    return Material(
      color: cardTheme.color ?? colorScheme.surface,
      surfaceTintColor: cardTheme.surfaceTintColor ?? colorScheme.primary,
      elevation: cardTheme.elevation ?? 1,
      shape: shape,
      shadowColor: cardTheme.shadowColor ?? theme.shadowColor,
      child: InkWell(
        borderRadius: borderRadius,
        onTap: onTap,
        child: Padding(
          padding: padding,
          child: child ?? _buildDefaultContent(context),
        ),
      ),
    );
  }

  Widget _buildDefaultContent(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (leading != null) ...[leading!, const SizedBox(width: 12)],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (title != null)
                DefaultTextStyle.merge(
                  style: Theme.of(context).textTheme.titleMedium,
                  child: title!,
                ),
              if (subtitle != null) ...[
                const SizedBox(height: 4),
                DefaultTextStyle.merge(
                  style: Theme.of(context).textTheme.bodyMedium,
                  child: subtitle!,
                ),
              ],
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: 12),
          Align(alignment: Alignment.topRight, child: trailing!),
        ],
      ],
    );
  }
}
```
- **Megjegyzések:** Átírtam a kódot a Theme.of(context) design tokenjeinek használatára. A stílus (háttérszín, árnyék, kerekítés) a cardTheme-ből származik, ha azok null‑ok, akkor alapértelmezett értékeket használ (colorScheme.surface, primary, elevation 1). A shape alapértelmezettként tartalmaz oldalszélt (outlineVariant). Az InkWell borderRadius‑t a shape‑ből nyerjük ki. A padding alapértelmezett értéke marad EdgeInsets.all(16), mivel a CardTheme nem tartalmaz padding property‑t. Nincs deep import, csak flutter/material.dart.

---

## 4. Prototípus értékelése
**Idő:** 23:27  
**Összegzés:** A 3‑ügynök prototípus sikeresen lefutott. Az `AppCard` komponens átültetése a tippmixapp‑ból a tipsterino projektbe kész, a feature‑first szabályoknak megfelelően.

**Következő lépések:**
1. **Ellenőrzés:** `flutter analyze` futtatása a tipsterino projektben.
2. **Skálázás:** Teljes legacy projekt átültetésének tervezése több ügynökkel.
3. **Koordináció:** Python szkript összerakása a teljes folyamathoz.