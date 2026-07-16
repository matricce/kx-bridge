## Changes in this build

- Feat: the dashboard is now fully customizable — enter edit mode to freely drag, resize (via GridStack.js), hide, and rearrange every card on a 12-column snap grid
- Feat: two built-in layout presets ("Standard", "Wide desktop" per Issue #89's original proposal) plus the ability to save your own layout as a named custom preset, switch between them, and delete presets you no longer need
- Fix: camera stream would freeze after ~15-30 minutes — non-monotonic timestamps from the printer's FLV stream broke ffmpeg's realtime pacing; now handled with `-use_wallclock_as_timestamps` (Issue #90)
- Fix: the camera card's height was previously capped at 320px and its image intercepted drag events — camera can now be resized freely like any other dashboard card
