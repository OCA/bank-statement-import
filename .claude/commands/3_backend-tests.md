# Erstelle Backend-Tests

Erstelle Tests für Odoo-Module dieses Repositories (Odoo-8-Test-Framework, Python 2.7).

## Input
 
* **Feature-Name**: $ARGUMENTS (z.B. `CAMT054-Import`) → liest `Specs/[Feature-Name].md`  
  Falls nicht angegeben: aus dem Konversations-Kontext ableiten (z.B. wenn zuvor `/0_anforderungen` oder `/1_umsetzungsplan` ausgeführt wurde); nur wenn unklar: nachfragen.

---

## Sub-Agent Ausführung

> **Als Sub-Agent:** Überspringe diesen Abschnitt und fahre direkt mit **Vorgehen** fort. Analysiere NUR:
> 1. Die Anforderungen in `Specs/[Feature-Name].md`
> 2. Den tatsächlich implementierten Code
> 3. Bestehende Tests als Vorlage

Starte einen neuen Sub-Agenten mit dem `Agent`-Tool:

- **description:** `"Backend-Tests: [Feature-Name]"`
- **prompt:**

```
Du erstellst Tests für Odoo-Module (Odoo 8.0, Python 2.7).
Feature: [Feature-Name]

Lies: .claude/commands/3_backend-tests.md
Fahre ab Abschnitt "Vorgehen" fort.
```

- **Hinweis:** Ersetze `[Feature-Name]` im `prompt` mit dem tatsächlichen Wert aus `$ARGUMENTS` (oder dem abgeleiteten Kontext).

---

## ⚠️ Wichtig: Tests werden hier nicht ausgeführt

In diesem Repository gibt es **keine lokal ausführbare Testumgebung** – kein Odoo, keine
Datenbank, kein Test-Runner. Tests werden **geschrieben**, aber nicht gestartet. Der Lauf
erfolgt später in der Odoo-Umgebung (Modul-Update mit `--test-enable`).

**Nie behaupten, Tests seien grün.** Im Bericht ausdrücklich vermerken, dass die Tests
statisch erstellt und nicht ausgeführt wurden.

---

## Vorgehen

### Phase 1: Unabhängige Code-Analyse
1. Lies die Anforderungen `Specs/[Feature-Name].md`
2. Finde alle relevanten Implementierungs-Dateien:
   - `<modul>/models/*.py` – Models und Parser
   - `<modul>/parserlib.py` – gemeinsame Parser-Strukturen (nur im Basismodul)
3. Analysiere die öffentliche API: Methoden, Parameter, Rückgaben, ausgelöste Exceptions
4. Identifiziere Edge Cases aus dem Code selbst (Default-Werte, Constraints, Fehlerbehandlung)

### Phase 2: Test-Gap-Analyse
1. Prüfe existierende Tests in `<modul>/tests/`
2. Vergleiche mit Spec-Anforderungen und implementiertem Code
3. Liste fehlende Test-Cases auf

### Phase 3: Test-Erstellung
1. Erstelle Tests für fehlende Cases (Vorlagen unten beachten)
2. Trage jedes neue Testmodul in `<modul>/tests/__init__.py` ein
3. Lege benötigte Beispieldateien unter `<modul>/test_files/` ab
4. Prüfe die Datei statisch (Syntax, Imports) – siehe Validierung

---

## Test-Framework

* **Basis:** `from openerp.tests.common import TransactionCase`
  (jeder Test läuft in einer Transaktion, die danach zurückgerollt wird)
* **Namenskonvention:** Dateien `<modul>/tests/test_<beschreibung>.py`, Klassen `Test<Etwas>`,
  Methoden `test_<beschreibung>`
* **Registrierung:** Jedes Testmodul muss in `<modul>/tests/__init__.py` importiert werden –
  sonst wird es nie ausgeführt
* **Zugriff auf Models:** `self.env['model.name']`
* **Ressourcen laden:** `from openerp.modules.module import get_module_resource`
* **Ausführung (ausserhalb dieses Repos):** Modul-Update mit `--test-enable`

### Gemeinsame Basisklasse für Import-Tests

Für Tests, die eine Bankauszugs-Datei importieren, existiert bereits eine Basisklasse:

```python
from openerp.addons.account_bank_statement_import.tests import TestStatementFile
```

Sie liegt in `account_bank_statement_import/tests/test_import_file.py` und stellt bereit:

| Methode | Zweck |
|---------|-------|
| `_test_statement_import(modul, dateiname, statement_name, local_account=…, start_balance=…, end_balance=…, transactions=[…])` | Importiert eine Datei aus `<modul>/test_files/` und prüft den erzeugten Auszug |
| `_test_transaction(statement_obj, remote_account=…, transferred_amount=…, value_date=…, ref=…)` | Prüft eine einzelne Transaktion des Auszugs |

**Für einen neuen Import-Parser immer diese Basisklasse verwenden** – keinen eigenen
Import-Testaufbau nachbauen.

---

## Datei-Struktur (exakt einhalten)

### Import-Parser-Test (Regelfall für dieses Repo)

Vorlage: `account_bank_statement_import_camt/tests/test_import_bank_statement.py`

```python
# -*- coding: utf-8 -*-
"""Run test to import <format>."""
# Copyright <Jahr> <Autor>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp.addons.account_bank_statement_import.tests import (
    TestStatementFile)


class TestImport(TestStatementFile):
    """Run test to import <format>."""

    def test_statement_import(self):
        """Test correct creation of single statement."""
        transactions = [
            {
                'remote_account': '<IBAN>',
                'transferred_amount': -754.25,
                'value_date': '2014-01-05',
                'ref': '<referenz>',
            },
        ]
        self._test_statement_import(
            '<modul>', '<datei im test_files-Verzeichnis>',
            '<erwarteter Statement-Name>',
            local_account='<IBAN>',
            start_balance=15568.27, end_balance=15121.12,
            transactions=transactions
        )
```

### Model-/Logik-Test

Vorlage: `account_bank_statement_import/tests/test_res_partner_bank.py`

```python
# -*- coding: utf-8 -*-
"""<Kurzbeschreibung>."""
# Copyright <Jahr> <Autor>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp.tests.common import TransactionCase


class Test<Etwas>(TransactionCase):
    """<Kurzbeschreibung>."""

    def setUp(self):
        super(Test<Etwas>, self).setUp()
        self.<model>_model = self.env['<model.name>']
        # Testdaten anlegen

    def test_<szenario>_<erwartung>(self):
        """<Was geprüft wird>."""
        record = self.<model>_model.create({...})
        self.assertEqual(record.<feld>, <erwartet>)
```

### `tests/__init__.py`

```python
# -*- coding: utf-8 -*-
"""Define tests to be run."""
from . import test_<beschreibung>
```

---

## Verbindliche Regeln

* **Python 2.7:** `# -*- coding: utf-8 -*-` als erste Zeile, `super(Klasse, self).setUp()`
  (nicht das argumentlose `super()`), keine f-Strings
* **Keine Fremd-Frameworks:** kein `pytest`, kein `mock`-Zwang – das Odoo-Framework reicht;
  Abhängigkeiten werden nicht gemockt, sondern gegen die echte Testdatenbank gefahren
* **Transaktions-Isolation:** Keine Daten manuell aufräumen – `TransactionCase` rollt zurück
* **Keine Abhängigkeit von Demo-Daten anderer Module**, ausser sie stehen im Manifest
* **Beispieldateien** gehören nach `<modul>/test_files/` und werden über
  `get_module_resource` bzw. die Basisklasse geladen – keine absoluten Pfade
* **Assertions konkret:** `assertEqual` auf konkrete Werte statt `assertTrue(...)` auf
  Wahrheitswerte
* **Neue Testdatei immer in `tests/__init__.py` eintragen**

## Naming-Konvention für Test-Methoden

```
test_<szenario>_<erwartung>
```
Beispiele:
- `test_statement_import`
- `test_zip_import`
- `test_wrong_format_is_skipped`
- `test_duplicate_import_is_rejected`
- `test_empty_file_raises_user_error`

## Pflicht-Tests pro neuem Import-Parser

| Fall | Test |
|------|------|
| Gültige Datei, ein Auszug | `test_statement_import` |
| Mehrere Auszüge / ZIP | `test_zip_import` |
| Falsches Format | Parser gibt ab, kein Absturz |
| Erneuter Import derselben Datei | Duplikate werden abgewiesen (`unique_import_id`) |
| Datei ohne Transaktionen | Verständliche Meldung statt leerem Auszug |

---

## Validierung

Kein Testlauf möglich. Statisch prüfen:

* **Syntax:**
  ```bash
  python -c "import ast; ast.parse(open('<pfad>.py','rb').read()); print('Syntax ok')"
  ```
  (Der Host hat Python 3.9, der Code ist Python 2.7 – ein Treffer bei legitimer
  Python-2-Syntax ist möglich und muss bewertet, nicht blind gemeldet werden.)
* **Registrierung:** Ist das neue Testmodul in `<modul>/tests/__init__.py` importiert?
* **Fixtures:** Liegen alle referenzierten Dateien unter `<modul>/test_files/`?
* **Erwartungswerte:** Stammen die erwarteten Beträge/Daten nachweislich aus der
  Beispieldatei – nicht geraten?

## Referenz
* `CLAUDE.md` - Modul-Aufbau und Code-Vorlagen
* `Specs/generell.md` - Odoo-Konventionen
* `account_bank_statement_import/tests/test_import_file.py` - gemeinsame Test-Basisklasse
