## Changes in this build

- Fix: dashboard reprint from the cache path crashed with an AttributeError (`self._db` did not exist) instead of applying the filament slot filter (PR #93, thanks @Pavulon87)
- Feat: the dashboard now shows a banner with the reason and error code when a print is paused, with a direct link to the Anycubic error-code docs (PR #92, thanks @Pavulon87)
- Fix: `/api/camera/stream` (the MJPEG live view used by the dashboard and every Moonraker-compatible client) opened a brand-new ffmpeg process and printer connection per HTTP client — two simultaneous viewers could already exhaust the printer's very limited camera connection slots and cause intermittent "stream unavailable"/429 failures. All consumers now share one ffmpeg process via the same fanout pattern already used for the H.264 stream (credit to @Pavulon87 for the fix and for finding two related race conditions along the way)
