# Contributing to KX-Bridge

Thanks for taking the time to contribute! Here's everything you need to know.

---

## How to report a bug or request a feature

Use the issue tracker:

- **Bug:** [New Bug Report](https://gitea.it-drui.de/viewit/KX-Bridge-Release/issues/new?template=bug_report.md)
- **Feature:** [New Feature Request](https://gitea.it-drui.de/viewit/KX-Bridge-Release/issues/new?template=feature_request.md)

Please fill in the template — especially the **KX-Bridge version** and **logs**.  
Issues without version info are hard to debug.

---

## How to submit a Pull Request

### 1. Fork the repository

Click **Fork** at the top of this page.  
You now have your own copy at `gitea.it-drui.de/your-username/KX-Bridge-Release`.

### 2. Clone your fork

```bash
git clone https://gitea.it-drui.de/your-username/KX-Bridge-Release.git
cd KX-Bridge-Release
```

### 3. Create a branch

Always branch off `nightly`:

```bash
git checkout nightly
git checkout -b feature/my-feature   # or fix/my-fix
```

### 4. Make your changes

- Test your changes locally with Docker:
  ```bash
  docker build -t kx-bridge:dev .
  docker run -p 7125:7125 -v ./config:/app/config kx-bridge:dev
  ```
- No debug `print()` statements — use `logging`
- Keep commits focused; one thing per commit

### 5. Push and open a PR

```bash
git push origin feature/my-feature
```

Gitea will show a banner — click **"Create Pull Request"**.  
The PR template will be pre-filled. Set the target branch to **`nightly`**.

---

## Branch model

```
master    ← stable releases only (merged by maintainer)
nightly   ← integration branch — PRs go here
feature/* ← your feature branch (in your fork)
fix/*     ← your bugfix branch (in your fork)
```

Your PR always targets `nightly`. The maintainer periodically merges `nightly → master` for a new stable release.

---

## Commit style

Use conventional commit prefixes:

| Prefix | When |
|---|---|
| `feat:` | new feature |
| `fix:` | bug fix |
| `docs:` | documentation only |
| `chore:` | maintenance, dependencies |
| `refactor:` | code change without new feature or fix |

Example: `fix: prevent crash when printer is offline during startup`

---

## Language

- **Code and comments:** English
- **Issue comments:** match the language of the issue (if someone writes in German, reply in German)
- **Commit messages:** English

---

## Questions?

Open a [Discussion](https://gitea.it-drui.de/viewit/KX-Bridge-Release/issues) or leave a comment on the relevant issue.
