## Changes in this build

- Fix: the poll interval setting was saved to config.ini but never actually applied — the poll loop always used a hardcoded 3s wait
- Fix: Spoolman status showed a green "connected" dot even when the server was unreachable — reachability is now rechecked periodically and shown accurately (green/red)
- Fix: **settings could silently revert after saving** — the bridge restart that applies settings didn't clean up all the relevant environment variables, so the old value could win over the one just saved (affected poll interval, resonance compensation, Docker host IP, and the new HTTP log toggle below). Fixed at the root so this class of bug can't recur for future settings.
- Feat: new "Log every HTTP request (verbose)" toggle in Settings — off by default, since aiohttp's per-request access log was drowning out the bridge's own logs with the frontend's 2s polling

**A stable release is coming soon** with the fixes and features from the last several nightly builds. As usual it will be published as ready-to-run binaries (Linux amd64/arm64, Windows) alongside the Docker image.
