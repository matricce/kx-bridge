# Changelog

## [0.9.7] – 2026-05-08

### Neu
- **fetch_credentials-Tool:** Ruft MQTT-Credentials direkt vom Drucker per HTTP ab — kein laufender Anycubic Slicer nötig, nur die Drucker-IP. Linux-Binary und Windows-EXE im Release enthalten. (Beitrag von bebu, PR #19)

### Fixes
- **Upload großer GCode-Dateien:** Dateien >1 MB wurden mit HTTP 413 abgelehnt — aiohttp `client_max_size` auf 256 MB erhöht
- **Upload-Timeout:** Socket-Timeout nach GCode-Upload von 10s auf 120s erhöht — große Dateien führten zu einem Absturz der Bridge mit leerer Antwort während der Drucker noch verarbeitete

---

## [0.9.6] – 2026-05-02

### Neu
- **Licht-Status-Synchronisierung:** Ein/Aus-Zustand und Helligkeit des Druckerlichts werden jetzt live über `light/report` MQTT gelesen — der Licht-Toggle in der UI spiegelt den echten Druckerstatus wider
- **Zeit-Minicards:** Fortschritts-Panel zeigt jetzt drei Karten — Verstrichen, Restzeit und Slicer-Schätzung — sowie einen Layer-Badge neben dem Fortschrittsbalken
- **Slicer-Schätzzeit aus GCode:** Geschätzte Druckzeit wird direkt aus der hochgeladenen GCode-Datei gelesen (OrcaSlicer: `; total estimated time:` am Dateiende, PrusaSlicer: `; estimated printing time` im Header)
- **Erweiterte Druckerstatus-Strings:** `pausing`, `paused`, `resuming`, `resumed`, `stopping`, `stopped` hinzugefügt — fehlten bisher und ließen die UI rohe Status-Codes bei Pause/Fortsetzen/Stopp anzeigen

### Fixes
- **file_ready-Banner:** Upload-Banner wird nach Stopp oder Abbruch eines Drucks nicht mehr angezeigt
- **Zeitanzeige bei Stopp/Abbruch:** Verstrichen-, Restzeit- und Slicer-Schätzung werden auf null zurückgesetzt wenn ein Druck gestoppt oder abgebrochen wird
- **start.sh:** `config/`-Verzeichnis und `config.ini.example` werden beim ersten Start automatisch angelegt wenn sie fehlen (Issue #15)

---

## [0.9.5] – 2026-05-01

### Neu
- **Upload-Banner:** Nach „Nur hochladen" erscheint ein grüner Banner mit Dateiname — „▶ Druck starten" startet den Druck direkt, „✕ Abbrechen" schließt den Banner

### Fixes
- **Auto-Print:** `auto_print` wurde nach dem Multipart-Loop immer auf `False` zurückgesetzt — OrcaSlicer „Hochladen und drucken" startete den Druck nie automatisch
- **Thumbnail:** Vorschaubild wird jetzt auch bei „Nur hochladen" angezeigt — Bridge fragt `fileDetails` direkt nach dem Upload an
- **Log Auto-Scroll:** Scroll-Position bleibt erhalten wenn Auto-Scroll deaktiviert ist — kein ungewollter Sprung nach oben mehr

---

## [0.9.4] – 2026-05-01

### Neu
- **AMS-Slot-Editor:** Slot im AMS-Panel anklicken → Dialog mit Farbpicker und Material-Auswahl (Schnellbuttons: PLA/PETG/ABS/ASA/TPU/PA/PC/HIPS oder Freitext) direkt im Browser
- **Verbessertes Log-Panel:** Vollständige MQTT-Payloads (keine Kürzung mehr), Richtungsfilter (Alle/RX/TX) und Topic-Schnellfilter (AMS / print / info / status)

### Fixes
- **i18n:** Kamera-Placeholder-Text und Log-Richtungs-Button „Alle" werden jetzt korrekt beim Sprachwechsel übersetzt

---

## [0.9.3] – 2026-05-01

### Fixes
- **Update-Check:** Stable-User erhalten keine Dev-Pre-Releases mehr — `STABLE_RELEASE_API` hatte `pre-release=true`, wodurch stabile Installationen Dev-Builds statt stabiler Releases fanden (Issue #14)
- **Version nach Update:** `VERSION`-Datei wird jetzt im Docker-Image mitgeliefert (`COPY VERSION .`) — `_write_version()` benötigt eine vorhandene Datei, ohne die wurde die Version nach dem Self-Update nie aktualisiert (Issue #14)

### Neu
- **Version im Header:** Laufende Version wird im Web-UI-Header neben dem Druckernamen angezeigt — kein Öffnen der Einstellungen nötig (Issue #14)

---

## [0.9.2] – 2026-04-29

### ⚠️ Breaking Change: Konfiguration wechselt von `.env` zu `config/config.ini`

**Migration erfolgt automatisch** beim ersten Start — keine manuelle Aktion nötig.

- Einstellungen werden ab sofort aus `config/config.ini` gelesen statt aus `.env`
- Beim ersten Start ohne `config.ini` wird die Datei automatisch aus `.env` erstellt
- **Docker:** Volume `./config:/app/config` in `docker-compose.yml` ist der persistente Speicherort — Einstellungen überleben `docker-compose restart` und Updates
- **Standalone:** `config/config.ini` liegt neben der Binary und wird bei Updates nicht überschrieben
- `.env` bleibt als read-only Fallback gemountet — kann liegen bleiben
- Zum manuellen Anlegen einer `config.ini`: Vorlage unter `config/config.ini.example`

### Neu
- **Persistente Einstellungen:** `config/config.ini` ersetzt `.env` — Einstellungen gehen nach `docker-compose restart` nicht mehr verloren (Issue #9)
- **Verbindungsfehler-Banner:** Roter Banner oben in der Web-UI wenn MQTT-Verbindung fehlschlägt (z.B. falsches Passwort, Drucker nicht erreichbar) (Issue #11)
- **Slicer-Schätzzeit:** Geschätzte Gesamtdruckzeit aus dem GCode-Header wird im Fortschritts-Panel angezeigt

### Fixes
- README: OrcaSlicer-Verbindung explizit mit `http://` und Port `:7125` dokumentiert (Issue #12)
- README: Direkter Download-Link für `extract_credentials` auf Gitea-Releases (Issue #13)

---

## [0.9.1-dev] – laufend (dev-Branch)

### Neu
- **Dev-Branch-Infrastruktur:** Versionsschema `0.9.1-dev+<hash>` — jeder Build eindeutig identifizierbar
- **Separater Update-Kanal:** Dev-Versionen prüfen auf Gitea Pre-Releases mit `-dev+` im Tag
- **AMS-Slot-Auswahl:** Einstellung „Standard-Slot (Einfarbdruck)" im Settings-Modal — fixiert einen bestimmten AMS-Kanal oder Auto (alle belegten Slots)
- **Auto-Leveling:** Checkbox im Settings-Modal — steuert `task_settings.auto_leveling` beim Druckstart
- **MQTT-Logging:** Strukturiertes TX/RX-Log mit Duplikat-Filter (`kobrax.mqtt` Logger)
- **Server-Log im Browser:** Live-Stream via SSE (`/api/log/stream`) — alle Server-Logs erscheinen im Log-Tab der UI
- **Log-Tab Verbesserungen:**
  - Auto-Scroll ein/aus — deaktiviert sich beim manuellen Hochscrollen, Button zum Reaktivieren
  - Textfilter — Live-Filterung der Log-Einträge
  - Error-Badge — roter Zähler im Tab-Button bei Fehlern/Warnungen
  - Clear-Button — Buffer leeren
  - Download-Button — letzte 500 Einträge als `kx-bridge.log`
  - Log-Fenster füllt den gesamten verfügbaren Platz (statt fester Höhe 160px)
- **Log-Buffer:** 500 Einträge (Server + Browser vereinheitlicht)
- **Changelog im Update-Dialog:** Release-Notes aus Gitea werden direkt im Update-Dialog angezeigt
- **Slicer-Schätzzeit:** Geschätzte Gesamtdruckzeit aus dem GCode-Header im Fortschritts-Panel

---

## [0.9.1-beta15] – 2026-04-26

### Fixes
- AMS: Leere Slots werden beim Druckstart übersprungen — kein `filament runout` mehr bei unbelegten Kanälen (Issue #5)
- AMS: Material-Typ wird jetzt korrekt aus dem Drucker-Protokoll gelesen (Feld `type` statt `material_type`)
- AMS UI: Leere Slots werden grau/transparent mit „Leer"-Label dargestellt

---

## [0.9.1-beta14] – 2026-04-26

### Fixes
- Z-Achse: ▲ fährt jetzt aufwärts (Z+), ▼ abwärts (Z−) — Pfeile waren vertauscht (Issue #4)
- Home All: korrekter Achsen-Code 5 — homed alle Achsen XYZ (Issue #4)
- Neuer Button „Home XY" (axis=4) in der UI
- Neuer Button „Motoren aus" (axis turnOff) in der UI

---

## [0.9.1-beta13] – 2026-04-26

### Fixes (Windows)
- Self-Update / Settings-Neustart: `os.execv` funktioniert jetzt korrekt in der PyInstaller-Binary
- Kamera: `ffmpeg nicht gefunden` crasht nicht mehr — saubere 503-Antwort wenn ffmpeg fehlt
- Reconnect-Loop: Kurze leere TCP-Reads unter Windows lösen keine sofortigen Reconnects mehr aus

### Struktur
- `bridge/`: Bridge-Dateien aus `05_scripts/` herausgelöst
- `tools/`: `extract_credentials.py` als eigenständiges Tool mit eigenem README
- `_archive/`: RE-Forschungsordner, Analyse-Tools und alte Release-Checksums archiviert
- README komplett neu: klarer 3-Schritte-Schnellstart

---

## [0.9.1-beta12] – 2026-04-25

### Fixes
- Falsche MQTT-Zugangsdaten zeigen jetzt eine verständliche Fehlermeldung statt des kryptischen `CONNACK failed: 20020005`

---

## [0.9.1-beta11] – 2026-04-25

### Fixes
- Drucker-IP wird automatisch bereinigt wenn der Nutzer versehentlich den Port miteingibt (z.B. `192.168.1.102:9883` → `192.168.1.102`)
- Settings-Modal: Hinweis erscheint wenn ein `:` in der IP erkannt wird
- `docker-compose.yml`: `.env` als Volume gemountet — Einstellungen bleiben nach `docker-compose restart` erhalten

---

## [0.9.1-beta10] – 2026-04-25

### Neu
- `start.sh` — startet die Bridge per Docker, baut das Image automatisch beim ersten Aufruf
- Tests: pytest-Suite (19 Tests) für API-State, Moonraker-Endpunkte, Settings; Installations-Smoke-Test (`test_install.sh`)
- Settings-Modal öffnet sich beim ersten Start automatisch wenn keine Zugangsdaten hinterlegt sind

### Geändert
- README: Schnellstart zeigt jetzt `./start.sh` statt manuellem `docker build`
- README: LAN-Modus korrekt als Drucker-Menüoption beschrieben
- README: Versionsnummer wird ab jetzt automatisch bei jedem Release aktualisiert
- `extract_credentials`: `--write-env` nicht mehr empfohlen — Werte im ⚙-Menü eintragen
- Dockerfile im Release-Repo: Pfade ohne `05_scripts/`-Präfix
- `release.sh`: Dockerfile für Release-Repo automatisch per `sed` angepasst

### Fixes
- Restdruckzeit (`remain_time`) wird jetzt korrekt aus `print/report` übernommen und in der UI angezeigt
- Übersetzungen: „Schrittweite" und „Ziel"-Placeholder in Temperatureingaben korrekt übersetzt

---

## [0.9.1-beta9] – 2026-04-25

### Neu
- OrcaSlicer-Profil (`kobra_x_orcaslicer_preset.zip`) als Release-Asset
- `release.sh`: OrcaSlicer-Profil wird automatisch ins Release-Repo kopiert und hochgeladen

### Geändert
- README: `extract_credentials` ohne `--write-env`, Werte manuell im ⚙-Menü eintragen
- README: Docker-Schnellstart vereinfacht

---

## [0.9.1-beta8] – 2026-04-25

### Neu
- Restdruckzeit-Anzeige in der UI (≈ Xh Ym verbleibend) aus `remain_time`-Feld
- Settings-Modal: Verbindungseinstellungen und Self-Update direkt im Browser
- Self-Update: Bridge prüft Gitea-Release-API auf neue Versionen und aktualisiert sich selbst

### Geändert
- Bridge startet im Offline-Modus wenn Drucker nicht erreichbar (kein Absturz)
- Verbinden/Trennen-Button im Header

---

## [0.9.1-beta7] – 2026-04-22

### Neu
- Offline-Start: Bridge läuft auch ohne MQTT-Verbindung, verbindet automatisch sobald Drucker erreichbar
- Verbinden/Trennen-Button im Header

---

## [0.9.1-beta6] – 2026-04-20

### Neu
- Release-ZIPs: `kx-bridge-linux.zip`, `kx-bridge-windows.zip`, `anycubic-certs.zip` mit Zertifikaten

### Fixes
- PyInstaller frozen-Binary: `__file__` durch `sys.executable`-Pfad ersetzt (Cert-Pfad-Fix)

---

## [0.9.1-beta5] – 2026-04-19

### Neu
- `kx-bridge.exe` (Windows) wird automatisch via GitHub Actions gebaut

---

## [0.9.1-beta4] – 2026-04-18

### Neu
- `release.sh`: baut Linux-Binary und Windows-EXE, lädt alle Assets auf Gitea hoch
- Englische README (`README.en.md`)

### Fixes
- `progress` und `filename` werden bei `stoped`/`canceled` korrekt auf 0 zurückgesetzt

---

## [0.9.1-beta3] – 2026-04-17

### Neu
- Druckgeschwindigkeit-Karte (Leise / Normal / Sport)
- Übersetzungen (DE/EN) vervollständigt

---

## [0.9.1-beta2] – 2026-04-17

### Fixes
- Temperatursteuerung während eines laufenden Drucks

---

## [0.9.1-beta1] – 2026-04-17

### Neu
- UI-Komplettüberarbeitung: Settings-Modal, Self-Update, Dashboard, Responsive Design
- Neue Drucker-Zustände: `pausing`, `paused`, `resuming`, `resumed`, `stopping`
- `release.sh`: Version-Bump und Release-Sync Skript

---

## [0.9.0-beta1] – 2026-04-10

### Neu
- Erster öffentlicher Release
- Docker-Deployment, Linux-Binary, `extract_credentials`-Tool
- Moonraker-kompatible HTTP/WebSocket-Bridge für den Anycubic Kobra X
- AMS Einziehen/Ausziehen, Licht- und Lüftersteuerung
- Web-UI mit Dashboard, Temperaturkarten, Achsensteuerung
