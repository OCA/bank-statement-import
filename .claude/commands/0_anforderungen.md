# Erstelle Anforderungsdokument

Erstelle ein vollständiges Anforderungsdokument (Spec) aus den eingegebenen Anforderungen.

## Input

$ARGUMENTS

* **Feature-Name** (erster Parameter): z.B. `CAMT054-Import`
* **Anforderungen** (Rest): Rohe Anforderungen, Wünsche und Rahmenbedingungen

## Vorgehen
1. **Analysiere die Eingabe** - Lies und verstehe alle angegebenen Anforderungen
2. **Recherchiere den Kontext** - Prüfe bestehende Specs in `/Specs/` auf verwandte Features und Abhängigkeiten
3. **Prüfe den bestehenden Code** - Identifiziere betroffene Odoo-Module, Models, Parser und Views
4. **Ergänze fehlende Abschnitte** - Leite aus den Anforderungen sinnvolle Akzeptanzkriterien, Edge Cases und NFR ab
5. **Stelle Rückfragen** bei wesentlichen Unklarheiten, die den Scope beeinflussen - BEVOR du das Dokument erstellst

## Output
* Erstelle eine neue Datei: `Specs/[Feature-Name].md`
* Verwende exakt die Struktur des Templates `Specs/SPEC.md`
* Der Feature-Name als H1-Titel (erster Parameter)

## Hinweise
* **Betroffenes Modul benennen:** Welches der Addons ist betroffen, oder braucht es ein neues?
  Neue Module immer mit `depends`, `data`, `installable` im Manifest spezifizieren.
* **Akzeptanzkriterien** müssen konkret und testbar sein (mit Checkbox `[ ]`)
* **Sicherheit (NFR-2):** Zugriffsrechte explizit nennen – in der Regel
  `account.group_account_user` (Buchhaltung) oder `account.group_account_manager`
  (Verantwortlicher). Bei einem **neuen eigenen Model** zusätzlich
  `security/ir.model.access.csv` als Anforderung aufnehmen.
* **Firmenbezug:** Falls neue firmenbezogene Daten gespeichert werden, auf `company_id` +
  Record Rule hinweisen (Odoo-Multi-Company) – keine selbstgebaute Mandantenlogik
* **i18n:** Neue UI-Texte werden **englisch** im Code geschrieben und mit `_()` übersetzbar
  gemacht; Übersetzungen liegen in `<modul>/i18n/*.po`. Als Abhängigkeit vermerken, wenn
  neue übersetzbare Strings entstehen.
* **Deutsche Texte** (z.B. in `de.po` oder in der Spec selbst) immer mit Umlauten schreiben
  (`ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`) – nie die Ersatzschreibweise `ae`/`oe`/`ue` (z.B. «Löschen»,
  nicht «Loeschen»); Eszett in Schweizer Schreibweise als `ss`. Dateien UTF-8-kodiert speichern.
* **Edge Cases:** Mindestens leere/fehlerhafte Eingabedateien, unbekanntes Format und
  doppelten Import behandeln
* **Kompatibilität:** Odoo 8.0 / Python 2.7 – keine Python-3-Syntax fordern. Änderungen
  sollen mergefähig zum OCA-Upstream bleiben.
* Abschnitte, für die keine Informationen vorliegen, mit sinnvollen Standardannahmen füllen und unter **8. Offene Fragen** vermerken

## Referenz
* `Specs/SPEC.md` - Template-Struktur
* `Specs/generell.md` - Allgemeine Projektanforderungen (Odoo-Konventionen, i18n, Zugriffsrechte)
* `CLAUDE.md` - Modul-Übersicht und Code-Vorlagen
