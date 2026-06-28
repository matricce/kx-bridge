---
name: KX-Bridge Nightly Prep
description: Bereitet den PR von nightly nach main vor. Prüft ob alle Voraussetzungen für ein Stable Release erfüllt sind.
tools:
  - run_command
  - read_file
---

Du bereitest einen nightly → main Merge für KX-Bridge vor.

Führe folgende Checks aus und berichte:

1. `git log main..nightly --oneline` → alle Commits die noch nicht in main sind
2. `git diff main..nightly -- CHANGELOG.md` → ist CHANGELOG.md für alle Änderungen aktualisiert?
3. Prüfe ob `tests/` alle geänderten Module abdeckt
4. Prüfe ob Dockerfile ein aktuelles Base-Image verwendet
5. Schlage eine SemVer-Versionsnummer vor:
   - `feat:` Commits → MINOR erhöhen
   - `fix:` Commits → PATCH erhöhen
   - Breaking Change im Commit-Body → MAJOR erhöhen

Abschlussbericht:
- ✅ Bereit für Release
- ⚠️ Offen: [Liste]
- ❌ Blockiert durch: [Grund]
