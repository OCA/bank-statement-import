# Init: Commands & Specs an neue Codebasis anpassen

Dieser Command passt die kopierten Commands (`.claude/commands/`) und Specs (`Specs/`) an eine neue Codebasis an. Er analysiert die neue Projektstruktur und aktualisiert alle projektspezifischen Referenzen.

## Voraussetzung

Diese Commands und Specs sind eng auf den Glue-Starter-Stack zugeschnitten: Multi-Modul-Maven mit Spring-Boot-Backend, Angular-Frontend, Hibernate-Multi-Tenancy, Flyway, Keycloak und eigenem Design System. Die Anpassung funktioniert deterministisch, solange das Zielprojekt eine **vergleichbare Architektur** hat (das 1:1-Mapping in Phase 2 setzt das voraus).

Weicht der Stack grundlegend ab (z.B. kein Java/Spring, kein Angular, keine relationale DB / kein Flyway), ist die Anpassung eher eine Teil-Neuschreibung als ein Mapping. In dem Fall:
- **Zuerst mit dem User Rücksprache halten**, bevor grössere Umbauten gemacht werden — klären, welche Commands überhaupt sinnvoll übertragbar sind.
- Nicht übertragbare Commands lieber als Stub mit Hinweis belassen oder entfernen, statt sie mit erfundenen Pfaden/Konventionen zu „raten".

## Vorgehen

### Phase 1: Neue Codebasis analysieren

Lies und analysiere die neue Codebasis. Suche nach folgenden Informationen:

**Projektstruktur:**
1. Lies `CLAUDE.md` (falls vorhanden) für Projektüberblick
2. Glob nach `pom.xml` und `package.json` auf Root-Ebene und in Unterverzeichnissen
3. Identifiziere die Modulnamen (z.B. `backend-service`, `frontend-service`)

**Backend:**
- Erkenne die Server-/Framework-Plattform (z.B. Spring Boot, Payara) und lies die Version (aus `pom.xml`)
- Java-Package-Name (z.B. `ch.glue` → via Glob `src/main/java/**/*.java`, dann den Package-Pfad lesen)
- Java-Version (aus `pom.xml`)
- Testcontainer-Version (aus `pom.xml`)
- Vorhandene Entities, Services, Controller, Repositories als Template-Referenzen

**Frontend:**
- Erkenne das Front-/UI-Framework (z.B. Angular, Vaadin) und lies die Version
- TypeScript-Version (aus `package.json`)
- Frontend-Modulname

**Design System:**
- Ist ein eigenes Design System vorhanden? (`design-system/` oder ähnlich)
- Falls ja: Verfügbare CSS-Klassen (aus `design-system/src/components/` oder ähnlichem)
- Falls nein: Welches CSS-Framework wird verwendet?

**Datenbank:**
- Erkenne den Datenbanktyp (z.B. PostgreSQL, MySQL) und lies die Version
- Wird Flyway verwendet? Falls ja, erkenne das Flyway-Migrations-Verzeichnis
- DB-Schema (aus Migrations oder `docker-compose.yml`)
- Gibt es MCP-Server-Konfigurationen?

**Auth:**
- Authentifizierungssystem (Keycloak, Auth0, eigenes, keines?)
- Rollen-Namen

**Docker:**
- `docker-compose.yml` lesen: Service-Namen, Ports

### Phase 2: Diff zum Glue-Starter ermitteln

Erstelle eine interne Übersicht der Unterschiede zwischen Glue-Starter und der neuen Codebasis:

| Dimension | Glue-Starter (alt) | Neues Projekt |
|-----------|-------------------|---------------|
| Java Package | `ch.glue` | `<neu>` |
| Backend-Modul | `backend-service` | `<neu>` |
| Frontend-Modul | `frontend-service` | `<neu>` |
| Spring Boot | 4.0.4 | `<neu>` |
| Java | 25 | `<neu>` |
| Angular | 21.2.6 | `<neu>` |
| TypeScript | 5.9.3 | `<neu>` |
| PostgreSQL | 16-alpine | `<neu>` |
| DB-Schema | `app` | `<neu>` |
| Auth | Keycloak | `<neu>` |
| Rollen | `user`, `admin` | `<neu>` |
| MCP DB-Server | `glue-db` | `<neu>` |
| Design System | `@glue/design-system` | `<neu>` |

### Phase 3: CLAUDE.md erstellen oder aktualisieren

Falls keine `CLAUDE.md` existiert: Erstelle eine neue basierend auf der analysierten Projektstruktur (orientiere dich an der Glue-Starter-Struktur, passe Inhalte an).

Falls eine `CLAUDE.md` existiert: Ergänze fehlende Abschnitte:
- Code-Vorlagen-Tabelle (Backend + Frontend) mit tatsächlichen Dateipfaden
- Build-Befehle
- Architektur-Übersicht
- Datenbankzugriff

### Phase 4: `Specs/generell.md` anpassen

Aktualisiere `Specs/generell.md` mit den ermittelten Werten:

**Technische Spezifikationen:**
- Java-Version aktualisieren
- Backend: Server-/Framework-Plattform
- Frontend: Front-/UI-Framework
- Design System: Abschnitt anpassen
  - Falls eigenes Design System: CSS-Klassen aus dem tatsächlichen Design System ermitteln und Tabelle ersetzen
  - Falls kein Design System (z.B. Bootstrap, Tailwind, eigenes): Abschnitt entsprechend umschreiben (verfügbare Klassen/Komponenten des genutzten Frameworks)
  - Build-Befehl anpassen oder entfernen

**Multi-Tenancy:**
- Falls keine Multi-Tenancy: Abschnitt auf `n/a` setzen und erklären
- Falls andere Implementierung: Anpassen

**Mehrsprachigkeit (i18n):**
- Falls kein i18n: Abschnitt auf `n/a` setzen
- Falls andere i18n-Implementierung: Anpassen

**Navigation:**
- Falls kein Keycloak: Abschnitt «Navigation» (Vorname/Nachname aus Keycloak-Token) anpassen oder entfernen

**Authentifizierung & Autorisierung:**
- Auth-System anpassen (Keycloak → `<neues System>`)
- Rollen aktualisieren

**Datenbankzugriff:**
- MCP-Server-Name aktualisieren (oder entfernen falls nicht vorhanden)
- Docker-Befehl mit neuem Container-Namen und Schema anpassen

### Phase 5: `Specs/SPEC.md` anpassen

Aktualisiere `Specs/SPEC.md`:
- Multi-Tenancy-Abschnitt: `org_id` Hinweise (Datenmodell-Tabelle in Abschnitt 2) anpassen oder entfernen
- i18n-Abschnitt («Übersetzungen»): Anpassen oder entfernen
- Auth-Rollen (`user`/`admin`, `@PreAuthorize`, `AuthGuard`): Aktualisieren
- Design-System-Klassen-Referenz (`.app-container`, `.app-table`, …): Anpassen oder entfernen
- Layout & Navigation: Pfad `frontend-service/src/app/components/navigation/navigation.component.html` mit neuem Modulnamen anpassen

### Phase 6: Commands anpassen

Aktualisiere alle Commands in `.claude/commands/`. Für jeden Command zuerst den Inhalt lesen, dann gezielt die projektspezifischen Stellen ersetzen.

**0_anforderungen.md**
- Referenz auf `Specs/Übersetzungsverwaltung.md` als Beispiel: durch eine passende Spec des neuen Projekts ersetzen (oder entfernen, falls keine vorhanden)
- Hinweis «Sicherheit (NFR-2): Rollen explizit nennen (`user` oder `admin`)»: Rollennamen an das neue Projekt anpassen
- Hinweis «Multi-Tenancy» (`org_id`): entfernen falls nicht relevant
- Hinweis «i18n» (`TranslationService`): entfernen falls nicht relevant

**0_anforderungen-check.md**
- Multi-Tenancy-Checks (`org_id`) entfernen falls nicht relevant
- i18n-Checks (`TranslationService`) entfernen falls nicht relevant
- Referenz auf `Specs/Übersetzungsverwaltung.md` anpassen (wie oben)

**1_umsetzungsplan.md**
- Template-Dateipfade: Java-Package `ch.glue` → neues Package
- Dateinamen-Konventionen (Tabelle): Modulnamen in den Angular-Pfaden anpassen, abweichende Muster korrigieren
- Phasen-Tabelle: Flyway-Pfad, Routing-Pfad, Navigations-Pfad anpassen
- Phasen-Tabelle: Phase «Übersetzungen» (i18n-Migration) entfernen falls kein i18n
- Hinweis «Multi-Tenancy: Neue Entities brauchen immer `org_id` (UUID), `@Filter` und `@FilterDef`»: entfernen falls nicht relevant
- Referenz auf `Specs/Übersetzungsverwaltung_Umsetzungsplan.md` anpassen

**2_umsetzung.md**
- Code-Pattern-Tabelle: Template-Dateipfade mit Java-Package und Modulnamen aktualisieren
- Validierungs-Befehle: Modul-Verzeichnisse und Build-Befehle anpassen (`mvn`, `npx ng build`, `npm.cmd` vs. `npm`)
- Abschnitt «Design System»: an das neue Projekt anpassen (Pfad `design-system/src/components/`, Build-Befehl, Showcase) oder ganz entfernen falls kein eigenes Design System
- Datenbank-Regel «Spalten-Kommentare» (`COMMENT ON COLUMN app.[tabelle]...`): Schema `app` an neues Schema anpassen
- Backend-Regeln: Falls kein Hibernate-Filter / Multi-Tenancy → `hibernateFilterService`- und `organizationContextService`-Referenzen entfernen
- Falls kein i18n: i18n-Regeln (`TranslationService`, `TranslatePipe`) entfernen

**3_backend-tests.md**
- Package-Namen (`ch.glue` → neues Package) in allen Code-Beispielen und Glob-Pfaden ersetzen
- `OrganizationContextService` / `HibernateFilterService` Mocks entfernen falls kein Multi-Tenancy
- Maven-Befehle: Modul-Verzeichnis prüfen

**4_frontend-unit-tests.md**
- Glob-Pfade (`frontend-service/src/app/**/*.ts`) mit neuem Modulnamen aktualisieren
- API-URL in Service-Tests (`localhost:8090` → neuer Backend-Port)
- `TranslationService`-Mock entfernen falls kein i18n
- npm-Befehle: Plattformspezifisch prüfen (`npm.cmd` nur auf Windows; auf anderen Systemen → `npm`)

**5_e2e-tests.md**
- Auth-Helper anpassen: `handleKeycloakLogin` → Pendant für neues Auth-System; falls kein separater Login-Flow → Helper entfernen
- Test-Credentials (`testuser`/`testpassword`) mit neuen Test-Usern aktualisieren
- Pfade (`frontend-service/tests/`, `frontend-service/src/app/app.routes.ts`) mit neuem Modulnamen aktualisieren
- Design-System-Selektoren (`.app-table`, `.app-kebab-button`) anpassen falls anderes UI-Framework
- Hardcodierten absoluten Pfad im Playwright-Report-Befehl (`C:\\data\\git\\glue-starter\\...`) durch relativen Pfad ersetzen

**6_test-gap-analyse.md**
- Alle Glob-Pfade mit Java-Package (`ch.glue`) und Modulnamen (`backend-service`, `frontend-service`) aktualisieren
- Falls kein Angular-Frontend: Frontend-Inventar-Abschnitt anpassen (andere Datei-Konventionen)
- `npm.cmd`-Befehl plattformspezifisch prüfen (wie bei `4_frontend-unit-tests.md`)

**7_akzeptanzkriterien-check.md**
- Pfade `app.routes.ts`, `navigation.component.html` mit neuem Modulnamen aktualisieren
- Multi-Tenancy-Prüfpunkte (`org_id`, `@Filter`, `@FilterDef`) entfernen falls nicht relevant
- i18n-Prüfpunkte (`TranslationService`, `TranslatePipe`) entfernen falls nicht relevant
- Auth-spezifische Prüfmethode (`@PreAuthorize` / `AuthGuard`) falls nötig anpassen

**10_vibe.md**
- Referenz auf `Specs/Übersetzungsverwaltung.md` als Beispiel anpassen

**pr_verify.md:**
- Alle Modulpfade (`backend-service/`, `frontend-service/`, `design-system/`) aktualisieren
- Build-Befehle anpassen (Modul-Verzeichnisse, `npm.cmd` vs. `npm`)
- Multi-Tenancy-Konventionschecks entfernen falls nicht relevant (`hibernateFilterService`, `orgId`, `@FilterDef`, `@Filter`)
- i18n-Konventionschecks entfernen falls nicht relevant (`TranslatePipe`, `TranslationService`)
- Design-System-Kategorisierung anpassen oder entfernen falls kein eigenes Design System

### Phase 7: Nicht relevante Specs entfernen

Lösche alle feature-spezifischen Specs, die aus dem Glue-Starter stammen und für das neue Projekt nicht relevant sind. Typische Kandidaten:
- `Specs/Übersetzungsverwaltung.md` + `Specs/Übersetzungsverwaltung_Umsetzungsplan.md`
- `Specs/Impressum-Datenschutzerklärung.md` + `Specs/Impressum-Datenschutzerklärung_Umsetzungsplan.md`
- `Specs/Kostenstellenverwaltung.md`

Behalte: `Specs/SPEC.md` (Template), `Specs/generell.md` (angepasst in Phase 4).

### Phase 8: Validierung

Prüfe die angepassten Dateien auf Konsistenz:
1. Alle Pfade in Commands zeigen auf tatsächlich existierende Dateien (stichprobenartig mit Glob prüfen)
2. Package-Namen stimmen überein
3. Build-Befehle passen zu den tatsächlichen Modul-Verzeichnissen
4. Keine verwaisten Glue-Starter-Referenzen mehr vorhanden — grepe in `.claude/commands/` und `Specs/` (ohne `99_init.md` selbst, da es die alten Werte als Referenz enthält) nach:
   - `ch.glue` (altes Java-Package)
   - `glue-db` (alter MCP-Server-Name, falls geändert)
   - `backend-service` / `frontend-service` / `design-system` (alte Modulnamen, falls geändert)
   - `@glue/design-system` (alte Design-System-Abhängigkeit)
   - `localhost:8090` / `localhost:4200` (alte Backend-/Frontend-Ports, falls geändert)
   - `Übersetzungsverwaltung`, `Impressum`, `Kostenstellenverwaltung` (Referenzen auf gelöschte Beispiel-Specs)
   - `Keycloak`, `testuser`, `testpassword` (altes Auth-System / Test-User, falls geändert)
   - `C:\\data\\git\\glue-starter` (absoluter Pfad aus E2E-Command)

## Output

Am Ende: Kurze Zusammenfassung der vorgenommenen Änderungen:

```
## Init abgeschlossen

### Angepasst
- CLAUDE.md: [erstellt / ergänzt]
- Specs/generell.md: [was geändert wurde]
- Specs/SPEC.md: [was geändert wurde]
- .claude/commands/: [N Dateien aktualisiert]

### Entfernt
- [Dateien die gelöscht wurden]

### Manuelle Nacharbeit empfohlen
- [Punkte die manuell geprüft werden sollten]
```

## Hinweise

- **Konservativ vorgehen:** Lieber nachfragen als falsche Annahmen treffen
- **Keine Features erfinden:** Nur anpassen was nachweislich vorhanden oder nicht vorhanden ist
- **Rückfragen:** Falls wesentliche Informationen fehlen (z.B. Auth-System unklar), fragen BEVOR Änderungen gemacht werden
- **Sicherheitskopie:** Der User sollte die Dateien vorher committen, damit Änderungen rückgängig gemacht werden können
- **Selbst-Bereinigung:** Nach erfolgreichem Init kann `99_init.md` gelöscht werden — es enthält nur die alten Glue-Starter-Werte als Referenz und wird im Zielprojekt nicht mehr benötigt (in der Zusammenfassung unter «Manuelle Nacharbeit empfohlen» erwähnen).
