## Changes in this build

- Unified axes control panel: XY and Z merged into one card, shared step size selector (0.1 / 1 / 5 / 10 mm) plus custom mm input field, Home XY/Z buttons placed directly below their respective pads
- Language selector moved from header bar to Settings → Appearance
- Filament mismatch detection: Upload-and-Print is intercepted when GCode material differs from the loaded AMS slot — slot mapper dialog opens automatically to correct the assignment before printing
- Spoolman: assign a spool per AMS slot directly in the AMS status tab (dropdown per slot tile) and in the Filaments settings tab (dedicated assignment card)
- Fix: filament profiles now isolated per printer in multi-printer setups — configuring one printer no longer overwrites the other (PR #75 by @walterioo)
- Fix: printer dropdown and switch link now navigate to each printer's own bridge URL (same-origin, no cross-instance profile bleed)
- Fix: Spoolman sync rate label corrected — 0 means sync at end of print, not disabled (Issue #76)
- Slot color editor: Pickr color picker (HSV wheel + hex input), recent color swatches (up to 16, saved in browser), and "Copy color from slot" dropdown for identical backup spool setup (Issue #73)
- UI: unified dropdown and input field styling across all settings panels
