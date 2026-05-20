# Changelog

## [0.9.12] – 2026-05-20

### Fixes
- **Pause state** is now read correctly: the bridge was looking at the device-level
  state instead of the nested print-job state, so a paused print sometimes still
  showed as printing. Layer/progress/remaining-time are now also taken from the
  job report.

### Internal
- Frontend (HTML/CSS/JS) extracted from the Python file into `web/index.html`,
  bundled back in at build time — easier to maintain, no change for users.

### Docs
- Linked the community **Home Assistant integration** by @gangoke.

## [0.9.11] – 2026-05-20

### New
- **ACE Pro 2 support (experimental, community contribution by @gangoke, PR #26):** the bridge now auto-detects the filament hardware and adapts:
  - **Modes:** `toolhead` (no ACE, stock 4-slot box), `ace_direct` (one ACE Pro 2 directly on the toolhead), `ace_hub` (up to 4 ACE units on the slot-4 hub) — up to **19 slots** total.
  - **AMS auto-refill** toggle.
  - **Dryer:** temperature/humidity monitor, start/stop/temp/duration control, with material presets configurable in a new `[ace_dry_presets]` config section (PLA, PLA+, PETG, TPU, ABS/ASA, PA/PC + 3 custom).
  - **UI:** filament section scales to 19 slots, mode label, loaded slot is green-outlined with a load/unload pulse animation, unload/load straight from the slot-edit dialog.
  - **GCode color mapping:** ACE2-aware, color-from-GCode fix, inconsistency notifier when the mapping doesn't match the objects, better default mapping.

> **⚠️ Experimental:** the ACE Pro 2 hardware paths were developed and tested by the contributor with a single ACE2 unit; the 2–4 unit hub configurations are theoretical and untested on real hardware. We don't have ACE2 hardware to verify against either. The standard `toolhead` (no-ACE) path was verified live against a real Kobra X here. If you run a multi-ACE setup, please report back via Issues.

### Fixes
- **Happy Hare MMU emulation:** only populated slots are now synced — no placeholder for empty slots (aligns with OrcaSlicer PR #13372).
- **GCode color dialog** no longer shows the previously-uploaded file's data after a new upload.

---

## [0.9.10] – 2026-05-17

> **Heads-up:** with this release the focus shifts from new features to
> **stabilization and bug-fixing**. The core flows (multi-printer, add/remove,
> filament dialog, skip objects, standalone binaries) are feature-complete
> enough — from now on the priority is making them rock-solid before adding
> more on top. Bigger feature requests (ACE Pro 2, Home Assistant integration
> completeness, …) stay on the backlog for now.

### New
- **Skip objects (pre-print and mid-print):** Reverse-engineered from the AnycubicSlicerNext Workbench bundle — the Kobra X actually supports object skipping over its native protocol, but the Anycubic slicer doesn't expose it. The bridge does now, in both flavors:
  - **Pre-print:** when starting a multi-object print from the Browser tab, the filament dialog now has an additional "Objects" section. Uncheck individual objects (or click the polygon directly on the build-plate SVG preview) and they're stripped from the print before it starts.
  - **Mid-print:** new ✂ button on the dashboard (only visible during an active print). Opens a dialog with the same interactive SVG preview — click a part to mark it for skipping, hit confirm, and the printer drops it from the rest of the run. Already-skipped parts stay greyed out and the dialog refreshes live so you can see which ones are gone.
- **Filament dialog – colored channel and slot markers (Issue #23):** the GCode channel number now sits in a colored box on the left (background = channel color, auto-contrast text instead of the old tiny dot), and the assigned AMS slot gets the same treatment on the right of the dropdown — updates live as you change the selection. Plays well with 4 channels; the layout iterates so more channels render correctly, but >4 actual filament slots still need an ACE Pro 2 hub to be testable end-to-end (parked as a feature request, Issues #22 and #23).

### Internal
- New `kobrax_client.skip_objects(names)` / `query_skip_objects()` helpers.
- New endpoints: `GET /kx/files/{id}/objects`, `POST /kx/skip`, `POST /kx/skip/query`, `GET /kx/skip/state`.
- SQLite schema: `gcode_files` gained `objects_skip_parts` and `svg_image` columns (auto-migrates on existing DBs).
- `_on_file` now extracts the printer-provided object list + SVG preview and persists them per file.
- `_on_skip` callback tracks which objects the printer reports as currently skipped.

---

## [0.9.9] – 2026-05-14

### Fixes
- **"Failed to fetch" loop in the UI (Issue #21):** When the web UI was opened via the LAN IP, `/kx/printers` was returning `bridge_url: http://localhost:7125`, which caused the browser to fire cross-origin requests from the LAN IP to `localhost` — these were silently blocked, producing a flood of `TypeError: Failed to fetch` poll errors. The bridge now sends an empty `bridge_url` in single-printer mode so the frontend uses relative paths against the same origin as the UI. In multi-printer mode, `localhost`/`127.0.0.1` are filtered out as bridge hosts.
- **Windows EXE startup crash (Issue #21):** The v0.9.8 `kx-bridge.exe` was built with a stale `config_loader.py` from an earlier release and crashed on startup with `AttributeError: module 'config_loader' has no attribute 'list_printers'`. `release.sh` now syncs `config_loader.py` into the Windows build repository together with the other source files.

---

## [0.9.8] – 2026-05-12

### New
- **Multi-printer in a single bridge instance:** One process now manages multiple printers — N MQTT connections + N HTTP listeners (ports 7125, 7126, …), shared SQLite + GCode store. Configure via `[printer_1]`, `[printer_2]` … sections in `config.ini`. Single-printer mode (`[connection]` only) keeps working unchanged. `docker-compose.yml` exposes a port range `7125-7130`.
- **Add printer from the UI:** "+ Add printer" button in the Printers tab — just enter the printer IP, the credentials (username, password, device ID) are fetched and decrypted from the printer automatically. Adding more printers assigns the next free port (7126, 7127, …).
- **Remove printer from the UI:** "✕" button on each printer card with a confirmation dialog — removes the `[printer_N]` section and renumbers the rest. Removing the last printer clears `[connection]` too, leaving an empty state.
- **GCode Store:** Uploaded files are persisted in SQLite with thumbnail extraction. New `/kx/files` API.
- **Browser tab:** Grid view of all uploaded files — thumbnail, status badge (✓/✗), last print duration, plus search, filter and sort.
- **Print history:** Print jobs (start/end/status) are recorded in SQLite, status shown per file in the Browser tab.
- **Filament dialog:** Per-channel remapping before print start — assign each GCode color channel to a physical AMS slot (like the Anycubic Slicer does). Available in the Browser tab and the upload banner.
- **MMU emulation:** `GET /printer/objects/query?mmu` returns a Happy-Hare-compatible structure so OrcaSlicer's filament sync detects the AMS slots.
- **Printers tab:** Live status of all printer instances, IP shown on each card, "Switch →" button.
- **Editable printer name:** Set a custom name in Settings (stored in `[bridge] printer_name`, takes precedence over the MQTT-reported name).
- **Standalone friendly:** Linux binary / Windows EXE run without Docker — `config/` and `data/` are placed next to the executable (portable). First start with no printer configured shows the Printers tab with "+ Add printer" instead of the settings modal.
- **i18n:** All new UI elements available in German and English.

### Fixes
- **CORS:** CORS middleware added to all endpoints — cross-instance fetches in the multi-printer UI work reliably.
- **Settings / update check** now reflect the active bridge instance in multi-printer mode (via `_apiUrl`).
- **Bridge restart:** Config-dependent environment variables are cleared before a restart (the config loader cached them, which made config changes invisible until the next cold start). Restart is now platform-aware: Docker/systemd → process exit (supervisor restarts), Linux standalone → `os.execv`, Windows → detached subprocess.
- **`--data-dir` default** is now platform-dependent — the `/app/data` default only applies inside Docker (set via `ENV`), standalone binaries use `<exe-dir>/data`. Fixes a startup crash when running the binary without Docker.

---

## [0.9.7] – 2026-05-08

### New
- **fetch_credentials tool:** Fetches and decrypts MQTT credentials directly from the printer via HTTP — no running Anycubic Slicer required, only the printer IP needed. Linux binary and Windows EXE included in release. (Contributed by bebu, PR #19)

### Fixes
- **Large GCode upload:** Files >1 MB were rejected with HTTP 413 — aiohttp `client_max_size` raised to 256 MB
- **Upload timeout:** Socket timeout after GCode upload raised from 10s to 120s — large files caused the bridge to crash with an empty response while the printer was still processing

---

## [0.9.6] – 2026-05-02

### New
- **Light status sync:** Light on/off state and brightness are now read live from the printer via `light/report` MQTT message — the light toggle in the UI reflects the actual printer state
- **Time mini-cards:** Progress panel now shows three cards — Elapsed, Remaining and Slicer estimate — with a layer counter badge next to the progress bar
- **Slicer estimate from GCode:** Estimated print time is parsed directly from the uploaded GCode file (OrcaSlicer: `; total estimated time:` at end of file, PrusaSlicer: `; estimated printing time` in header)
- **Extended printer status strings:** Added `pausing`, `paused`, `resuming`, `resumed`, `stopping`, `stopped` states — previously missing, causing the UI to show raw status codes during pause/resume/stop transitions

### Fixes
- **file_ready banner:** Upload banner is no longer shown after print stop or cancel
- **Timers on stop/cancel:** Elapsed, remaining and slicer estimate times are reset to zero when a print is stopped or cancelled
- **start.sh:** `config/` directory and `config.ini.example` are now created automatically on first run if missing (Issue #15)

---

## [0.9.5] – 2026-05-01

### New
- **Upload banner:** After "Upload only", a green banner appears with the filename — "▶ Start Print" starts the print directly, "✕ Cancel" dismisses the banner

### Fixes
- **Auto-print:** `auto_print` was always reset to `False` after the multipart loop — OrcaSlicer "Upload and print" never started the print automatically
- **Thumbnail:** Preview image is now shown after "Upload only" — bridge requests `fileDetails` immediately after upload
- **Log auto-scroll:** Scroll position is preserved when auto-scroll is disabled — no more unwanted jump to top

---

## [0.9.4] – 2026-05-01

### New
- **AMS slot editor:** Click any slot in the AMS panel to open an edit dialog — set color (color picker) and material (preset buttons: PLA/PETG/ABS/ASA/TPU/PA/PC/HIPS or free text) directly from the browser
- **Improved log panel:** Full MQTT payloads (no truncation), direction filter (All/RX/TX) and topic quick-filter buttons (AMS / print / info / status)

### Fixes
- **i18n:** Camera placeholder text and log direction "All" button now correctly translated on language switch

---

## [0.9.3] – 2026-05-01

### Fixes
- **Update check:** Stable users no longer receive dev pre-releases — `STABLE_RELEASE_API` had `pre-release=true` which caused stable installs to find dev builds instead of stable releases (Issue #14)
- **Version after update:** `VERSION` file is now included in the Docker image (`COPY VERSION .`) — `_write_version()` requires the file to exist, without it the version was never updated after self-update (Issue #14)

### New
- **Version in header:** Running version shown in the Web-UI header next to the printer name — no need to open Settings to check (Issue #14)

---

## [0.9.2] – 2026-04-29

### ⚠️ Breaking Change: Configuration moves from `.env` to `config/config.ini`

**Migration is automatic** on first start — no manual action required.

- Settings are now read from `config/config.ini` instead of `.env`
- On first start without `config.ini`, the file is created automatically from `.env`
- **Docker:** Volume `./config:/app/config` in `docker-compose.yml` is the persistent storage — settings survive `docker-compose restart` and updates
- **Standalone:** `config/config.ini` sits next to the binary and is not overwritten on update
- `.env` stays mounted read-only as a migration source — you can leave it in place
- To create a `config.ini` manually: copy `config/config.ini.example`

### New
- **Persistent settings:** `config/config.ini` replaces `.env` — settings no longer lost after `docker-compose restart` (Issue #9)
- **Connection error banner:** Red banner at the top of the Web-UI when MQTT connection fails (e.g. wrong password, printer unreachable) (Issue #11)
- **Slicer estimated time:** Estimated total print time from GCode header shown in the progress panel

### Fixes
- README: OrcaSlicer connection documented explicitly with `http://` and port `:7125` (Issue #12)
- README: Direct download link for `extract_credentials` pointing to Gitea releases (Issue #13)

---

## [0.9.1-dev] – ongoing (dev branch)

### New
- **Dev branch infrastructure:** Version scheme `0.9.1-dev+<hash>` — every build uniquely identifiable
- **Separate update channel:** Dev versions check for Gitea pre-releases with `-dev+` in the tag
- **AMS slot selection:** Setting "Default slot (single color)" in the Settings modal — pins a specific AMS channel or Auto (all loaded slots)
- **Auto-leveling:** Checkbox in Settings modal — controls `task_settings.auto_leveling` on print start
- **MQTT logging:** Structured TX/RX log with duplicate filter (`kobrax.mqtt` logger)
- **Server log in browser console:** Live stream via SSE (`/api/log/stream`) — all server logs appear in the Log tab
- **Log tab improvements:**
  - Auto-scroll on/off — disables automatically on manual scroll-up, button to re-enable
  - Text filter — live filtering of log entries
  - Error badge — red counter on the tab button when errors/warnings occur while on another tab
  - Clear button — empty the buffer
  - Download button — last 500 entries as `kx-bridge.log`
  - Log window now fills all available space (instead of fixed 160px height)
- **Log buffer:** 500 entries (server + browser unified)
- **Changelog in update dialog:** Release notes from Gitea loaded and shown directly in the update dialog
- **Slicer estimated time:** Estimated total print time from GCode header shown in the progress panel

---

## [0.9.1-beta15] – 2026-04-26

### Fixes
- AMS: Empty slots are skipped on print start — no more `filament runout` for unloaded channels (Issue #5)
- AMS: Material type is now correctly read from the printer protocol (field `type` instead of `material_type`)
- AMS UI: Empty slots shown grey/transparent with "Empty" label

---

## [0.9.1-beta14] – 2026-04-26

### Fixes
- Z axis: ▲ now moves up (Z+), ▼ moves down (Z−) — arrows were reversed (Issue #4)
- Home All: correct axis code 5 — homes all axes XYZ (Issue #4)
- New "Home XY" button (axis=4) in the UI
- New "Motors Off" button (axis turnOff) in the UI

---

## [0.9.1-beta13] – 2026-04-26

### Fixes (Windows)
- Self-update / Settings restart: `os.execv` now works correctly in PyInstaller binary
- Camera: `ffmpeg not found` no longer crashes — clean 503 response when ffmpeg is not installed
- Reconnect loop: Short empty TCP reads on Windows no longer trigger immediate reconnects

### Structure
- `bridge/`: Bridge files extracted from `05_scripts/`
- `tools/`: `extract_credentials.py` as standalone tool with its own README
- `_archive/`: RE research folders, analysis tools and old release checksums archived
- README fully rewritten: clear 3-step quick start

---

## [0.9.1-beta12] – 2026-04-25

### Fixes
- Wrong MQTT credentials now shows a human-readable error instead of cryptic `CONNACK failed: 20020005`

---

## [0.9.1-beta11] – 2026-04-25

### Fixes
- Printer IP is automatically cleaned if the user accidentally includes the port (e.g. `192.168.1.102:9883` → `192.168.1.102`)
- Settings modal: hint shown when `:` is detected in the IP field
- `docker-compose.yml`: `.env` mounted as volume into the container — settings persist after `docker-compose restart`

---

## [0.9.1-beta10] – 2026-04-25

### New
- `start.sh` — starts the bridge via Docker, builds the image automatically on first run
- Tests: pytest suite (19 tests) for API state, Moonraker endpoints, settings; install smoke test (`test_install.sh`)
- Settings modal opens automatically on first start when no credentials are configured

### Changed
- README: Quick start now shows `./start.sh` instead of manual `docker build`
- README: LAN mode correctly described as a printer menu option
- README: Version number now updated automatically on each release
- `extract_credentials`: `--write-env` no longer recommended — enter values in the ⚙ menu
- Dockerfile in release repo: paths without `05_scripts/` prefix
- `release.sh`: Dockerfile for release repo automatically patched via `sed`

### Fixes
- Remaining print time (`remain_time`) now correctly taken from `print/report` and shown in UI
- Translation: "Step size" and "Target" placeholders in temperature inputs now correctly translated

---

## [0.9.1-beta9] – 2026-04-25

### New
- OrcaSlicer profile (`kobra_x_orcaslicer_preset.zip`) as release asset
- `release.sh`: OrcaSlicer profile automatically copied to release repo and uploaded

### Changed
- README: `extract_credentials` without `--write-env`, values entered manually in the ⚙ menu
- README: Docker quick start simplified

---

## [0.9.1-beta8] – 2026-04-25

### New
- Remaining print time display in UI (≈ Xh Ym remaining) from `remain_time` field
- Settings modal: connection settings and self-update directly in the browser
- Self-update: bridge checks Gitea release API for new versions and updates itself

### Changed
- Bridge starts in offline mode when printer is unreachable (no crash)
- Connect/Disconnect button in header

---

## [0.9.1-beta7] – 2026-04-22

### New
- Offline start: bridge runs without MQTT connection, reconnects automatically when printer is reachable
- Connect/Disconnect button in header

---

## [0.9.1-beta6] – 2026-04-20

### New
- Release ZIPs: `kx-bridge-linux.zip`, `kx-bridge-windows.zip`, `anycubic-certs.zip` with certificates

### Fixes
- PyInstaller frozen binary: `__file__` replaced with `sys.executable` path (cert path fix)

---

## [0.9.1-beta5] – 2026-04-19

### New
- `kx-bridge.exe` (Windows) built automatically via GitHub Actions

---

## [0.9.1-beta4] – 2026-04-18

### New
- `release.sh`: builds Linux binary and Windows EXE, uploads all assets to Gitea
- English README (`README.en.md`)

### Fixes
- `progress` and `filename` correctly reset to 0 on `stoped`/`canceled`

---

## [0.9.1-beta3] – 2026-04-17

### New
- Print speed card (Silent / Normal / Sport)
- Translations (DE/EN) completed

---

## [0.9.1-beta2] – 2026-04-17

### Fixes
- Temperature control during an active print

---

## [0.9.1-beta1] – 2026-04-17

### New
- Complete UI overhaul: Settings modal, self-update, dashboard, responsive design
- New printer states: `pausing`, `paused`, `resuming`, `resumed`, `stopping`
- `release.sh`: version bump and release sync script

---

## [0.9.0-beta1] – 2026-04-10

### New
- First public release
- Docker deployment, Linux binary, `extract_credentials` tool
- Moonraker-compatible HTTP/WebSocket bridge for the Anycubic Kobra X
- AMS load/unload, light and fan control
- Web-UI with dashboard, temperature cards, motion control
