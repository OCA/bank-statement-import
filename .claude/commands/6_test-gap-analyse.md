# Test-Gap-Analyse

Führt eine umfassende Analyse aller fehlenden Tests im Repository durch.

## Input
* Optional: $ARGUMENTS – Scope:
  * `all` – alle Addons **(Default)**
  * konkreter Modulname (z.B. `account_bank_statement_import_camt`)

---

## Sub-Agent Ausführung

> **Als Sub-Agent:** Überspringe diesen Abschnitt und fahre direkt mit **Vorgehen** fort. Analysiere NUR:
> 1. Tatsächlich vorhandene Implementierungs-Dateien
> 2. Tatsächlich vorhandene Test-Dateien
> 3. Projekt-Konventionen aus `CLAUDE.md`

Starte einen neuen Sub-Agenten mit dem `Agent`-Tool:

- **description:** `"Test-Gap-Analyse: [all/modul]"`
- **prompt:**

```
Du führst eine umfassende Test-Gap-Analyse für ein Odoo-8-Addon-Repository durch.
Scope: [all/modul] (default: all)

Lies: .claude/commands/6_test-gap-analyse.md
Fahre ab Abschnitt "Vorgehen" fort.
```

- **Hinweis:** Ersetze `[all/modul]` im `prompt` mit dem tatsächlichen Wert aus `$ARGUMENTS` (default: `all`).

---

## Vorgehen

### Phase 1: Implementierungen inventarisieren

Pro Addon (Verzeichnis mit `__openerp__.py`, ohne `setup/`):

```
<modul>/models/*.py        → Models, Wizards, Parser
<modul>/parserlib.py       → gemeinsame Parser-Strukturen (nur im Basismodul)
<modul>/views/*.xml        → Views, Actions, Menüs
<modul>/migrations/*/      → Datenmigrationen
```

Erfasse je Datei die Klassen (`models.Model`, `models.TransientModel`,
`models.AbstractModel`) und deren öffentliche Methoden.

### Phase 2: Vorhandene Tests inventarisieren

```
<modul>/tests/test_*.py    → Testmodule
<modul>/tests/__init__.py  → welche Testmodule tatsächlich registriert sind
<modul>/test_files/*       → vorhandene Beispieldateien (Fixtures)
```

### Phase 3: Gap-Analyse erstellen

Für jedes Addon prüfen:
- Existiert überhaupt ein `tests/`-Verzeichnis?
- Ist jedes vorhandene `test_*.py` in `tests/__init__.py` importiert?
  **Nicht importierte Testmodule laufen nie** – das ist ein eigener, häufig übersehener Befund.
- Gibt es zu jedem Parser einen Import-Test mit Beispieldatei?
- Gibt es zu jeder eigenen Geschäftslogik (Constraints, CRUD-Überschreibungen,
  Compute-Felder) einen Test?
- Werden die Pflicht-Fälle aus `/3_backend-tests` abgedeckt (gültige Datei, ZIP/mehrere
  Auszüge, falsches Format, doppelter Import, leere Datei)?

### Phase 4: Bericht erstellen

Ausgabe als Markdown-Tabellen:

1. **Addons im Überblick** – Tests vorhanden / registriert
2. **Models & Logik** – Test vorhanden?
3. **Parser / Importformate** – Import-Test + Fixture vorhanden?
4. **Pflicht-Fälle je Parser** – Abdeckung der Standard-Szenarien

---

## Ausgabe-Format

```markdown
# Test-Gap-Analyse

## 1. Addons im Überblick

| Addon | tests/ | in __init__ registriert | Test-Fixtures | Status |
|-------|--------|-------------------------|---------------|--------|
| account_bank_statement_import | ja | ja | – | ✅ OK |
| account_bank_statement_import_mt940_base | nein | – | – | ❌ FEHLT |

## 2. Models & Logik

| Addon | Datei / Klasse | Test | Status |
|-------|----------------|------|--------|
| ... | ... | ... | ... |

## 3. Parser / Importformate

| Addon | Format | Import-Test | Fixture | Status |
|-------|--------|-------------|---------|--------|
| ... | ... | ... | ... | ... |

## 4. Pflicht-Fälle je Parser

| Addon | gültige Datei | mehrere/ZIP | falsches Format | doppelter Import | leere Datei |
|-------|---------------|-------------|-----------------|------------------|-------------|
| ... | ✅ | ✅ | ❌ | ❌ | ❌ |

## Zusammenfassung

| Bereich | Vorhanden | Fehlend | Abdeckung |
|---------|-----------|---------|-----------|
| Addons mit Tests | X | Y | Z% |
| Parser mit Import-Test | X | Y | Z% |

## Priorisierte Empfehlungen

### Hohe Priorität
1. ...

### Mittlere Priorität
1. ...

### Niedrige Priorität
1. ...
```

---

## Priorisierungs-Kriterien

**Hohe Priorität:**
- Parser ohne jeden Import-Test (Kernfunktion des Repos)
- Nicht in `tests/__init__.py` registrierte Testmodule (laufen nie)
- Constraints und CRUD-Überschreibungen ohne Test

**Mittlere Priorität:**
- Fehlende Edge-Case-Tests bei vorhandenem Grundtest
- Datenmigrationen ohne Test

**Niedrige Priorität:**
- Reine View-Erweiterungen
- Hilfsfunktionen ohne Geschäftslogik

---

## Hinweise

- Diese Analyse ist **READ-ONLY** – es werden keine Dateien erstellt oder geändert
- Die Existenzprüfung basiert auf Dateinamen-Konventionen und dem Inhalt von `tests/__init__.py`
- **Keine Coverage-Zahlen:** Es gibt in diesem Repository keine ausführbare Testumgebung,
  also auch keinen Coverage-Report. Abdeckung wird ausschliesslich strukturell
  (Test vorhanden / nicht vorhanden) bewertet – nie eine Prozentzahl aus einem Lauf behaupten.

## Ausführung

Nach der Analyse:
1. Zeige den vollständigen Bericht
2. Frage ob Tests erstellt werden sollen
3. Bei "ja": Verwende `/3_backend-tests`

## Referenz
* `CLAUDE.md` - Modul-Übersicht und Aufbau
* `.claude/commands/3_backend-tests.md` - Test-Konventionen und Pflicht-Fälle
