<div align="center">

<img src="knlogo.png" alt="KX-Bridge" width="160"/>

# KX-Bridge

**Control your Anycubic Kobra X with OrcaSlicer — no Klipper, no Raspberry Pi.**

A Moonraker-compatible bridge that talks directly to the printer.

<sub>🇩🇪 <a href="README.de.md">Deutsche Version</a></sub>

<br>

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20this%20project-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/viewitde)
&nbsp;
[![Releases](https://img.shields.io/badge/Download-Releases-2EA043?style=for-the-badge&logo=gitea&logoColor=white)](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)
&nbsp;
[![Downloads](https://img.shields.io/badge/Downloads-800%2B-8957E5?style=for-the-badge&logo=gitea&logoColor=white)](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases)
&nbsp;
[![Video](https://img.shields.io/badge/YouTube-Tutorial-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=1Ql4wfH27fM)

<sub>Like KX-Bridge? A coffee on <a href="https://ko-fi.com/viewitde">Ko-fi</a> keeps the project alive. ☕</sub>

</div>

---

## ✨ Features

| | |
|---|---|
| 🖨️ | **Printer control** — start, pause, resume, cancel, temperatures, print speed |
| 📊 | **Live status** — temperature, progress, layers, remaining time, camera stream |
| 🎨 | **AMS / multicolor** — filament slots, per-channel remapping, MMU emulation for OrcaSlicer filament sync |
| 🗂️ | **GCode browser** — uploaded files with thumbnails, print history, search & filter |
| 🧩 | **Multi-printer** — multiple printers in **one** bridge instance, switch via dropdown |
| ➕ | **Add a printer with one click** — just enter the IP, credentials are imported automatically |
| 🔄 | **Self-update** — install new versions directly in the browser |
| 🌐 | **OrcaSlicer** — full Moonraker protocol (HTTP + WebSocket), EN/DE UI |

---

## 🚀 Quick Start

### 1. Prepare the printer

Enable LAN mode on the Kobra X:
**Printer display → Settings → Enable LAN mode**

### 2. Start the bridge

**Docker (recommended):**
```bash
docker compose up -d
```

**Linux binary (no Docker):**
```bash
chmod +x kx-bridge && ./kx-bridge
```

**Windows EXE (no Docker):**
```
kx-bridge.exe
```
> `config\` and `data\` are created next to the EXE — portable.

> With the Linux and Windows binaries, `config/` and `data/` (settings, SQLite, GCode store)
> live next to the program. Copy the whole folder = move the installation.

**Python directly:**
```bash
pip install -r bridge/requirements.txt
python bridge/kobrax_moonraker_bridge.py
```

### 3. Set up the printer

Open the Web UI: **`http://BRIDGE-IP:7125`**

On first start the **Printers tab** shows *"+ Add printer"* — just enter the printer's IP
address, the rest (username, password, device ID) is fetched from the printer and decrypted
automatically. Done.

> More than one printer? Just click *"+ Add printer"* again — each gets its own port
> (7125, 7126, …) and is selectable from the header dropdown.

### 4. Connect OrcaSlicer

Printer → Connection type **Moonraker** → Host: `http://BRIDGE-IP:7125`

> ⚠️ Connection type must be **Moonraker** (not "Bambu" or "Klipper").
> Enter the full URL including `http://` and port `:7125` in the host field.

---

## 📺 Video Tutorial

[![KX-Bridge Setup & Usage](https://img.youtube.com/vi/1Ql4wfH27fM/hqdefault.jpg)](https://www.youtube.com/watch?v=1Ql4wfH27fM)

---

## 🎨 Recommended Slicer

For the best KX-Bridge experience we offer a **patched OrcaSlicer build** that
bundles three open SoftFever/OrcaSlicer PRs: the Anycubic Kobra X printer
profile, a multicolor G-code fix and — most importantly — a Moonraker/Happy-Hare
filament-sync fix that keeps AMS slot positions intact even with an empty slot.

→ **[OrcaSlicer-KX releases](https://gitea.it-drui.de/viewit/OrcaSlicer-KX/releases/latest)** (Linux AppImage + Windows ZIP)

Standard OrcaSlicer also works; the patched build mainly improves AMS handling.
It's a build of [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) (AGPL-3.0);
source is available via the linked PRs.

---

## 🏠 Community & Integrations

- **[Home Assistant integration](https://github.com/gangoke/kobrax-lan-hass-component)**
  by [@gangoke](https://github.com/gangoke) — exposes sensors, print controls,
  light, camera and the GCode thumbnail as native Home Assistant entities.

> These are **community projects**, not maintained or supported by KX-Bridge.
> For questions or issues, please use the linked repository.

---

## 🔧 Getting credentials manually

Normally not needed — *"+ Add printer"* does this automatically. If you do need it:

```bash
fetch_credentials --ip 192.168.x.x --write-config
```
Fetches the credentials directly from the printer via HTTP and writes them to `config/config.ini`.
Only the printer IP is required, no slicer.

Alternatively (if the IP is unknown): open AnycubicSlicerNext, connect the printer, then run
`extract_credentials` → outputs username, password, device ID and the printer IP.

> **Downloads:** [Releases](https://gitea.it-drui.de/viewit/KX-Bridge-Release/releases) → `fetch_credentials` / `extract_credentials` (Linux & Windows)

---

## ⚙️ Useful commands

```bash
docker compose logs -f       # show logs
docker compose down          # stop the bridge
docker compose up -d --build # rebuild & start (after an update)
```

---

## 🩹 Troubleshooting

<details>
<summary><b>"Wrong MQTT credentials" on start</b></summary>

- Re-add the printer via *"+ Add printer"*, or run
  `fetch_credentials --ip <ip> --write-config` and restart the bridge
- Enter only the IP address, no port (✗ `192.168.1.102:9883` → ✓ `192.168.1.102`)
</details>

<details>
<summary><b>Printer not found / no LAN mode</b></summary>

- On the printer display: Settings → Enable LAN mode
- Printer and bridge must be on the same network
</details>

<details>
<summary><b>Docker: Permission denied</b></summary>

```bash
sudo usermod -aG docker $USER   # then log out and back in
```
</details>

<details>
<summary><b>Upgrading from 0.9.1 or earlier</b></summary>

Starting with 0.9.2, KX-Bridge stores settings in `config/config.ini` instead of `.env`.
Migration runs automatically on first start after the upgrade — no action required.
</details>

---

## 🔒 Security

- The bridge is reachable on the local network at `http://<host-IP>:7125` — **do not** expose it to the internet
- `config/config.ini` contains printer credentials — do not share publicly
- The credentials do **not** grant access to Anycubic cloud services

---

## 📄 License

[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg)](LICENSE)

KX-Bridge is released under the **GNU General Public License v3.0**. See
[LICENSE](LICENSE) for the full text. Forks and modifications must remain
under GPLv3 if redistributed.

The MQTT protocol implementation is the result of independent
reverse-engineering for interoperability purposes (§69e UrhG / EU Software
Directive Art. 6). Third-party material in the repository (Anycubic TLS
certificates) is **not** covered by GPLv3 and is included solely to enable
authentication against printers the end-user already owns. See
[NOTICE.md](NOTICE.md) for details and disclaimer.

This project is independent and not affiliated with Anycubic.

<div align="center">
<br>

**If KX-Bridge helps you, the project appreciates your support:**

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/viewitde)

</div>
