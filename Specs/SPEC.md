# Titel des Features / der Änderung

## 1. Ziel & Kontext - Warum wird das Feature benötigt?
* **Was soll erreicht werden:** (Kurze Zusammenfassung)
* **Warum machen wir das:** (Business Value / Hintergrund)
* **Aktueller Stand:** Wie funktioniert es jetzt? (Falls relevant)
* **Betroffenes Modul:** z.B. `account_bank_statement_import_camt` (neu oder bestehend?)

## 2. Funktionale Anforderungen (FR) - Was soll das System tun?
### FR-1: Ablauf / Flow
1. User öffnet...
2. System validiert...
3. System speichert...

### FR-2: Datenmodell & Persistierung
* Betroffenes Odoo-Model (neu via `_name`, erweitert via `_inherit`)
* Felder: Name, Typ (`fields.Char` / `Many2one` / …), Pflicht/Optional, Default
* Constraints: `_sql_constraints` bzw. `@api.constrains`
* Firmenbezug: braucht es `company_id` + Record Rule?

### FR-3: Oberfläche (Views)
* Betroffene XML-Views: neu oder Erweiterung via `inherit_id` + XPath
* Menüeintrag / Action nötig?

## 3. Akzeptanzkriterien - Wann ist die Anforderung erfüllt? (testbar)
* [ ] Muss X können
* [ ] Darf Y nicht zulassen
* [ ] Muss Fehlermeldung Z anzeigen, wenn...

## 4. Nicht-funktionale Anforderungen (NFR)

### NFR-1: Performance
* z.B. "Import einer Datei mit 5000 Transaktionen darf nicht in einen Timeout laufen"

### NFR-2: Sicherheit
* Zugriffsrechte explizit nennen, z.B. "nur für Buchhaltungs-Verantwortliche"
  (`account.group_account_manager`) bzw. "für Buchhaltung allgemein"
  (`account.group_account_user`)
* Bei neuem eigenem Model: `security/ir.model.access.csv` gefordert?

### NFR-3: Kompatibilität
* z.B. bestehende Daten müssen nach dem Modul-Update weiter funktionieren
* Manifest-Version erhöhen? Datenmigration nötig?
* Bleibt die Änderung mergefähig zum OCA-Upstream?

## 5. Edge Cases & Fehlerbehandlung
Typische Fälle prüfen:
* Was passiert bei leeren Eingaben / leeren Dateien?
* Was passiert bei unerwartetem oder beschädigtem Dateiformat?
* Was passiert beim Löschen von referenzierten Daten?
* Was passiert bei erneutem Import derselben Daten (Duplikate)?
* Was passiert bei ungültigen / doppelten Werten?

## 6. Abhängigkeiten & betroffene Funktionalität
* **Voraussetzungen:** Welche Module müssen im Manifest unter `depends` stehen?
* **Externe Bibliotheken:** Neue Python-Pakete unter `external_dependencies` nötig?
* **Betroffener Code:** Welcher bestehende Code muss angepasst werden?
* **Datenmigration:** Müssen bestehende Daten transformiert werden
  (→ `migrations/<version>/post-migrate.py`)?
* **Übersetzungen:** Neue übersetzbare Strings (`_()`)? Betrifft `i18n/*.po`.

## 7. Abgrenzung / Out of Scope
* Was wird bewusst **nicht** umgesetzt?

## 8. Offene Fragen
* Punkte die noch geklärt werden müssen bevor die Umsetzung startet
