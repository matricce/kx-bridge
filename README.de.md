<div align="center">

<img src="knlogo.png" alt="KX-Bridge" width="160"/>

# KX-Bridge

**Steuere deinen Anycubic Kobra X mit OrcaSlicer — ohne Klipper, ohne Raspberry Pi.**

Eine Moonraker-kompatible Bridge, die direkt mit dem Drucker spricht.

<br>

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20this%20project-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/viewitde)
&nbsp;
[![Releases](https://img.shields.io/badge/Download-Releases-2EA043?style=for-the-badge&logo=gitea&logoColor=white)](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)
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
| 🎨 | **AMS / Multicolor** — Filament-Slots, Per-Kanal-Remapping, MMU-Emulation für OrcaSlicer Filament-Sync |
| 🗂️ | **GCode-Browser** — hochgeladene Dateien mit Thumbnail, Druckhistorie, Suche & Filter |
| 🧩 | **Multi-Printer** — mehrere Drucker in **einer** Bridge-Instanz, Umschalten per Dropdown |
| ➕ | **Drucker hinzufügen per Klick** — nur die IP eingeben, Zugangsdaten werden automatisch importiert |
| 🔄 | **Self-Update** — neue Versionen direkt im Browser installieren |
| 🌐 | **OrcaSlicer** — volles Moonraker-Protokoll (HTTP + WebSocket), DE/EN UI |

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
docker compose logs -f      # Logs anzeigen
docker compose down         # Bridge stoppen
docker compose up -d --build # Bridge neu bauen & starten (nach Update)
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

Interoperabilitätsforschung gem. §69e UrhG — private, nicht-kommerzielle Nutzung.

<div align="center">
<br>

**Wenn dir KX-Bridge hilft, freut sich das Projekt über Unterstützung:**

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/viewitde)

</div>