# Generelle Anforderungen

## 1. Ziel & Kontext
* **Was soll erreicht werden:** Hier sind generelle Anforderungen aufgeführt, die bei jeder Umsetzung einer Anforderung
    berücksichtigt werden sollen.
* **Warum machen wir das:**
  * Deterministische Umsetzung wird so erreicht.
  * Die Module bleiben einheitlich und nah am OCA-Upstream, damit Merges möglich bleiben.

## 2. Funktionale Anforderungen (Functional Requirements)
* Die funktionalen Anforderungen werden in User Stories aufgeführt.

## 3. Technische Spezifikationen (Technical Specs)

### Plattform
* **Odoo 8.0** mit **Python 2.7**, Namespace `openerp`, Manifest `__openerp__.py`
* Kein Build-Schritt – Module werden direkt aus dem Quellverzeichnis geladen und via
  Modul-Update in der Odoo-Instanz aktiv

### Backend (Odoo-Models)
* Neue API verwenden: `@api.model`, `@api.multi`, `fields.Char(...)` – **nicht** die alte
  `_columns`-Notation, **kein** `@api.one`
* Import immer `from openerp import api, fields, models`
* Übersetzbare Strings über `from openerp.tools.translate import _` → `_('Text')`
* Fehler an den Benutzer: `from openerp.exceptions import Warning as UserError`
* Logging: `_logger = logging.getLogger(__name__)` auf Modulebene
* Erste Zeile jeder `.py`-Datei: `# -*- coding: utf-8 -*-`
* Keine Python-3-Syntax (keine f-Strings, `StringIO` aus dem Modul `StringIO`)

### Frontend (Odoo Web Client)
* Es gibt **kein eigenes Frontend-Projekt**. Die Oberfläche entsteht ausschliesslich aus
  XML-Views (`ir.ui.view`), Actions und Menüs im jeweiligen Modul unter `views/`
* Erweiterungen bestehender Views immer über `inherit_id` + XPath, nie durch Kopieren
* Datums- und Zahlenformate kommen aus der Odoo-Sprach-/Länder-Konfiguration
  (`res.lang`) – **nicht** im Code hart formatieren

### Design System
* n/a – es gibt kein eigenes Design System. Das Styling liefert der Odoo-Web-Client.
  Eigene CSS-/JS-Assets nur, wenn unvermeidbar, dann unter `static/src/` und über ein
  `assets`-Template eingebunden.

### Datenbank / Migrationen
* Schema-Änderungen entstehen **deklarativ** aus den Feld-Definitionen im Model. Odoo legt
  Spalten beim Modul-Update an – es gibt **kein** Flyway und keine DDL-Skripte.
* Nur für **Datentransformationen** ein Skript unter
  `<modul>/migrations/<manifest-version>/post-migrate.py` mit `def migrate(cr, version)` anlegen
  (Vorlage: `account_bank_statement_import/migrations/8.0.1.0/post-migrate.py`)
* Die Manifest-Version (`8.0.<major>.<minor>.<patch>`) bei funktionalen Änderungen erhöhen;
  ein Migrationsskript wird über genau diese Version gefunden
* Rohes SQL (`self.env.cr.execute`) nur, wenn das ORM den Fall nicht abdeckt – und dann
  **immer** mit Parameter-Binding, nie mit String-Konkatenation

### Multi-Tenancy
* n/a im Sinne eigener Mandantenspalten. Odoo trennt Daten über **Multi-Company**
  (`company_id` + Record Rules) und über die Datenbank selbst.
* Neue eigene Models, die firmenbezogene Daten halten, bekommen ein
  `company_id = fields.Many2one('res.company', ...)` und eine passende Record Rule –
  keine selbstgebaute `org_id`-Logik

### Mehrsprachigkeit (i18n)
* UI-Strings werden **englisch** im Quellcode geschrieben und mit `_()` übersetzbar gemacht
* Übersetzungen liegen als Gettext-Dateien in `<modul>/i18n/*.po` (+ `*.pot`) und werden
  regulär über Odoo-Export bzw. Transifex gepflegt – **nicht** von Hand um einzelne Keys
  ergänzen, ausser der Auftrag verlangt es ausdrücklich
* **Deutsche Texte immer mit Umlauten** (`ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`) – **nie** die
  Ersatzschreibung `ae`/`oe`/`ue`. Die Texte erscheinen unverändert auf dem Bildschirm.
  * **Kein Eszett:** Schweizer Schreibweise, also `ss` – «Strasse», «ausschliesslich», «gemäss».
    Das ist keine Ersatzschreibung, sondern richtig und bleibt so.
  * Gilt für die `msgstr`-Einträge in `de.po`. Die Dateien sind UTF-8; Umlaute sind darin
    unproblematisch.
  * **Nicht** betroffen: Bezeichner (Model- und Feldnamen, XML-IDs, Selection-Keys) – die bleiben ASCII.

### Fehleranzeige
* Benutzerfehler über `raise UserError(_('...'))` – Odoo zeigt sie als Dialog an
* Technische Fehler ins Log (`_logger.error(...)`), nicht roh an den Benutzer durchreichen
* Bei Importfehlern: aussagekräftige Meldung inkl. betroffenem Dateinamen / Datensatz

### Git-Konventionen
* Commit-Messages: Kurz und prägnant, beschreiben was geändert wurde;
  projektspezifisch oft mit Ticket-Präfix (`OERPGLUE-<Nr>`)
* Keine Secrets oder Credentials committen
* Upstream ist OCA – möglichst nah am Upstream-Stil bleiben, damit Merges funktionieren

### Code-Vorlagen
Bei der Code-Generierung die Vorlagen-Tabelle in `CLAUDE.md` (Abschnitt "Code-Vorlagen für
deterministische Generierung") beachten und deren Struktur exakt übernehmen.

## 4. Nicht-funktionale Anforderungen

### Authentifizierung & Autorisierung
* Authentifizierung macht Odoo selbst (`res.users`) – kein externes Auth-System in diesem Repo
* Dieses Repository definiert **keine** eigenen Sicherheitsgruppen und keine
  `ir.model.access.csv`. Die Rechte ergeben sich aus den erweiterten Modellen des
  Standardmoduls `account`:
    * `account.group_account_user` – Buchhaltung, Standardbenutzer
    * `account.group_account_manager` – Buchhaltung, Verantwortlicher
* Wird ein **neues eigenes Model** eingeführt, braucht es zwingend:
    * `security/ir.model.access.csv` mit Zeilen je Gruppe (read/write/create/unlink)
    * den Eintrag der Datei unter `data` im Manifest
    * bei firmenbezogenen Daten zusätzlich eine Record Rule auf `company_id`
* Menüeinträge und Buttons über `groups=` einschränken, wenn nur eine Gruppe sie sehen soll

### Logging
* INFO: Wichtige Geschäftsvorgänge (z.B. Import gestartet, N Auszüge erzeugt)
* WARN: Unerwartete aber behandelbare Situationen (z.B. Datei enthält keine Transaktionen)
* ERROR: Fehler mit Stacktrace

### Exception Handling
* Erwartete Fehlerfälle → `UserError` mit übersetzbarer, verständlicher Meldung
* Unerwartete Fehler → loggen und weiterwerfen, damit die Transaktion zurückgerollt wird
* Beim Parsen fremder Dateiformate defensiv vorgehen: fehlende Elemente/Attribute abfangen

### Validierung
* Eingaben validieren, bevor sie verarbeitet werden
* Datenbankseitige Invarianten über `_sql_constraints` bzw. `@api.constrains` absichern
  (Vorlage: `unique_import_id` in `account_bank_statement_import/models/account_bank_statement_import.py`)

## 5. Edge Cases & Fehlerbehandlung (Generelle Patterns)
* Leere Datei / Datei ohne Transaktionen: klare Meldung, kein leerer Auszug
* Falsches Dateiformat: Parser gibt ab, nächster Parser übernimmt (Framework-Verhalten)
* Doppelter Import derselben Transaktion: über `unique_import_id` verhindert
* Unbekanntes Bankkonto: Journal nicht automatisch ermittelbar → Benutzer muss es wählen
* ZIP-Archive: mehrere Auszüge in einer Datei korrekt einzeln verarbeiten

## 6. Zusätzliche Infos

### Laufzeit-Umgebung
Dieses Repository ist ein Git-Submodul des übergeordneten Odoo-Setups unter
`C:\data\git\odoo_glue` (Docker-Compose):

| Element | Wert |
|---------|------|
| Odoo-Container | `odoo-cloud` (Port 8080 → 8069) |
| DB-Container | `psql` (PostgreSQL 13.15-alpine) |
| Datenbank | `odoo-glue-prod` |
| Konfiguration | `config/odoodev/odoo-server.conf` |

### Zugriff auf die Datenbank
* Kein MCP-Datenbank-Server konfiguriert.
* Lesend via Docker, z.B.:
  `docker exec psql psql -U odoo -d odoo-glue-prod -c "SELECT name FROM account_bank_statement ORDER BY date DESC LIMIT 10;"`
* **Nur lesend** für Analysen. Datenänderungen laufen über Odoo, nicht über direktes SQL.

### Validierung von Änderungen
Es gibt in diesem Repository **keine lokal ausführbare Test- oder Build-Pipeline**.
Geprüft wird statisch: Syntax/Stil nach OCA-Konvention (flake8 / pylint-odoo gemäss
`.travis.yml`), Manifest-Konsistenz und Code-Review gegen die Vorlagen in `CLAUDE.md`.
