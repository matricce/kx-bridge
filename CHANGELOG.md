# Changelog

## [0.9.1-beta11] – 2026-04-25

### Fixes
- Drucker-IP wird automatisch bereinigt wenn der Nutzer versehentlich den Port miteingibt (z.B. `192.168.1.102:9883` → `192.168.1.102`)
- Settings-Modal: Hinweis erscheint wenn ein `:` in der IP erkannt wird
- `docker-compose.yml`: `.env` wird als Volume in den Container gemountet – Einstellungen bleiben nach `docker-compose restart` erhalten

---

## [0.9.1-beta10] – 2026-04-25

### Neu
- `start.sh` – startet die Bridge per Docker, baut das Image automatisch beim ersten Aufruf
- Tests: pytest-Suite (19 Tests) für API-State, Moonraker-Endpunkte, Settings; Installations-Smoke-Test (`test_install.sh`)
- Settings-Modal öffnet sich beim ersten Start automatisch wenn keine Zugangsdaten hinterlegt sind

### Geändert
- README (DE + EN): Schnellstart zeigt jetzt `./start.sh` statt manuellem `docker build`
- README: LAN-Modus korrekt als Drucker-Menüoption beschrieben (kein WLAN-Bezug)
- README: Versionsnummer wird ab jetzt automatisch bei jedem Release aktualisiert
- `extract_credentials`: kein `--write-env` mehr empfohlen – Werte im ⚙-Menü eintragen
- Dockerfile im Release-Repo: Pfade ohne `05_scripts/`-Präfix (direkt aus Repo-Root)
- `release.sh`: Dockerfile für Release-Repo automatisch per `sed` angepasst

### Fixes
- Restdruckzeit (`remain_time`) wird jetzt korrekt aus `print/report` übernommen und in der UI angezeigt
- Übersetzung: „Schrittweite" und „Ziel"-Placeholder in Temperatureingaben werden jetzt korrekt übersetzt

---

## [0.9.1-beta9] – 2026-04-25

### Neu
- OrcaSlicer-Profil (`kobra_x_orcaslicer_preset.zip`) als Release-Asset
- `release.sh`: OrcaSlicer-Profil wird automatisch ins Release-Repo kopiert und hochgeladen

### Geändert
- README: `extract_credentials` ohne `--write-env`, Werte manuell ins ⚙-Menü eintragen
- README: Docker-Schnellstart vereinfacht (kein `.env` anlegen vor dem Start nötig)

---

## [0.9.1-beta8] – 2026-04-25

### Neu
- Restdruckzeit-Anzeige in der UI (≈ Xh Ym verbleibend) aus `remain_time`-Feld des Druckers
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
- Print-Speed-Card (Leise / Normal / Sport)
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
