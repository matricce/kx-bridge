<p align="center"><img src="knlogo.png" alt="KX-Bridge Logo" width="180"/></p>

# KX-Bridge – Dev Branch

> **Achtung:** Dies ist der Entwicklungs-Branch. Builds hier sind experimentell und nicht für den produktiven Einsatz geeignet.
> Für stabile Releases → [KX-Bridge-Release](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)

---

## Versionsschema

Dev-Builds verwenden das Format:

```
<basis-version>-dev+<git-hash>
```

**Beispiel:** `0.9.1-dev+04a6a20`

- `0.9.1` – Basis der aktuellen stabilen Version
- `-dev` – kennzeichnet den Entwicklungs-Branch
- `+04a6a20` – 7-stelliger Git-Commit-Hash, eindeutig je Build

---

## Dev-Binaries testen

Dev-Releases sind auf Gitea als Pre-Releases verfügbar:
[Dev-Releases](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)

### Docker (empfohlen)

```bash
git clone <repo-url> -b dev
cd kobrax
docker compose up -d
```

### Linux-Binary

```bash
# Dev-Release herunterladen (kx-bridge-linux.zip)
unzip kx-bridge-linux.zip
chmod +x kx-bridge
./kx-bridge
```

`config/config.ini` und `data/` (SQLite + GCode-Store) werden **neben dem Binary**
angelegt. Beim Erststart ohne Drucker zeigt die UI auf `http://localhost:7125` den
Drucker-Tab mit "+ Drucker hinzufügen" — dort nur die IP eingeben, der Rest wird
automatisch importiert.

### Windows-EXE

```
# Dev-Release herunterladen (kx-bridge-windows.zip)
# kx-bridge.exe starten — config/ und data/ liegen daneben
```

---

## Update-Kanal

Dev-Versionen prüfen automatisch auf neue **Dev-Releases** — nicht auf stabile Releases.
Im Settings-Modal → „Auf Updates prüfen" zeigt den neuesten Dev-Build an.

---

## Aktive Entwicklung (Stand 2026-05-10)

Stand `dev`-Branch über v0.9.7 hinaus:

| Feature | Status |
|---------|--------|
| MMU-Emulation (`/printer/objects/query?mmu`) für OrcaSlicer Filament-Sync | ✅ |
| GCode Store (SQLite + Thumbnails) | ✅ |
| Browser-Tab mit Suche/Filter/Sortierung | ✅ |
| Filament-Dialog: Per-Kanal-Remapping (GCode-Kanal → AMS-Slot) | ✅ |
| MQTT Print-Payload `ams_settings.ams_box_mapping` (nested) | ✅ |
| Print-History in SQLite | ✅ |
| Multi-Printer Support (Drucker-Tab + Header-Dropdown) | ✅ |
| **Multi-Printer in einer Bridge-Instanz** (ein Prozess, N Listener) | ✅ |
| Drucker-Emulator (`_archive/tools/kx_printer_emulator.py`) | ✅ |
| i18n DE/EN für alle neuen UI-Elemente | ✅ |

---

## Multi-Printer-Setup

Eine Bridge-Instanz kann jetzt mehrere Drucker gleichzeitig verwalten — ein Prozess,
N MQTT-Verbindungen, N HTTP-Listener, geteilte SQLite + GCode-Verzeichnis.

### Konfiguration

In `config/config.ini` pro Drucker eine `[printer_N]`-Sektion anlegen:

```ini
[printer_1]
name       = Kobra X
printer_ip = <DRUCKER_IP_1>
mqtt_port  = 9883
username   = <MQTT_USER>
password   = <MQTT_PASSWORT>
mode_id    = 20030
device_id  = <DEVICE_ID_1>
http_port  = 7125

[printer_2]
name       = Drucker 2
printer_ip = <DRUCKER_IP_2>
mqtt_port  = 9883
username   = <MQTT_USER>
password   = <MQTT_PASSWORT>
mode_id    = 20030
device_id  = <DEVICE_ID_2>
http_port  = 7126
```

Credentials per `extract_credentials` oder `fetch_credentials` ermitteln (siehe Haupt-README).

`http_port` ist optional — Default ist `7125 + (N-1)`. Wenn keine `[printer_N]`-Sektionen
existieren, läuft die Bridge im klassischen Einzel-Modus mit `[connection]` und einem Listener.

### Docker

`docker-compose.yml` exposed jetzt einen Port-Range `7125-7130`:

```yaml
ports:
  - "7125-7130:7125-7130"
```

```bash
docker compose up -d
# Drucker 1: http://localhost:7125
# Drucker 2: http://localhost:7126
```

OrcaSlicer / Mainsail richten den Klipper-Endpunkt pro Drucker auf den jeweiligen Port —
keine Slicer-Anpassungen nötig.

---

## Stabile Version

Für den produktiven Einsatz bitte die stabile Version verwenden:
[→ Zum stabilen Release](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)
