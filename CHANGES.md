## KX-Bridge 0.9.27-nightly9 — Nightly Build

[experimentell] Ungetestete Features, nur für Tester geeignet.

### Änderungen seit `v0.9.26`

- fix(spoolman): Status-Dot beim Seitenload initialisieren
- chore: CHANGES.md mit echtem Changelog aus Dev-Repo ins Release-Repo schreiben
- fix(spoolman): SPOOLMAN_* env-Cache bei Restart leeren, Status-Dot nach Save aktualisieren
- chore: README.es.md + CONTRIBUTING.md in release.sh-Sync aufnehmen
- docs: Nightly-Sektion, Wartungshinweis + CONTRIBUTING.md, FR/IT-Sprachen, Downloads-Badge
- fix(update): Nightly-Vergleich auf Versions-String umstellen (statt Datum)
- feat(update): Nightly-Track vom Stable-Track trennen
- fix(release): nightly immer auf nightly-Branch pushen, kein master-Push
- fix(camera): exponentielles Backoff bei ffmpeg-Fehler + /api/camera/reset + ↺-Button
- fix(release): Nightly-Release vom nightly-Branch erlauben
- feat(i18n): fehlende UI-Übersetzungen ergänzt + Keys alphabetisch sortiert (PR #70 @fenopy)
- fix: config/config.ini.example beim Release-Sync mitübertragen (Issue #72)
- feat(ui): Integrationen-Tab in Settings (Spoolman + Obico-Hinweis)
- feat(stack): KobraX Full Stack Compose für Portainer (KX-Bridge + Obico + Spoolman)
- feat(release): Nightly/Stable Release-Workflow mit eigenem Docker-Tag
- feat(spoolman): optionale Spoolman-Filamentverbrauch-Integration (PR #65, @p2l)
- fix(release): Artifact-Download per HTTP statt lokalem Dateipfad

---

### Docker-Image aktualisieren

```bash
docker compose pull && docker compose up -d
```

Image-Tag: `gitea.it-drui.de/viewit/kx-bridge:nightly`
