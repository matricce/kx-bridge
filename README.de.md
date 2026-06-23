<div align="center">

<img src="knlogo.png" alt="KX-Bridge" width="160"/>

# KX-Bridge

**Steuere deinen Anycubic Kobra X mit OrcaSlicer — ohne Klipper, ohne Raspberry Pi.**

Eine Moonraker-kompatible Bridge, die direkt mit dem Drucker spricht.

<sub>🧪 Ein Community-Bericht auf Reddit deutet darauf hin, dass die Bridge auch
mit dem **Kobra S1** und **Kobra S1 Max** funktioniert — die Protokolle wirken
kompatibel, beides ist aber weder offiziell getestet noch unterstützt.
Feedback willkommen.</sub>

<sub>🇬🇧 <a href="README.md">English version</a>  ·  🇪🇸 <a href="README.es.md">Versión española</a></sub>

<br>

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20this%20project-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/viewitde)
&nbsp;
[![Releases](https://img.shields.io/badge/Download-Releases-2EA043?style=for-the-badge&logo=gitea&logoColor=white)](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)
&nbsp;
[![Downloads](https://img.shields.io/badge/Downloads-800%2B-8957E5?style=for-the-badge&logo=gitea&logoColor=white)](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)
&nbsp;
[![Video](https://img.shields.io/badge/YouTube-Tutorial-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=1Ql4wfH27fM)

<sub>Gefällt dir KX-Bridge? Ein Kaffee auf <a href="https://ko-fi.com/viewitde">Ko-fi</a> hält das Projekt am Leben. ☕</sub>

</div>

---

## ✨ Was kann KX-Bridge?

| | Feature |
|---|---|
| 🖨️ | **Druckersteuerung** — Start, Pause, Resume, Abbruch, Temperaturen, Druckgeschwindigkeit |
| 📊 | **Live-Status** — Temperatur, Fortschritt, Layer, Restzeit, Kamera-Stream |
| 🎨 | **AMS / Multicolor** — Slots mit **Profil-Picker pro Slot** (eigene Marke aus OrcaSlicer-Profilen pro Slot zuweisen); Bridge schreibt Material und Farbe ans Drucker-Display zurück |
| 📦 | **Eigene OrcaSlicer-Profile importieren** — ZIP aus `~/.config/OrcaSlicer/user/<id>/filament/` in die Bridge ziehen; tauchen im Slot-Dropdown unter ★ Eigene Profile auf |
| 📷 | **Obico-Integration (experimentell)** — Time-Lapse und WebRTC-Livestream gegen einen selbst gehosteten [Obico-Server](https://github.com/TheSpaghettiDetective/obico-server) via moonraker-obico |
| 📐 | **H.264-Direkt-Stream + Z-Höhe** — sparsamer Kamera-Pfad für Obico, aktuelle Z aus der Layer-Höhe abgeleitet (Mm-Progress-Widget) |
| 🗂️ | **GCode-Browser** — hochgeladene Dateien mit Thumbnail, Druckhistorie, Suche & Filter |
| 🧩 | **Multi-Printer** — mehrere Drucker in **einer** Bridge-Instanz, Umschalten per Dropdown |
| ➕ | **Drucker hinzufügen per Klick** — nur die IP eingeben, Zugangsdaten werden automatisch importiert |
| 🔁 | **Robuster MQTT-Reconnect** — Bridge überlebt nächtlichen Drucker-Reboot ohne manuellen Neustart |
| 🌐 | **Mehrsprachiges UI** — DE / EN / ES / 中文, Browser-Sprache automatisch erkannt |
| 🔄 | **Self-Update** — neue Versionen direkt im Browser installieren |
| 🧠 | **OrcaSlicer** — volles Moonraker-Protokoll (HTTP + WebSocket); für korrekten Vendor-Match pro Slot den [OrcaSlicer-KX-Build](#-empfohlener-slicer) nutzen |

---

## 🚀 Schnellstart

### 1. Drucker vorbereiten

LAN-Modus am Kobra X aktivieren:
**Drucker-Display → Einstellungen → LAN-Modus aktivieren**

### 2. Bridge starten

**Docker (empfohlen):**
```bash
docker compose up -d
```

**Linux-Binary (kein Docker):**
```bash
chmod +x kx-bridge && ./kx-bridge
```

**Windows-EXE (kein Docker):**
```
kx-bridge.exe
```
> `config\` und `data\` werden neben der EXE angelegt — portabel.

> Bei Linux- und Windows-Binary liegen `config/` und `data/` (Einstellungen, SQLite,
> GCode-Store) jeweils neben dem Programm. Einfach den ganzen Ordner kopieren = umziehen.

**Python direkt:**
```bash
pip install -r bridge/requirements.txt
python bridge/kobrax_moonraker_bridge.py
```

### 3. Drucker einrichten

Web-UI öffnen: **`http://BRIDGE-IP:7125`**

Beim Erststart erscheint der **Drucker-Tab** mit *„+ Drucker hinzufügen"* — einfach die
IP-Adresse des Druckers eingeben, der Rest (Username, Passwort, Device-ID) wird automatisch
vom Drucker geholt und entschlüsselt. Fertig.

> Mehrere Drucker? Einfach mehrfach *„+ Drucker hinzufügen"* — jeder bekommt seinen eigenen
> Port (7125, 7126, …) und ist im Header-Dropdown auswählbar.

### 4. OrcaSlicer verbinden

Drucker → Verbindungstyp **Moonraker** → Host: `http://BRIDGE-IP:7125`

> ⚠️ Verbindungstyp muss **Moonraker** sein (nicht „Bambu" oder „Klipper").
> Vollständige URL inkl. `http://` und Port `:7125` im Host-Feld eintragen.

---

## 📺 Video-Tutorial

[![KX-Bridge Setup & Usage](https://img.youtube.com/vi/1Ql4wfH27fM/hqdefault.jpg)](https://www.youtube.com/watch?v=1Ql4wfH27fM)

---

## 🎨 Empfohlener Slicer

Für sauberen AMS-Filament-Sync gibt es einen **gepatchten OrcaSlicer-Build**:

→ **[OrcaSlicer-KX Releases](https://gitea.it-drui.de/viewit/OrcaSlicer-KX/releases/latest)** (Linux AppImage + Windows ZIP)

**Upstream-PRs im KX-Build:**

- **[PR #13372](https://github.com/SoftFever/OrcaSlicer/pull/13372)** — Moonraker / Happy-Hare AMS-Sync-Fix (Slot-Positionen bleiben auch bei leerem Slot in der Mitte korrekt)
- **[PR #13719](https://github.com/SoftFever/OrcaSlicer/pull/13719)** — Vendor- + Name-Matching für Moonraker (liest `name` + `vendor_name` pro Slot und matched gegen deine Filament-Presets), von [@LordGuenni](https://github.com/LordGuenni)
- **[PR #13315](https://github.com/SoftFever/OrcaSlicer/pull/13315)** — Eindeutige `filament_id` für User-Presets (neu erstellte eigene Profile bekommen eine frische ID statt das `OGFL99` vom Generic-Parent zu erben), von [@mrnoisytiger](https://github.com/mrnoisytiger)

**Plus vier KX-eigene Verbesserungen on top:**

- Bridge-Filament-Hint (`tray_info_idx` + Vendor) respektieren
- Vendor-Match auch wenn das gewählte Base-Preset **nicht is_compatible** mit dem aktiven Drucker ist (so matchen Profile aus anderen Drucker-Setups trotzdem über die Marke)
- Vendor-Match wenn `tray_info_idx` gesetzt ist, das Preset aber inkompatibel
- Zwei-Pass-Suche: erst kompatible Presets, dann alle sichtbaren

**Warum das zusammen wichtig ist:** ohne #13719 landen die AMS-Slots in OrcaSlicer alle auf `Generic PLA` / `Generic PETG`, obwohl die Bridge die konkrete Marke schon mitsendet (`name + vendor_name + gate_filament_name`). Mit dem KX-Build matched OrcaSlicer deine echten User-Presets — auch die, die du via [Eigene OrcaSlicer-Profile importieren](#-features) in die Bridge gezogen hast.

Stock-Upstream-OrcaSlicer funktioniert für Slicing und Drucken weiterhin — nur das Per-Slot-Vendor-Matching beim AMS-Sync fällt dann weg. Material und Farbe pro Slot kannst du auch ohne den KX-Build über die Bridge ans Drucker-Display schreiben (das läuft über MQTT, nicht über den Slicer).

OrcaSlicer-KX ist ein Build von [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) (AGPL-3.0); der Quellcode der Upstream-PRs ist auf GitHub, die KX-spezifischen Patches im OrcaSlicer-KX-Repo.

---

## 🏠 Community & Integrationen

- **[Home-Assistant-Integration](https://github.com/gangoke/kobrax-lan-hass-component)**
  von [@gangoke](https://github.com/gangoke) — bindet Sensoren, Drucksteuerung,
  Licht, Kamera und das GCode-Vorschaubild als native Home-Assistant-Entitäten ein.
- **[Obico (selbst gehostet)](https://github.com/TheSpaghettiDetective/obico-server)** —
  die Bridge bietet eine Moonraker-kompatible API, die
  [moonraker-obico](https://github.com/TheSpaghettiDetective/moonraker-obico)
  akzeptiert; damit hast du Time-Lapse und WebRTC-Live-Stream gegen deinen
  eigenen Obico-Server. Die KI-Spaghetti-Erkennung ist beim Kobra X
  experimentell — der Top-Down-Kamerawinkel weicht von dem ab, auf den
  das Modell trainiert wurde.

> Dies sind **Community-Projekte**, die nicht von KX-Bridge betreut oder
> supportet werden. Bei Fragen oder Problemen bitte das verlinkte Repository nutzen.

---

## 🔧 Zugangsdaten manuell ermitteln

Normalerweise nicht nötig — *„+ Drucker hinzufügen"* macht das automatisch. Falls doch:

```bash
fetch_credentials --ip 192.168.x.x --write-config
```
Holt die Zugangsdaten per HTTP direkt vom Drucker und schreibt sie in `config/config.ini`.
Nur die Drucker-IP nötig, kein Slicer.

Alternativ (wenn die IP unbekannt ist): AnycubicSlicerNext öffnen, Drucker verbinden,
dann `extract_credentials` ausführen → gibt Username, Passwort, Device-ID und IP aus.

> **Downloads:** [Releases](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases) → `fetch_credentials` / `extract_credentials` (Linux & Windows)

---

## ⚙️ Nützliche Befehle

```bash
docker compose logs -f                 # Logs anzeigen
docker compose down                    # Bridge stoppen
docker compose pull && docker compose up -d   # auf neueste veröffentlichte Version updaten
docker compose up -d --build           # lokal selber bauen (statt zu pullen)
```

### 🌙 Nightly-Builds

Nightly-Builds enthalten die neuesten unveröffentlichten Funktionen und werden bei jedem Entwicklungs-Commit gebaut.
Sie können instabil sein — für Tests oder frühzeitigen Zugang zu neuen Features geeignet.

```bash
docker compose -f docker-compose.yml -f docker-compose.nightly.yml pull
docker compose -f docker-compose.yml -f docker-compose.nightly.yml up -d
```

Zurück zum stabilen Release:

```bash
docker compose pull && docker compose up -d
```

---

## 🩹 Troubleshooting

<details>
<summary><b>"Falsche MQTT-Zugangsdaten" beim Start</b></summary>

- Drucker über *„+ Drucker hinzufügen"* erneut hinzufügen, oder
  `fetch_credentials --ip <ip> --write-config` ausführen und Bridge neu starten
- Nur die IP-Adresse eingeben, ohne Port (✗ `192.168.1.102:9883` → ✓ `192.168.1.102`)
</details>

<details>
<summary><b>Drucker nicht gefunden / kein LAN-Modus</b></summary>

- Am Drucker-Display: Einstellungen → LAN-Modus aktivieren
- Drucker und Bridge müssen im selben Netzwerk sein
</details>

<details>
<summary><b>Docker: Permission denied</b></summary>

```bash
sudo usermod -aG docker $USER   # danach aus- und wieder einloggen
```
</details>

<details>
<summary><b>Upgrade von 0.9.1 oder älter</b></summary>

Ab 0.9.2 speichert KX-Bridge die Einstellungen in `config/config.ini` statt `.env`.
Die Migration läuft automatisch beim ersten Start nach dem Upgrade — keine Aktion nötig.
</details>

---

## 🔒 Sicherheit

- Die Bridge ist im lokalen Netzwerk unter `http://<host-IP>:7125` erreichbar — **nicht** ins Internet exposen
- `config/config.ini` enthält Drucker-Zugangsdaten — nicht öffentlich teilen
- Die Zugangsdaten geben **keinen** Zugriff auf Anycubic-Cloud-Dienste

---

## 📄 Lizenz

[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg)](LICENSE)

KX-Bridge steht unter der **GNU General Public License v3.0** ([LICENSE](LICENSE)).
Forks und Erweiterungen müssen bei Weitergabe ebenfalls unter GPLv3 stehen.

Die MQTT-Protokoll-Implementierung ist das Ergebnis unabhängiger
Reverse-Engineering-Arbeit zur Herstellung der Interoperabilität (§69e UrhG /
EU-Softwarerichtlinie Art. 6). Drittmaterial im Repository (Anycubic-
TLS-Zertifikate) fällt **nicht** unter die GPLv3 und ist ausschließlich
enthalten, um die Authentifizierung am eigenen Drucker zu ermöglichen.
Details + Disclaimer in [NOTICE.md](NOTICE.md).

Dieses Projekt ist unabhängig und steht in keinem Zusammenhang mit Anycubic.

<div align="center">
<br>

**Wenn dir KX-Bridge hilft, freut sich das Projekt über Unterstützung:**

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/viewitde)

</div>
