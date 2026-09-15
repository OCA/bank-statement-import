# Umsetzung

Setze einen Umsetzungsplan schrittweise um.

## Input

* **Feature-Name**: $ARGUMENTS (z.B. `CAMT054-Import`) → liest `Specs/[Feature-Name]_Umsetzungsplan.md`  
  Falls nicht angegeben: aus dem Konversations-Kontext ableiten (z.B. wenn zuvor `/0_anforderungen` oder `/1_umsetzungsplan` ausgeführt wurde); nur wenn unklar: nachfragen.

## Vorgehen
1. **Lies den Umsetzungsplan** `Specs/[Feature-Name]_Umsetzungsplan.md` – verstehe alle Phasen und deren Status
2. **Identifiziere nächste Phase** - Finde die erste Phase mit `[ ]` (nicht erledigt)
3. **Implementiere die Phase** - Setze die beschriebenen Änderungen um (Patterns unten beachten!)
4. **Prüfe statisch** - Siehe Abschnitt Validierung
5. **Aktualisiere den Status** - Markiere die Phase mit `[x]` als erledigt
6. **Wiederhole** - Fahre mit der nächsten Phase fort

## Konventionen

* **Python 2.7 / Odoo 8.0:**
    * Erste Zeile jeder `.py`-Datei: `# -*- coding: utf-8 -*-`
    * `from openerp import api, fields, models` – **nicht** `from odoo import ...`
    * Neue API: `@api.model`, `@api.multi`, `fields.Char(...)` – **kein** `@api.one`,
      **keine** alte `_columns`-Notation
    * `super(KlassenName, self).methode(...)` – **nicht** das argumentlose `super()` aus Python 3
    * Keine f-Strings, kein `yield from`, keine Type-Hints
    * `_logger = logging.getLogger(__name__)` auf Modulebene
    * Lizenzheader der jeweiligen Datei-Umgebung beibehalten (AGPL-3)
* **Views (XML):**
    * Wurzelelement ist `<openerp><data>` – **nicht** `<odoo>` (das gibt es erst ab Odoo 9)
    * Bestehende Views immer über `inherit_id` + Positionsangabe erweitern, nie kopieren
    * Jede neue XML-Datei unter `data` (bzw. `demo`) im Manifest eintragen
* **Manifest (`__openerp__.py`):**
    * Bei funktionalen Änderungen `version` erhöhen (`8.0.<major>.<minor>.<patch>`)
    * `depends` vollständig halten; externe Python-Pakete unter `external_dependencies`
* **Datenbank:**
    * Neue Felder entstehen **deklarativ** im Model – **kein** DDL-Skript schreiben
    * Migrationsskript nur für **Datentransformationen**:
      `<modul>/migrations/<manifest-version>/post-migrate.py` mit `def migrate(cr, version)`
    * Rohes SQL nur wenn nötig, und dann **immer** mit Parameter-Binding
* **Zugriffsrechte:**
    * Neues eigenes Model → `<modul>/security/ir.model.access.csv` anlegen und im Manifest
      unter `data` eintragen
    * Erweiterte Standard-Models erben die Rechte aus `account` – nichts hinzufügen
* **Übersetzungen (i18n):**
    * Neue UI-Texte **englisch** im Code und mit `_('...')` übersetzbar machen
    * `i18n/*.po` **nicht** von Hand um einzelne Keys ergänzen, ausser der Auftrag verlangt es
    * **Deutsche Texte immer mit Umlauten:** `ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü` – nie `ae`/`oe`/`ue`
      (z.B. «Löschen», «Zurück», «Änderung», nicht «Loeschen», «Zurueck», «Aenderung»);
      Eszett in Schweizer Schreibweise als `ss`. Dateien UTF-8-kodiert speichern.
* **Upstream-Nähe:** Dieses Repo ist ein OCA-Fork. Änderungen möglichst klein und im
  Upstream-Stil halten, damit künftige Merges funktionieren.
* **Code-Vorlagen:** Verwende die Vorlagen aus `CLAUDE.md` (Abschnitt "Code-Vorlagen für deterministische Generierung")

## Validierung nach jeder Phase

Es gibt in diesem Repository **keine lokal ausführbare Test- oder Build-Pipeline** – kein
Maven, kein npm, kein lauffähiges Odoo im Repo. Geprüft wird **statisch**:

* **XML-Wohlgeformtheit** (jede geänderte View-/Daten-Datei):
  ```bash
  python -c "import xml.etree.ElementTree as ET; ET.parse('<pfad>.xml'); print('XML ok')"
  ```
* **Manifest-Konsistenz:** Jede unter `data` und `demo` gelistete Datei existiert tatsächlich;
  jedes Modul unter `depends` ist auflösbar.
* **Python-Syntax (grobe Prüfung):**
  ```bash
  python -c "import ast; ast.parse(open('<pfad>.py','rb').read()); print('Syntax ok')"
  ```
  **Achtung:** Auf diesem Rechner läuft Python 3.9, der Code ist Python 2.7. Der Check fängt
  grobe Tippfehler, schlägt aber bei legitimer Python-2-only-Syntax fälschlich an (bekannter
  Fall im Repo: `account_bank_statement_import_ofx/account_bank_statement_import_ofx.py`).
  Einen solchen Treffer bewerten, nicht blind als Fehler melden.
* **Imports gegen `tests/__init__.py` und `models/__init__.py`:** Neue Dateien dort eintragen.
* **Code-Review gegen die Vorlagen** in `CLAUDE.md`.

Ein tatsächlicher Odoo-Testlauf (`--test-enable`) findet ausserhalb dieses Repos statt und ist
**nicht** Teil dieses Commands. Nie behaupten, Tests seien gelaufen.

## Wichtige Regeln
* **Keine Tests erstellen** - Tests werden separat mit `/3_backend-tests` erstellt
* **Inkrementell arbeiten** - Eine Phase nach der anderen abschliessen
* **Status aktuell halten** - Umsetzungsplan nach jeder Phase aktualisieren
* **Statisch validieren** - Nach jeder Phase (siehe oben)
* **Deterministische Patterns** - Code MUSS exakt den unten definierten Patterns folgen

---

## Code-Patterns

Die Struktur jeder Datei wird aus den **Vorlagen-Dateien in CLAUDE.md** übernommen (Abschnitt
"Code-Vorlagen für deterministische Generierung"). Lies die entsprechende Vorlage und passe sie
an den neuen Use Case an.

| Neuer Code | Vorlage lesen |
|------------|---------------|
| Model-Erweiterung (`_inherit`) | `account_bank_statement_import/models/account_bank_statement.py` |
| Neues Model / Wizard (`TransientModel`) | `account_bank_statement_import/models/account_bank_statement_import.py` |
| Parser (`AbstractModel`) | `account_bank_statement_import_camt/models/parser.py` |
| Manifest | `account_bank_statement_import_camt/__openerp__.py` |
| View (Formular) | `account_bank_statement_import/views/account_bank_statement_import_view.xml` |
| View-Erweiterung (`inherit_id`) | `account_bank_statement_import/views/account_journal.xml` |
| Demo-Daten | `account_bank_statement_import_camt/demo/demo_data.xml` |
| Datenmigration | `account_bank_statement_import/migrations/8.0.1.0/post-migrate.py` |
| Modul-Doku | `account_bank_statement_import_camt/README.rst` |

### Verbindliche Regeln Models

**Aufbau einer Model-Datei (Reihenfolge):**
1. `# -*- coding: utf-8 -*-`
2. Lizenz-/Copyright-Header
3. Standard-Library-Imports
4. `from openerp import ...`
5. `_logger = logging.getLogger(__name__)`
6. Klassen

**Innerhalb einer Klasse (Reihenfolge):**
1. Docstring
2. `_name` / `_inherit` / `_description`
3. Feld-Definitionen
4. `_sql_constraints`
5. Compute-/Default-Methoden (`_get_*`, `_compute_*`)
6. Constraints (`@api.constrains`)
7. CRUD-Überschreibungen (`create`, `write`, `unlink`)
8. Öffentliche Geschäftslogik
9. Private Hilfsmethoden (`_`-Präfix)

**Regeln:**
* Feld-Definitionen immer mit `string=` und – wo nicht selbsterklärend – `help=`
* Eindeutigkeit über `_sql_constraints` absichern (Muster: `unique_import_id`)
* Erwartete Fehler: `raise UserError(_('Meldung'))`
  (Import: `from openerp.exceptions import Warning as UserError`)
* Übersetzbare Strings mit `_()` aus `openerp.tools.translate`
* CRUD-Überschreibungen rufen immer `super(...)` auf und geben dessen Ergebnis zurück
* Neue Datei → in `models/__init__.py` eintragen

### Verbindliche Regeln Parser

* Parser sind `models.AbstractModel` mit eigenem `_name`
  (Muster: `account.bank.statement.import.camt.parser`)
* Erkennt der Parser das Format nicht, bricht er sauber ab, damit das Framework den
  nächsten Parser probieren kann – keine unspezifische Exception nach aussen
* Fehlende Elemente/Attribute defensiv behandeln (Default statt `KeyError`)
* Rückgabe im Format der `parserlib.py`-Strukturen (`BankStatement`, Transaktionen)

### Verbindliche Regeln Views

* Wurzel: `<?xml version="1.0" encoding="utf-8"?>` + `<openerp><data>`
* Jeder Record mit sprechender `id`; Erweiterungen mit `inherit_id` + `ref="<modul>.<view_id>"`
* Positionierung über `position="after|before|replace|inside"` bzw. XPath
* Sichtbarkeit rollenabhängig über `groups="..."`
* Neue Datei → im Manifest unter `data` eintragen

---

## Referenz
* `CLAUDE.md` - Vorlagen-Dateien, Modul-Aufbau und Projekt-Architektur
* `Specs/generell.md` - Odoo-Konventionen, i18n, Zugriffsrechte
