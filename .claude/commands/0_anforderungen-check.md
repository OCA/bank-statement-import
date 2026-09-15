# Prüfe das Anforderungsdokument

Erstelle einen strukturierten Bericht über Vollständigkeit, Korrektheit und Umsetzbarkeit eines Anforderungsdokuments.

## Input

* **Feature-Name**: $ARGUMENTS (z.B. `CAMT054-Import`) → liest `Specs/[Feature-Name].md`  
  Falls nicht angegeben: aus dem Konversations-Kontext ableiten (z.B. wenn zuvor `/0_anforderungen` ausgeführt wurde); nur wenn unklar: nachfragen.

---

## Vorgehen

### Phase 1: Dokument lesen
1. Lies `Specs/[Feature-Name].md`
2. Lies `Specs/SPEC.md` (Template-Struktur) zum Abgleich
3. Lies `Specs/generell.md` (allgemeine Anforderungen)

### Phase 2: Kontext recherchieren
4. Lies verwandte Specs aus `/Specs/` (über Abhängigkeiten in Abschnitt 6)
5. Prüfe den **bestehenden Code** auf Widersprüche und Machbarkeit:
   - Betroffene Models (`models/*.py`): Existieren die genannten Felder? Sind sie `required`?
   - Bestehende Parser (`parserlib.py`, `models/parser.py`): Liefern sie die genannten Daten?
   - Bestehende Views (`views/*.xml`): Verändert die Spec eine bestehende View?
   - Manifest (`__openerp__.py`): Sind die vorausgesetzten Module in `depends`?

### Phase 3: Systematische Prüfung

**Struktur:**
- Sind alle 8 Abschnitte des Templates vorhanden?
- Sind keine Abschnitte leer oder nur mit Platzhaltern befüllt?
- Ist das betroffene Odoo-Modul benannt (bestehend oder neu)?

**Akzeptanzkriterien:**
- Haben alle Kriterien eine Checkbox (`[ ]`)?
- Sind sie konkret und testbar (nicht "soll funktionieren", sondern prüfbares Verhalten)?
- Decken sie alle FR-Anforderungen ab?
- Decken sie NFR-2 (Sicherheit/Zugriffsrechte) ab?
- Sind Edge Cases aus Abschnitt 5 als testbare AK abgebildet?

**Sicherheit (NFR-2):**
- Sind die nötigen Zugriffsrechte explizit genannt (`account.group_account_user` /
  `account.group_account_manager` oder eine andere konkrete Gruppe)?
- Bei einem neuen eigenen Model: Ist `security/ir.model.access.csv` gefordert?
- Ist eine Einschränkung von Menü/Button über `groups=` spezifiziert, falls nötig?

**Firmenbezug (Multi-Company):**
- Werden neue firmenbezogene Daten gespeichert? Dann: `company_id` + Record Rule gefordert?
- Wird der Firmenbezug serverseitig gesetzt (Default), nicht vom Client bestimmt?

**Datenmodell & Persistierung:**
- Sind alle Felder mit Typ (`fields.Char` / `Many2one` / …), Pflicht/Optional und Default spezifiziert?
- Sind Relationen vollständig (`ondelete`-Verhalten bei `Many2one`)?
- Sind Eindeutigkeits-Constraints definiert (`_sql_constraints`), falls Duplikate zu verhindern sind?
- Wird angegeben, ob die Manifest-Version erhöht werden muss?
- Ist eine Datenmigration (`migrations/<version>/post-migrate.py`) nötig und vermerkt?

**i18n:**
- Werden neue UI-Texte englisch im Code und über `_()` gefordert?
- Ist vermerkt, dass daraus Änderungen an `i18n/*.po` entstehen?
- Sind deutsche Texte in der Spec mit Umlauten geschrieben (`ä`/`ö`/`ü` statt `ae`/`oe`/`ue`)?

**Kompatibilität:**
- Ist die Anforderung mit Odoo 8.0 / Python 2.7 umsetzbar (keine Python-3-Syntax,
  keine API aus späteren Odoo-Versionen)?
- Bleibt die Änderung mergefähig zum OCA-Upstream?
- Sind neue externe Python-Bibliotheken unter `external_dependencies` vermerkt?

**Edge Cases:**
- Mindestens abgedeckt: leere/fehlerhafte Datei, unbekanntes Format, doppelter Import
- Verhalten bei referenziellen Abhängigkeiten (Löschen, Kaskadierung)?

**Widersprüche mit bestehendem Code:**
- Stimmen Feldnamen und -typen mit den Models überein?
- Stimmen die erwarteten Parser-Ausgaben mit `parserlib.py` überein?
- Sind neue Constraints mit bestehenden Daten kompatibel?

**Offene Fragen:**
- Sind noch unbeantwortete Fragen vorhanden, die die Umsetzung blockieren?

---

## Output

Gib den Bericht **im Chat** aus (keine Datei erstellen, Spec nicht verändern).

```markdown
# Anforderungs-Review: [Feature-Name]

## Ergebnis: [Anzahl Befunde] Befunde ([K] kritisch, [M] minor)

### Kritische Inkonsistenzen
> Blockieren die Umsetzung oder führen zu falschem Verhalten

| # | Problem | Abschnitt | Empfehlung |
|---|---------|-----------|------------|
| 1 | Beschreibung... | FR-2 | Empfehlung... |

### Kleinere Lücken
> Sollten vor der Umsetzung geklärt werden

| # | Problem | Abschnitt | Empfehlung |
|---|---------|-----------|------------|
| 1 | Beschreibung... | AK | Empfehlung... |

### Offene Fragen (falls vorhanden)
* Frage 1
* Frage 2

## Fazit
[Bereit zur Umsetzung / Korrekturbedarf / Klärungsbedarf]
```

Falls keine Befunde: "Keine Befunde — Spec ist vollständig und umsetzungsbereit."

---

## Hinweise

* **Konservativ bewerten:** Im Zweifel als Befund aufführen
* **Nachweis liefern:** Für Code-Widersprüche die konkrete Datei und Zeile angeben
* **Keine Korrekturen vornehmen:** Nur berichten, nicht ändern — Korrekturen macht der User selbst
* Diese Analyse ist **READ-ONLY** — keine Spec-Datei wird verändert

---

## Referenz
* `Specs/SPEC.md` - Template-Struktur
* `Specs/generell.md` - Allgemeine Projektanforderungen (Odoo-Konventionen, i18n, Zugriffsrechte)
* `CLAUDE.md` - Modul-Übersicht und Code-Vorlagen
