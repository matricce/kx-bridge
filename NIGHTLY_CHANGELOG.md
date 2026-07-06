## Changes in this build

- Refactor: all logs, comments and API error strings translated to English across the codebase (no behavior change)
- Refactor: the `print/start` payload was duplicated in three places and had drifted (the new resonance-compensation setting was missing from the upload+print path) — all print start paths now share one payload builder
- Fix: a couple of silently swallowed errors (dashboard reprint filament-cache load, filament metadata backfill) now log a warning/debug message instead of failing silently

**A stable release is coming soon** with the fixes and features from the last several nightly builds. As usual it will be published as ready-to-run binaries (Linux amd64/arm64, Windows) alongside the Docker image.
