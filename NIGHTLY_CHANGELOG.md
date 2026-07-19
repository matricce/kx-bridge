## Changes in this build

- Fix: on printers with multiple daisy-chained ACE units and no toolhead buffer (e.g. Kobra S1 with 2 ACE Pro), only the first unit's 4 slots were ever shown on the dashboard or synced to OrcaSlicer — the bridge silently discarded every ACE unit after the first. All units now show up correctly (Issue #95, thanks @hoovercl for the detailed report and logs)
- Feat: the GCode browser now supports multi-select and bulk delete — click any file's checkbox to enter select mode, use "Select All" to grab everything currently visible (respecting your active search/filter), then delete the selection with one confirmation instead of one-by-one (Issue #94, thanks @Blaim)
