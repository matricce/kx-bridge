## Changes in this build

- Fix: wrong filament slot used in multicolor prints when T0 is unused — AMS box mapping now includes placeholder entries for all paint indices so the printer correctly matches T1/T2/T3 tool changes to the right slots (Issue #78)
- Fix: Spoolman spool-slot assignment now persisted to config.ini and restored on bridge restart
