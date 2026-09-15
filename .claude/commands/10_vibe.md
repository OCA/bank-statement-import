# Vibe → Anforderungsdokument + Umsetzung

Ergänze mit frei formulierten Anforderungen ein bestehendes Anforderungsdokument und setze die neuen Anforderungen direkt um.

## Input

$ARGUMENTS

* **Feature-Name** (erster Parameter): z.B. `CAMT054-Import`
* **Anforderungen** (Rest): Neue oder angepasste Anforderungen, Änderungen oder Rahmenbedingungen zu einem bereits bestehenden Anforderungsdokument.

## Vorgehen
1. **Lies die Referenzdokumente** – `Specs/[Feature-Name].md` und `Specs/generell.md`.
2. **Verstehe die neuen Anforderungen** aus dem Input.
3. **Stelle Rückfragen** bei wesentlichen Unklarheiten, die die Umsetzung beeinflussen – BEVOR du weitermachst.
4. **Ergänze das Anforderungsdokument** mit den zusätzlichen Anforderungen.
    - Ergänze die Funktionalen Anforderungen, die Akzeptanzkriterien und die Nichtfunktionalen Anforderungen wo nötig.
5. **Setze die neuen Anforderungen um** gemäss den Vorgaben in `Specs/generell.md` und den
   Code-Patterns in `.claude/commands/2_umsetzung.md`.

## ⚠️ Odoo-Besonderheiten – zwingend beachten

* **Kein Schema-Skript schreiben.** Neue Felder entstehen deklarativ im Model; Odoo legt die
  Spalten beim Modul-Update an. Es gibt **kein** Flyway und keine DDL-Migrationen.
* **Datenmigration** (Umschreiben bestehender Werte) nur über
  `<modul>/migrations/<manifest-version>/post-migrate.py` mit `def migrate(cr, version)`.
  Das Skript wird über genau die Manifest-Version gefunden – diese also **vorher** erhöhen.
* **Manifest pflegen:** Jede neue XML-Datei unter `data` bzw. `demo` eintragen, `depends`
  ergänzen, `version` erhöhen (`8.0.<major>.<minor>.<patch>`).
* **Python 2.7 / Odoo 8:** `from openerp import ...`, neue API (`@api.model`, `@api.multi`,
  `fields.*`), `super(Klasse, self)`, keine f-Strings. XML-Wurzel ist `<openerp><data>`.
* **Zugriffsrechte:** Neues eigenes Model braucht `<modul>/security/ir.model.access.csv` –
  erweiterte Standard-Models erben die Rechte aus `account`.
* **Übersetzungen:** Neue UI-Texte englisch im Code mit `_()`. Die `i18n/*.po` **nicht** von
  Hand um einzelne Keys ergänzen, ausser es ist ausdrücklich beauftragt.
  Deutsche Texte immer mit Umlauten (`ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`) – nie `ae`/`oe`/`ue`
  (z.B. «Löschen», nicht «Loeschen»); Eszett in Schweizer Schreibweise als `ss`.
  Dateien UTF-8-kodiert speichern.
* **Keine Testläufe:** In diesem Repository läuft kein Odoo und keine Testsuite. Nach der
  Umsetzung nur statisch prüfen (XML-Wohlgeformtheit, Manifest-Konsistenz, Syntax) und
  **nie** behaupten, etwas sei getestet.

## Output
* Ergänze die bestehende Anforderungsdatei: `Specs/[Feature-Name].md`
* Ergänze den bestehenden Umsetzungsplan (falls vorhanden): `Specs/[Feature-Name]_Umsetzungsplan.md`
* Weiche nicht von der Struktur des Templates `Specs/SPEC.md` ab
* Implementiere die neuen Anforderungen im Modul-Code
* Passe die bestehenden Tests falls nötig an

## Referenz
* `Specs/[Feature-Name].md` - das bestehende und zu ergänzende Anforderungsdokument
* `Specs/[Feature-Name]_Umsetzungsplan.md` - der zu ergänzende Umsetzungsplan (falls vorhanden)
* `Specs/SPEC.md` – Template-Struktur
* `Specs/generell.md` – Allgemeine Projektanforderungen (Odoo-Konventionen, i18n, Zugriffsrechte)
* `CLAUDE.md` – Modul-Übersicht und Code-Vorlagen
