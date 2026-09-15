# CLAUDE.md

Leitfaden für Claude Code in diesem Repository.

## Projekt-Überblick

`bank-statement-import` ist ein **Odoo-8.0-Addon-Repository** – ein Fork des OCA-Repositories
`OCA/bank-statement-import` mit projektspezifischen Anpassungen (zuletzt gemergt: `jamotion/8.0`).
Es enthält Module zum Import von Bankauszügen in verschiedenen Formaten (CAMT, MT940, OFX, QIF).

**Es gibt keinen Build-Schritt.** Die Module werden von Odoo direkt aus dem Quellverzeichnis
geladen; Änderungen werden über ein Modul-Update in der laufenden Odoo-Instanz wirksam.

## Tech-Stack

| Dimension | Wert |
|-----------|------|
| Plattform | Odoo 8.0 (Namespace `openerp`, Manifest `__openerp__.py`) |
| Sprache | Python 2.7 |
| ORM / Persistenz | Odoo-ORM auf PostgreSQL – **kein** Flyway, **kein** SQLAlchemy |
| UI | Odoo Web Client – XML-Views (`ir.ui.view`), kein separates Frontend-Projekt |
| i18n | Odoo-Gettext (`i18n/*.po`, `*.pot`), Pflege via Transifex |
| Tests | Odoo-Test-Framework (`openerp.tests.common`) |
| Lizenz | AGPL-3 |
| Externe Python-Abhängigkeiten | `lxml`, `ofxparse` (nur `account_bank_statement_import_ofx`, deklariert unter `external_dependencies`) |

## Module

| Modul | Zweck |
|-------|-------|
| `account_bank_statement_import` | Basis-Framework für den Auszugs-Import (Wizard, Parser-Bibliothek `parserlib.py`) |
| `account_bank_statement_import_camt` | SEPA CAMT.053 / CAMT.054 |
| `account_bank_statement_import_mt940_base` | MT940-Basisparser |
| `account_bank_statement_import_mt940_nl_ing` | MT940-Variante ING |
| `account_bank_statement_import_mt940_nl_rabo` | MT940-Variante Rabobank |
| `account_bank_statement_import_ofx` | OFX |
| `account_bank_statement_import_qif` | QIF |
| `account_bank_statement_import_save_file` | Speichert die importierte Rohdatei am Auszug |
| `base_bank_account_number_unique` | Eindeutigkeit von Bankkontonummern |
| `setup/` | Von `setuptools-odoo` generierte Setup-Wrapper – **nicht** manuell bearbeiten |

## Modul-Aufbau (Konvention)

```
<modul>/
  __init__.py                  # importiert models
  __openerp__.py               # Manifest (name, version, depends, data, demo, installable)
  models/
    __init__.py
    <modell>.py                # models.Model / models.TransientModel / models.AbstractModel
  views/*.xml                  # ir.ui.view-Records, Actions, Menüs
  demo/*.xml                   # Demo-Daten (nur mit Demo-Daten geladen)
  migrations/<version>/post-migrate.py   # nur bei Datenmigration nötig
  i18n/*.po, *.pot             # Übersetzungen
  tests/__init__.py, test_*.py # Tests
  test_files/                  # Beispiel-Importdateien für Tests
  static/description/icon.png  # Modul-Icon
  README.rst                   # Beschreibung, Known issues, Credits
```

## Code-Vorlagen für deterministische Generierung

Bei der Code-Generierung die Struktur der folgenden Dateien **exakt** übernehmen:

| Neuer Code | Vorlage lesen |
|------------|---------------|
| Model-Erweiterung (`_inherit`) | `account_bank_statement_import/models/account_bank_statement.py` |
| Neues Model / Wizard (`TransientModel`) | `account_bank_statement_import/models/account_bank_statement_import.py` |
| Parser (`AbstractModel`) | `account_bank_statement_import_camt/models/parser.py` |
| Manifest | `account_bank_statement_import_camt/__openerp__.py` |
| View (Formular) | `account_bank_statement_import/views/account_bank_statement_import_view.xml` |
| View-Erweiterung (`inherit_id`) | `account_bank_statement_import/views/account_journal.xml` |
| Demo-Daten | `account_bank_statement_import_camt/demo/demo_data.xml` |
| Test | `account_bank_statement_import_camt/tests/test_import_bank_statement.py` |
| Test-Basisklasse | `account_bank_statement_import/tests/test_import_file.py` |
| Datenmigration | `account_bank_statement_import/migrations/8.0.1.0/post-migrate.py` |
| Modul-Doku | `account_bank_statement_import_camt/README.rst` |

## Konventionen

* **Python 2.7:** `# -*- coding: utf-8 -*-` als erste Zeile jeder `.py`-Datei.
  `from StringIO import StringIO`, `print` als Statement vermeiden, keine f-Strings,
  keine Python-3-only-Syntax.
* **Imports:** `from openerp import api, fields, models` – nicht `from odoo import ...`.
* **API:** Neue API verwenden (`@api.model`, `@api.multi`, `@api.one` vermeiden,
  `fields.Char(...)` statt der alten `_columns`-Notation).
* **Übersetzbare Strings:** `from openerp.tools.translate import _` und `_('Text')`.
* **Logging:** `_logger = logging.getLogger(__name__)` auf Modulebene.
* **Fehler:** `openerp.exceptions.Warning as UserError` (Odoo 8 kennt `UserError` noch nicht direkt).
* **Manifest-Version:** `8.0.<major>.<minor>.<patch>` – bei funktionalen Änderungen erhöhen.
* **Lizenzheader:** AGPL-3-Header bzw. die im jeweiligen Modul bereits verwendete Kurzform beibehalten.
* **Keine `.pyc` committen** (einzelne liegen historisch im Repo, neue nicht hinzufügen).

## Datenbank & Migrationen

* Schema-Änderungen entstehen **deklarativ** aus den Feld-Definitionen im Model – Odoo legt
  Spalten beim Modul-Update selbst an. Es gibt **keine** Migrationsskripte für Schema-DDL.
* Nur für **Datentransformationen** (Umschreiben bestehender Werte) wird ein Skript unter
  `migrations/<manifest-version>/post-migrate.py` mit `def migrate(cr, version)` angelegt.
* Manuelle DDL im Skript nur, wenn das ORM den Fall nicht abdeckt.

## Übersetzungen (i18n)

* UI-Strings kommen aus dem Quellcode (englisch) und werden über `i18n/*.po` übersetzt.
* Die `.pot`/`.po`-Dateien werden regulär über Odoo-Export bzw. Transifex gepflegt –
  **nicht** von Hand um einzelne Keys ergänzen, ausser der Auftrag verlangt es ausdrücklich.
* Deutsche Texte (z.B. in `de.po`) mit Umlauten schreiben (`ä`, `ö`, `ü`), `ß` in Schweizer
  Schreibweise als `ss`. Dateien sind UTF-8.

## Zugriffsrechte

* Dieses Repository definiert **keine** eigenen Sicherheitsgruppen und keine
  `ir.model.access.csv`. Die Rechte ergeben sich aus den erweiterten Modellen des
  Standardmoduls `account` (u.a. `account.group_account_user`, `account.group_account_manager`).
* Wird ein neues eigenes Model eingeführt, braucht es eine `security/ir.model.access.csv`
  und einen Eintrag unter `data` im Manifest.

## Laufzeit-Umgebung

Dieses Repository ist ein Git-Submodul des übergeordneten Odoo-Setups unter
`C:\data\git\odoo_glue`. Dort liegen Docker-Compose und Konfiguration:

| Element | Wert |
|---------|------|
| Odoo-Container | `odoo-cloud` (Port 8080 → 8069) |
| DB-Container | `psql` (PostgreSQL 13.15-alpine, Port 5432) |
| Datenbank | `odoo-glue-prod` |
| Konfiguration | `config/odoodev/odoo-server.conf` |
| Addons-Pfad | enthält u.a. `/var/lib/odoo/addons/github/bank-statement-import` |

## Validierung von Änderungen

Es gibt in diesem Repository **keine lokal ausführbare Test- oder Build-Pipeline**.
Änderungen werden statisch geprüft:

* Syntax/Stil gegen die OCA-Konventionen (flake8 / pylint-odoo, wie in `.travis.yml` via
  `maintainer-quality-tools` konfiguriert).
* Manifest-Konsistenz: Jede Datei unter `data` / `demo` existiert; `depends` vollständig.
* Code-Review gegen die Vorlagen oben.

Ein tatsächlicher Testlauf (`--test-enable`) erfolgt ausserhalb dieses Repos in der
Odoo-Umgebung und ist nicht Teil der Command-Workflows.

## Git-Konventionen

* Commit-Messages kurz und präzise; projektspezifisch oft mit Ticket-Präfix (`OERPGLUE-<Nr>`).
* Keine Secrets oder Credentials committen.
* Upstream ist OCA – Änderungen möglichst nah am Upstream-Stil halten, um Merges zu erleichtern.
