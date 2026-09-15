# PR Verify

Prüft einen Pull Request auf Code-Qualität, Korrektheit und Projektkonventionen.

## Input
* PR-Nummer oder Branch: $ARGUMENTS (z.B. `42`, `feature/camt054`, oder leer für den aktuellen Stand)

---

## Sub-Agent Ausführung

> **Als Sub-Agent:** Überspringe diesen Abschnitt und fahre direkt mit **Vorgehen** fort. Analysiere NUR:
> 1. Den tatsächlichen Diff des PRs / Branches gegenüber dem Basis-Branch
> 2. Den betroffenen Code und seine Abhängigkeiten
> 3. Projekt-Konventionen aus `CLAUDE.md` und `Specs/generell.md`

Starte einen neuen Sub-Agenten mit dem `Agent`-Tool:

- **description:** `"PR Verify: [PR-Nummer/Branch]"`
- **prompt:**

```
Du prüfst einen Pull Request auf Code-Qualität, Korrektheit und Projektkonventionen.
Repository: Odoo-8.0-Addons (Python 2.7), Fork von OCA/bank-statement-import.
PR/Branch: [PR-Nummer oder Branch-Name]

Lies: .claude/commands/pr_verify.md
Fahre ab Abschnitt "Vorgehen" fort.
```

- **Hinweis:** Ersetze `[PR-Nummer oder Branch-Name]` im `prompt` mit dem tatsächlichen Wert aus `$ARGUMENTS` (oder dem aktuellen Branch falls leer).

---

## Vorgehen

### Phase 1: Diff ermitteln

**Basis-Branch bestimmen:** Dieses Repository hat **keinen** `main`-Branch. Die Branches sind
Odoo-Versionsbranches (`8.0`, `9.0`, `10.0`); `origin/HEAD` zeigt auf `10.0`, der Code-Stand
dieses Arbeitsverzeichnisses stammt aber aus der 8.0-Linie. Den korrekten Basis-Branch
ermitteln, **nicht** `main` annehmen:

```bash
git remote show origin | grep "HEAD branch"
git branch -a
git merge-base HEAD <basis-branch>
```
Bei Unklarheit den Basis-Branch beim User erfragen.

Falls eine PR-Nummer angegeben:
```bash
gh pr diff <nummer>
gh pr view <nummer> --json title,body,additions,deletions,changedFiles,baseRefName,headRefName
```

Falls ein Branch-Name oder kein Argument angegeben:
```bash
git diff <basis-branch>...HEAD --stat
git diff <basis-branch>...HEAD
git log <basis-branch>..HEAD --oneline
```

### Phase 2: Geänderte Dateien kategorisieren

- **Models / Logik:** `<modul>/models/*.py`, `<modul>/parserlib.py`
- **Tests:** `<modul>/tests/*.py`
- **Test-Fixtures:** `<modul>/test_files/*`
- **Views / Daten:** `<modul>/views/*.xml`, `<modul>/demo/*.xml`
- **Zugriffsrechte:** `<modul>/security/*.csv`, `<modul>/security/*.xml`
- **Manifest:** `<modul>/__openerp__.py`
- **Migrationen:** `<modul>/migrations/*/`
- **Übersetzungen:** `<modul>/i18n/*.po`, `*.pot`
- **Doku:** `<modul>/README.rst`, `README.md`, `CLAUDE.md`
- **Setup-Wrapper:** `setup/` (generiert – Änderungen hier hinterfragen)
- **Config / Infra:** `.travis.yml`, `.gitignore`

### Phase 3: Validierungen durchführen

> **Es gibt keine ausführbare Build- oder Testpipeline.** Kein Maven, kein npm, kein lauffähiges
> Odoo im Repo. Alle Prüfungen unten sind **statisch**. Nie behaupten, etwas sei kompiliert
> oder getestet worden.

#### 3.1 Statische Prüfungen

```bash
# XML-Wohlgeformtheit (jede geänderte XML-Datei)
python -c "import xml.etree.ElementTree as ET; ET.parse('<pfad>.xml'); print('XML ok')"

# Python-Syntax (grobe Prüfung)
python -c "import ast; ast.parse(open('<pfad>.py','rb').read()); print('Syntax ok')"
```

**Achtung:** Der Host hat Python 3.9, der Code ist Python 2.7. Der Syntax-Check fängt grobe
Tippfehler, kann aber bei legitimer Python-2-only-Syntax fälschlich anschlagen (bekannter
Fall im Repo: `account_bank_statement_import_ofx/account_bank_statement_import_ofx.py`).
Einen Treffer bewerten, nicht blind als Blocker melden.

#### 3.2 Manifest-Konsistenz

Für jedes geänderte `__openerp__.py`:
- [ ] Jede unter `data` und `demo` gelistete Datei existiert tatsächlich?
- [ ] Jede neue XML-Datei im Modul ist unter `data` bzw. `demo` eingetragen?
- [ ] `depends` enthält alle tatsächlich benutzten Module?
- [ ] Neue externe Python-Bibliotheken unter `external_dependencies` deklariert?
- [ ] `version` bei funktionaler Änderung erhöht (`8.0.<major>.<minor>.<patch>`)?
- [ ] `installable` / `license` unverändert korrekt?

#### 3.3 Model- und Python-Konventionen

Für jede geänderte `*.py`:
- [ ] `# -*- coding: utf-8 -*-` als erste Zeile?
- [ ] `from openerp import ...` (nicht `from odoo import ...`)?
- [ ] Neue API (`@api.model`, `@api.multi`, `fields.*`) – kein `@api.one`, keine `_columns`?
- [ ] `super(KlassenName, self)` – **nicht** das argumentlose `super()` aus Python 3?
- [ ] Keine Python-3-Syntax (f-Strings, Type-Hints, `yield from`)?
- [ ] CRUD-Überschreibungen rufen `super(...)` auf und geben dessen Ergebnis zurück?
- [ ] Benutzerfehler als `UserError(_('...'))` – übersetzbar und verständlich?
- [ ] Neue Datei in `models/__init__.py` bzw. `tests/__init__.py` eingetragen?
- [ ] `_logger` statt `print` für Diagnose-Ausgaben?

Für jeden geänderten Parser:
- [ ] `models.AbstractModel` mit eigenem `_name`?
- [ ] Bricht bei fremdem Format sauber ab, statt eine unspezifische Exception zu werfen?
- [ ] Fehlende Elemente/Attribute defensiv behandelt (Default statt `KeyError`)?

#### 3.4 View-Konventionen

Für jede geänderte `*.xml`:
- [ ] Wurzel `<openerp><data>` (nicht `<odoo>` – das gibt es erst ab Odoo 9)?
- [ ] Bestehende Views über `inherit_id` + Position/XPath erweitert statt kopiert?
- [ ] `ref=` verweist auf eine existierende View-ID im angegebenen Modul?
- [ ] Sichtbarkeit wo nötig über `groups=` eingeschränkt?
- [ ] Datei im Manifest eingetragen (siehe 3.2)?

#### 3.5 Datenbank & Migrationen

- [ ] **Kein** DDL-/Schema-Skript hinzugefügt (Felder entstehen deklarativ im Model)?
- [ ] Datenmigration – falls vorhanden – unter `<modul>/migrations/<manifest-version>/post-migrate.py`
      mit `def migrate(cr, version)`?
- [ ] Passt das Migrations-Verzeichnis zur **erhöhten** Manifest-Version?
- [ ] Rohes SQL nur wo nötig, und **immer** mit Parameter-Binding (kein String-Concat)?

#### 3.6 Zugriffsrechte

- [ ] Neues eigenes Model → `security/ir.model.access.csv` vorhanden und im Manifest unter `data`?
- [ ] Rechte auf die in der Spec genannte Gruppe beschränkt, keine unabsichtlich offenen Schreibrechte?
- [ ] Bei firmenbezogenen Daten: `company_id` + Record Rule?

#### 3.7 Übersetzungen

- [ ] Neue UI-Texte englisch im Code und mit `_()` umschlossen?
- [ ] Keine hartcodierten, nicht übersetzbaren Benutzertexte?
- [ ] `i18n/*.po` nur geändert, wenn das beauftragt war?
- [ ] Deutsche Texte mit Umlauten (`ä`/`ö`/`ü`) statt `ae`/`oe`/`ue`; Eszett als `ss`?
- [ ] Dateien UTF-8-kodiert?

#### 3.8 Sicherheits-Check

Prüfe im Diff auf:
- [ ] Keine Secrets / Credentials im Code (Passwörter, API-Keys, Tokens)?
- [ ] Kein `print` / Logging mit sensiblen Daten (Kontonummern, Kundendaten)?
- [ ] SQL: Keine String-Konkatenation in Queries (SQL-Injection-Risiko)?
- [ ] XML-Parsing fremder Dateien: keine Auflösung externer Entities (XXE)?
- [ ] Keine unbeabsichtigt committeten `.pyc`-Dateien oder Testdaten mit echten Kundendaten?

#### 3.9 Test-Abdeckung

- [ ] Für jeden neuen Parser: Import-Test in `<modul>/tests/` plus Beispieldatei in `test_files/`?
- [ ] Für jede neue Geschäftslogik (Constraint, CRUD-Überschreibung): Test vorhanden?
- [ ] Jedes neue Testmodul in `<modul>/tests/__init__.py` importiert
      (sonst läuft es nie – häufiger Befund)?
- [ ] Erwartungswerte in Tests stammen nachweislich aus der Beispieldatei?

#### 3.10 Upstream-Verträglichkeit

- [ ] Änderung möglichst klein und im OCA-Upstream-Stil gehalten?
- [ ] Keine unnötige Umformatierung fremder Dateien (erschwert künftige Merges)?
- [ ] `setup/`-Dateien unverändert (die werden generiert)?

---

## Phase 4: Bericht ausgeben

Gib den vollständigen Bericht im folgenden Format aus:

```markdown
# PR Verify: [Branch/PR-Titel]

## Übersicht
- Branch: `feature/xxx` → `<basis-branch>`
- Geänderte Dateien: X (Models: A, Views: B, Tests: C, Manifest: D, i18n: E)
- Additions: +X, Deletions: -Y

## Statische Prüfungen

| Check | Status | Details |
|-------|--------|---------|
| XML wohlgeformt | ✅ / ❌ | |
| Python-Syntax | ✅ / ❌ / ➖ | (Python-3-Check auf Python-2-Code – Treffer bewerten) |
| Manifest-Konsistenz | ✅ / ❌ | |

> Hinweis: In diesem Repository laufen keine Tests und kein Build. Es wurde ausschliesslich
> statisch geprüft.

## Konventions-Check

### Python / Models
| Datei | Check | Status | Bemerkung |
|-------|-------|--------|-----------|
| models/xxx.py | openerp-Import | ✅ | |
| models/xxx.py | super(Klasse, self) | ❌ | Zeile 42: argumentloses super() |

### Views / Manifest
| Datei | Check | Status | Bemerkung |
|-------|-------|--------|-----------|
| views/xxx.xml | Wurzel `<openerp>` | ✅ | |
| __openerp__.py | version erhöht | ⚠️ | unverändert bei funktionaler Änderung |

### Zugriffsrechte & i18n
| Datei | Check | Status | Bemerkung |
|-------|-------|--------|-----------|
| ... | ... | ... | ... |

## Sicherheit
| Check | Status | Bemerkung |
|-------|--------|-----------|
| Keine Secrets | ✅ | |
| Kein SQL-Injection-Risiko | ✅ | |

## Test-Abdeckung
| Implementierung | Test | Status |
|-----------------|------|--------|
| models/parser.py | tests/test_import_bank_statement.py | ✅ |
| models/xxx.py | – | ❌ FEHLT |

## Zusammenfassung

### Kritische Probleme (Blocker)
1. ...

### Warnungen (sollten behoben werden)
1. ...

### Hinweise (optional)
1. ...

### Gesamturteil
✅ PR ist merge-ready / ⚠️ Kleinere Probleme / ❌ Kritische Probleme müssen behoben werden
```

---

## Symbole

| Symbol | Bedeutung |
|--------|-----------|
| ✅ | Erfüllt |
| ⚠️ | Warnung – sollte behoben werden |
| ❌ | Kritisches Problem – muss behoben werden |
| ➖ | Nicht anwendbar |

---

## Wichtige Regeln

* **READ-ONLY**: Dieser Command ändert keinen Code – er analysiert und berichtet nur
* **Nur relevante Checks**: Prüfe nur Bereiche, die im Diff tatsächlich geändert wurden
* **Konkrete Nachweise**: Für jedes Problem Datei:Zeile angeben
* **Konservativ bewerten**: Im Zweifel als Warnung oder Blocker markieren
* **Keine Testläufe behaupten**: Es wird ausschliesslich statisch geprüft

## Referenz
* `CLAUDE.md` – Architektur, Modul-Aufbau, Konventionen
* `Specs/generell.md` – Odoo-Konventionen, i18n, Zugriffsrechte
* `.claude/commands/2_umsetzung.md` – verbindliche Code-Patterns
* `.claude/commands/3_backend-tests.md` – Test-Konventionen
