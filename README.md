<div align="center">

<img src="knlogo.png" alt="KX-Bridge" width="160"/>

# KX-Bridge

**Control your Anycubic Kobra X with OrcaSlicer — no Klipper, no Raspberry Pi.**

A Moonraker-compatible bridge that talks directly to the printer.

<sub>🧪 A community report on Reddit suggests the bridge also works with the
**Kobra S1** and **Kobra S1 Max** — protocols look compatible, but neither is
officially tested or supported. Feedback welcome.</sub>

<sub>🇩🇪 <a href="README.de.md">Deutsche Version</a>  ·  🇪🇸 <a href="README.es.md">Versión española</a></sub>

</div>

> [!CAUTION]
> **Ongoing maintenance work this week** — We are restructuring the repository (branch model, CI workflows, contribution process). You may notice changes to branch names, PR templates, and how releases are published. We apologise for any inconvenience. Handling, workflow, and long-term maintainability will be significantly improved as a result.
>
> 👉 Want to contribute? Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

<div align="center">

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
| 🎨 | **AMS / multicolor** — slots with per-slot **profile picker** (assign your own brand from OrcaSlicer profiles per slot); bridge writes material & colour back to the printer display |
| 📦 | **Import your own OrcaSlicer profiles** — drag a ZIP from `~/.config/OrcaSlicer/user/<id>/filament/` into the bridge; they show up in the slot dropdown under ★ Own profiles |
| 📷 | **Obico integration (experimental)** — Time-Lapse and WebRTC live stream against a self-hosted [Obico server](https://github.com/TheSpaghettiDetective/obico-server) via moonraker-obico |
| 📐 | **Direct H.264 stream + Z-height** — low-CPU camera path for Obico, current Z derived from layer-height for the print-progress widget |
| 🗂️ | **GCode browser** — uploaded files with thumbnails, print history, search & filter |
| 🧩 | **Multi-printer** — multiple printers in **one** bridge instance, switch via dropdown |
| ➕ | **Add a printer with one click** — just enter the IP, credentials are imported automatically |
| 🔁 | **Robust MQTT reconnect** — bridge survives overnight printer reboots without manual restart |
| 🌐 | **Multi-language UI** — DE / EN / ES / 中文, auto-detect browser locale |
| 🔄 | **Self-update** — install new versions directly in the browser |
| 🧠 | **OrcaSlicer** — full Moonraker protocol (HTTP + WebSocket); pair with the [OrcaSlicer-KX build](#-recommended-slicer) for proper per-slot vendor matching |

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



## 🎨 Recommended Slicer

For proper AMS filament-sync we ship a **patched OrcaSlicer build**:

→ **[OrcaSlicer-KX releases](https://gitea.it-drui.de/viewit/OrcaSlicer-KX/releases/latest)** (Linux AppImage + Windows ZIP)

**Upstream PRs bundled in the KX build:**

- **[PR #13372](https://github.com/SoftFever/OrcaSlicer/pull/13372)** — Moonraker / Happy-Hare AMS sync fix (slot positions stay correct even with empty slots)
- **[PR #13719](https://github.com/SoftFever/OrcaSlicer/pull/13719)** — Vendor + Name matching for Moonraker (reads `name` + `vendor_name` per slot and matches against the user's filament presets), by [@LordGuenni](https://github.com/LordGuenni)
- **[PR #13315](https://github.com/SoftFever/OrcaSlicer/pull/13315)** — Unique `filament_id` for user presets (so newly created custom profiles get a fresh ID instead of inheriting `OGFL99` from the generic parent), by [@mrnoisytiger](https://github.com/mrnoisytiger)

**Plus four KX-specific matching improvements on top:**

- Respect the bridge filament hint (`tray_info_idx` + vendor)
- Vendor match also when the chosen base preset is **not is_compatible** with the active printer (so a profile copied from a different machine still matches by vendor)
- Vendor match when `tray_info_idx` is set but its preset is incompatible
- Two-pass lookup: first compatible presets, then all visible ones

**Why this matters:** without #13719 the AMS slots in OrcaSlicer all fall back to `Generic PLA` / `Generic PETG` even though the bridge already sends the concrete brand (`name + vendor_name + gate_filament_name`). With the KX build OrcaSlicer matches your actual user presets — including profiles you imported into the bridge via the [Import your own OrcaSlicer profiles](#-features) flow.

Stock upstream OrcaSlicer still works for slicing and printing — you just lose the per-slot brand matching on AMS sync. Slot material + colour can still be pushed bridge → printer either way (that goes over MQTT, not via the slicer).

OrcaSlicer-KX is a build of [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) (AGPL-3.0); source for each upstream PR is on GitHub, KX-specific patches live in the OrcaSlicer-KX repo.

---

## 🏠 Community & Integrations

- **[Home Assistant integration](https://github.com/gangoke/kobrax-lan-hass-component)**
  by [@gangoke](https://github.com/gangoke) — exposes sensors, print controls,
  light, camera and the GCode thumbnail as native Home Assistant entities.
- **[Obico (self-hosted)](https://github.com/TheSpaghettiDetective/obico-server)** —
  the bridge exposes a Moonraker-compatible surface that
  [moonraker-obico](https://github.com/TheSpaghettiDetective/moonraker-obico)
  accepts, so you get Time-Lapse and WebRTC live streaming against your own
  Obico server. The AI failure-detection side is experimental on the Kobra X
  (top-down camera angle differs from what the model was trained on).

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
docker compose logs -f                 # show logs
docker compose down                    # stop the bridge
docker compose pull && docker compose up -d   # update to the latest published image
docker compose up -d --build           # rebuild locally (instead of pulling)
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
