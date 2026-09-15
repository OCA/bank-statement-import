# Erstelle Umsetzungsplan

Erstelle einen detaillierten Umsetzungsplan für eine Spezifikation.

## Input

* **Feature-Name**: $ARGUMENTS (z.B. `CAMT054-Import`) → liest `Specs/[Feature-Name].md`  
  Falls nicht angegeben: aus dem Konversations-Kontext ableiten (z.B. wenn zuvor `/0_anforderungen` ausgeführt wurde); nur wenn unklar: nachfragen.

## Vorgehen
1. **Analysiere die Spezifikation** in `Specs/[Feature-Name].md` - Lies und verstehe alle Anforderungen
2. **Recherchiere den Code** - Finde das betroffene Addon und die bestehenden Patterns (Models, Parser, Views)
3. **Prüfe Abhängigkeiten** - Betroffene Module, `depends` im Manifest, `external_dependencies`
4. **Prüfe offene Fragen** - Lies Abschnitt "8. Offene Fragen" der Spec:
   - Fragen mit Antwort (` --> ...`): als Annahme in den Plan übernehmen
   - Fragen ohne Antwort, die den Scope oder die Architektur beeinflussen: **Rückfrage stellen BEVOR du den Plan erstellst**
   - Fragen ohne Antwort, die Details betreffen: als Annahme treffen und unter "Offene Punkte / Annahmen" dokumentieren

## Output
* Erstelle einen neuen Umsetzungsplan in: `Specs/[Feature-Name]_Umsetzungsplan.md`
* **Spec-Tabellen 1:1 übernehmen:** Die strukturierten Tabellen aus Abschnitt 2 der Spec sind die verbindliche Quelle. Übernimm sie unverändert in den Plan, statt sie neu zu formulieren:
    - **Datenmodell & Persistierung** → Felder, Typen, Constraints und `company_id`-Entscheidung in die Model-Phase
    - **Oberfläche (Views)** → betroffene Views und Erweiterungspunkte in die View-Phase
    - **Validierungen** → 1:1 in das Kapitel «Validierungen»
* Der Umsetzungsplan enthält folgende Kapitel:
    - **Zusammenfassung:** 2-3 Sätze: Was wird implementiert und warum
    - **Betroffene Komponenten:** Liste aller zu ändernden/erstellenden Dateien
    - **Phasen-Tabelle:** Mit Spalten für Status, Phase, Beschreibung
    - **Validierungen:** Validierungsregeln (Model-Constraints, Parser-Prüfungen)
    - **Offene Punkte / Annahmen:** inkl. der in Abschnitt 8 der Spec beantworteten Fragen (` --> `)

### Phasen-Tabelle Format

Nur die Phasen aufnehmen, die tatsächlich anfallen. `<modul>` durch das betroffene Addon ersetzen.

```markdown
| Status | Phase                   | Beschreibung                                                                 |
|--------|-------------------------|------------------------------------------------------------------------------|
|  [ ]   | 1. Model                | Felder / Logik in `<modul>/models/<datei>.py`                                 |
|  [ ]   | 2. Parser               | Parse-Logik in `<modul>/models/parser.py` bzw. `parserlib.py` (falls Format betroffen) |
|  [ ]   | 3. Views                | XML in `<modul>/views/<datei>.xml` (neu oder via `inherit_id` erweitert)      |
|  [ ]   | 4. Zugriffsrechte       | `<modul>/security/ir.model.access.csv` (nur bei neuem eigenem Model)          |
|  [ ]   | 5. Manifest             | `<modul>/__openerp__.py`: `depends`, `data`, `version` erhöhen                |
|  [ ]   | 6. Datenmigration       | `<modul>/migrations/<version>/post-migrate.py` (nur bei Datentransformation)  |
|  [ ]   | 7. Demo-/Testdaten      | `<modul>/demo/demo_data.xml`, Beispieldatei in `<modul>/test_files/`          |
|  [ ]   | 8. Übersetzungen        | Neue `_()`-Strings; `<modul>/i18n/*.po` nur bei ausdrücklichem Auftrag anfassen |
|  [ ]   | 9. Doku                 | `<modul>/README.rst` aktualisieren                                            |
```

#### Hinweise
* Phasen so granular gestalten, dass sie einzeln umsetzbar sind
* Bei der Umsetzung wird der Status in der Phasen-Tabelle nachgeführt
* Beachte bestehende Architektur-Patterns im Projekt (siehe Code-Vorlagen in `CLAUDE.md`)
* **Kein Schema-Skript:** Neue Spalten entstehen deklarativ aus den Feld-Definitionen. Ein
  Migrationsskript wird **nur** für Datentransformationen bestehender Datensätze angelegt.
* **Manifest-Version:** Bei funktionalen Änderungen `8.0.<major>.<minor>.<patch>` erhöhen –
  ein Migrationsskript wird über genau diese Version gefunden.
* **Firmenbezug:** Neue firmenbezogene Models brauchen `company_id` + Record Rule – keine
  selbstgebaute Mandantenlogik.
* **Python 2.7 / Odoo 8:** Keine Python-3-Syntax, `from openerp import ...`, neue API
  (`@api.model`, `@api.multi`, `fields.*`).
* **Deutsche Texte:** immer mit Umlauten schreiben (`ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`) – nie die
  Ersatzschreibweise `ae`/`oe`/`ue` (z.B. «Löschen», nicht «Loeschen»); Eszett in Schweizer
  Schreibweise als `ss`. Dateien UTF-8-kodiert speichern.
* **Keine Spec-Daten erfinden:** Felder, Formate und Zugriffsrechte stammen aus der Spec.
  Fehlt etwas, unter «Offene Punkte / Annahmen» dokumentieren — nicht raten.
* **Code-Vorlagen:** Verwende die Vorlagen aus `CLAUDE.md` (Abschnitt "Code-Vorlagen für deterministische Generierung")

## Konventionen

### Dateinamen
| Typ | Muster |
|-----|--------|
| Model | `<modul>/models/<snake_case>.py` (Dateiname folgt dem Model-Namen, z.B. `account_bank_statement.py`) |
| Parser | `<modul>/models/parser.py` |
| View | `<modul>/views/<snake_case>.xml` bzw. `<snake_case>_view.xml` |
| Zugriffsrechte | `<modul>/security/ir.model.access.csv` |
| Manifest | `<modul>/__openerp__.py` |
| Migration | `<modul>/migrations/<manifest-version>/post-migrate.py` |
| Demo-Daten | `<modul>/demo/demo_data.xml` |
| Test | `<modul>/tests/test_<beschreibung>.py` (plus Import in `tests/__init__.py`) |
| Testdatei (Fixture) | `<modul>/test_files/<name>` |
| Übersetzung | `<modul>/i18n/<sprache>.po` |

---

## Referenz
* `CLAUDE.md` - Projekt-Architektur, Modul-Aufbau und Code-Vorlagen
* `Specs/generell.md` - Allgemeine Anforderungen
* `Specs/SPEC.md` - Template-Struktur der Spec
