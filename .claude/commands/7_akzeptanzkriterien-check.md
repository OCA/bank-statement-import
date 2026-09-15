# Akzeptanzkriterien-Check

Prüft ob alle Akzeptanzkriterien einer Spec im Code erfüllt sind und aktualisiert die Checkboxen.

## Input

* **Feature-Name**: $ARGUMENTS (z.B. `CAMT054-Import`) → liest `Specs/[Feature-Name].md`  
  Falls nicht angegeben: aus dem Konversations-Kontext ableiten (z.B. wenn zuvor `/0_anforderungen` oder `/1_umsetzungsplan` ausgeführt wurde); nur wenn unklar: nachfragen.

---

## Sub-Agent Ausführung

> **Als Sub-Agent:** Überspringe diesen Abschnitt und fahre direkt mit **Vorgehen** fort. Analysiere NUR:
> 1. Die Anforderungen in `Specs/[Feature-Name].md`
> 2. Den tatsächlich implementierten Code
> 3. Bestehende Tests

Starte einen neuen Sub-Agenten mit dem `Agent`-Tool:

- **description:** `"Akzeptanzkriterien-Check: [Feature-Name]"`
- **prompt:**

```
Du prüfst ob alle Akzeptanzkriterien einer Spec im Code erfüllt sind.
Feature: [Feature-Name]

Lies: .claude/commands/7_akzeptanzkriterien-check.md
Fahre ab Abschnitt "Vorgehen" fort.
```

- **Hinweis:** Ersetze `[Feature-Name]` im `prompt` mit dem tatsächlichen Wert aus `$ARGUMENTS` (oder dem abgeleiteten Kontext).

---

## Vorgehen

### Phase 1: Akzeptanzkriterien extrahieren
1. Lies die Anforderungen `Specs/[Feature-Name].md`
2. Extrahiere alle Akzeptanzkriterien (Zeilen mit `[ ]` oder `[x]` im Abschnitt "Akzeptanzkriterien")
3. Extrahiere zusätzlich prüfbare Anforderungen aus:
   - Funktionale Anforderungen (FR-1, FR-2, FR-3)
   - Nicht-funktionale Anforderungen (Sicherheit, Kompatibilität)
   - Edge Cases & Fehlerbehandlung

### Phase 2: Code-Analyse pro Kriterium
Für jedes Akzeptanzkriterium systematisch prüfen:

#### Oberfläche / Menü
- View-Record in `<modul>/views/*.xml` vorhanden?
- Bei Erweiterung: korrektes `inherit_id` mit `ref="<modul>.<view_id>"`?
- Action und Menüeintrag vorhanden und über `groups=` richtig eingeschränkt?
- Ist die XML-Datei im Manifest unter `data` eingetragen?

#### Model & Persistierung
- Felder mit korrektem Typ im Model vorhanden (`fields.*`)?
- `_sql_constraints` / `@api.constrains` für geforderte Invarianten?
- CRUD-Überschreibungen rufen `super(...)` auf?
- Bei firmenbezogenen Daten: `company_id` + Record Rule?
- Datenmigration nötig und unter `<modul>/migrations/<version>/post-migrate.py` vorhanden?
- Manifest-`version` erhöht?

#### Import / Parser (Kernfunktion dieses Repos)
- Parser als `models.AbstractModel` mit eigenem `_name` vorhanden?
- Bricht der Parser bei fremdem Format sauber ab (nächster Parser kommt zum Zug)?
- Doppelte Transaktionen über `unique_import_id` ausgeschlossen?
- Beispieldatei unter `<modul>/test_files/` und Import-Test vorhanden?

#### Validierungen
- Validierungslogik im Model bzw. Parser vorhanden?
- Fehlermeldungen als `UserError` mit `_()` übersetzbar?

#### Übersetzungen (i18n)
- Neue UI-Texte englisch im Code und mit `_()` umschlossen?
- Keine hartcodierten, nicht übersetzbaren Benutzertexte?
- Deutsche Texte (falls in dieser Änderung gepflegt) mit Umlauten (`ä`/`ö`/`ü`) statt `ae`/`oe`/`ue`?

#### Sicherheit / Zugriffsrechte
- Bei neuem eigenem Model: `<modul>/security/ir.model.access.csv` vorhanden und im Manifest
  unter `data` eingetragen?
- Wird die in der Spec genannte Gruppe (z.B. `account.group_account_manager`) tatsächlich
  verwendet – in der ACL-Datei bzw. als `groups=` an Menü/Feld/Button?
- Kein ungewollt offener Zugriff (ACL mit Schreibrechten für alle)?

#### Kompatibilität
- Odoo-8-/Python-2.7-konform (`from openerp import ...`, `super(Klasse, self)`, keine f-Strings)?
- XML mit `<openerp><data>` als Wurzel (nicht `<odoo>`)?

### Phase 3: Ergebnis-Bericht + Spec aktualisieren

1. Zeige dem User den Bericht im folgenden Format **im Chat** (keine separate Datei erstellen):

```markdown
# Akzeptanzkriterien-Check: [Feature-Name]

## Ergebnis: X/Y Kriterien erfüllt

| # | Kriterium | Status | Nachweis |
|---|-----------|--------|----------|
| 1 | Beschreibung... | ✅ OK | View `account_journal.xml:5`, im Manifest unter `data` |
| 2 | Beschreibung... | ✅ OK | `_sql_constraints` in account_bank_statement_import.py:24 |
| 3 | Beschreibung... | ❌ FEHLT | Keine Behandlung leerer Dateien gefunden |

## Zusätzliche Befunde
- Befunde die nicht direkt ein Akzeptanzkriterium betreffen, aber relevant sind
```

2. Aktualisiere direkt im Anschluss die Checkboxen in der Spec-Datei:
   * **Nur erfüllte Kriterien** von `[ ]` auf `[x]` ändern
   * Nicht erfüllte Kriterien bleiben als `[ ]`

---

## Prüfmethoden pro Kriterium-Typ

| Kriterium-Typ | Wie prüfen |
|---------------|-----------|
| "ist aus dem Menü aufrufbar" | `ir.actions.*`- und `menuitem`-Record in `views/*.xml`, Datei im Manifest unter `data` |
| "Feld X wird angezeigt" | View-Record bzw. `inherit_id`-Erweiterung mit dem Feld |
| "können erfasst, bearbeitet, gelöscht werden" | Model-Definition + ACL-Zeile mit `perm_write`/`perm_unlink` |
| "Validierung X muss gelten" | `_sql_constraints`, `@api.constrains`, Prüfung im Parser |
| "Gruppe X notwendig" | `ir.model.access.csv`-Zeile, `groups=` an Menü/Feld/Button |
| "Fehlermeldung anzeigen" | `raise UserError(_('...'))` an der passenden Stelle |
| "Daten werden gespeichert" | Feld-Definition im Model (kein DDL-Skript erwartet!) |
| "Format Y wird importiert" | Parser-`AbstractModel`, Beispieldatei in `test_files/`, Import-Test |
| "doppelter Import verhindert" | `unique_import_id` bzw. eigener Unique-Constraint |
| "pro Firma" | `company_id`-Feld + Record Rule |

---

## Wichtige Regeln
* **Konservativ bewerten** - Im Zweifel als "FEHLT" markieren
* **Nachweis liefern** - Für jedes "OK" den konkreten Code-Ort angeben (Datei:Zeile)
* **Keine Testläufe behaupten** - In diesem Repository laufen keine Tests. Ein Kriterium gilt
  über den Code als nachgewiesen, nicht über ein Testergebnis.
* **Keine Code-Änderungen** - Nur die Spec-Datei wird aktualisiert (Checkboxen), keine neue Datei erstellen

## Referenz
* `CLAUDE.md` - Projekt-Architektur und Modul-Aufbau
* `Specs/generell.md` - Allgemeine Anforderungen
