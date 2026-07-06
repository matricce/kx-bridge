## Changes in this build

- Fix: Dashboard reprint no longer targets wrong/empty slot after a spool is removed between prints — slot mapping now uses cached GCode filament data to apply the same used-paint-index filter as a regular upload+print (Issue #84)
- Fix: Startup log no longer shows `0.0.0.0` as the bridge address — the actual LAN IP is now displayed, matching what OrcaSlicer needs (Issue #86)
- Feat: New "Resonance Compensation" toggle in Settings — when enabled, `vibration_compensation` is activated before each print, compensating for mass shifts as the spool empties (Issue #85)

- Fix: Spoolman spool-slot assignment persistence was silently broken (NameError on config_loader swallowed by bare except) — now uses correct module reference and logs failures; per-printer isolation added so multi-printer setups no longer overwrite each other (Issue #80, PR #83 by @walterioo)
- Fix: spool dropdown in print dialog showed "[object Object]" instead of vendor name (PR #83)
- Fix: gate_spool_id in MMU object now populated from per-printer slot map instead of hardcoded -1 (PR #83)
- Fix: PLA variants (PLA+, PLA Silk, PLA Matte) now recognized as their material family — correct tray_info_idx sent to printer, correct Generic profile synced to OrcaSlicer, and vendor profiles for the variant shown in slot editor dropdown (Issue #82)
- UI: PLA+, PLA Silk and PLA Matte buttons added to slot material selector
