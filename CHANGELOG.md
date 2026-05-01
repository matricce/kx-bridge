# Changelog

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
