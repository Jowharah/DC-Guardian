# DC-GUARDIAN — Development workflow and local setup

**Updated:** 2026-10-12. How changes reach `main`, how to read CI, and the one-time setup on the operator's Windows PC. Rules for code and research claims are in [`CLAUDE.md`](../CLAUDE.md).

## 1. How a change reaches `main`

`main` is protected by a GitHub repository ruleset (created 2026-10-12). Nobody, including the owner, can push to it directly.

1. Branch from an up-to-date `main`, named by type: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `test/<topic>`, `ui/<topic>`.
2. Commit with `type(scope): summary` and a body explaining why. Record the change in [`WORK_LOG.md`](WORK_LOG.md).
3. Push the branch and open a pull request:
   ```powershell
   git push -u origin <branch>
   gh pr create --base main
   ```
4. Wait for both CI checks (section 3):
   ```powershell
   gh pr checks <number> --watch
   ```
5. Merge with a **merge commit** (never squash or rebase: the docs cite commit hashes), which also deletes the branch:
   ```powershell
   gh pr merge <number> --merge --delete-branch
   ```
   Or on github.com: **Create a merge commit**. Claude merges only when the operator says so.
6. Update local `main`: `git checkout main; git pull --ff-only`.

## 2. The `main` ruleset

Settings → Rules → Rulesets on GitHub. Check what is enforced with `gh api repos/{owner}/{repo}/rules/branches/main`.

| Rule | Setting | Why |
|---|---|---|
| Enforcement | Active, empty bypass list | Applies to everyone, including the owner |
| Restrict deletions, block force pushes | On | History stays intact; cited hashes stay valid |
| Require a pull request | 0 approvals; merge method **Merge commit** only | Single maintainer (GitHub does not let you approve your own PR); merge commits keep hashes |
| Require status checks | Both CI jobs; branch must be up to date with `main` | A failing change cannot land |
| Require linear history | **Off** | It would forbid merge commits |

## 3. Continuous integration

`.github/workflows/ci.yml` runs on every push to any branch, as two jobs (the two required checks):

- **Python layers (Evidence, Reasoning, Response, Decision, backend):** dependency audit (pip-audit), Bandit static analysis (medium/high), then `check_all.py` against a Neo4j service. GPU, private-data and RAG-knowledge-base checks are skipped with a stated reason.
- **Frontend type-check, build and browser tests:** `npm audit` (high), type-check and build, Playwright browser tests (including the WCAG accessibility scans).

**Reading a failure**
```powershell
gh pr checks <number>                         # which job failed
gh run view <run-id> --log-failed             # failing step output
gh run download <run-id> -n check-report      # full check_all.py report and per-check logs
```

**Notes**
- `pip-audit` prints "Dependency not found on PyPI" for the CPU builds of `torch`/`torchvision`; this is expected and does not fail the job.
- A Bandit finding that has been reviewed as safe is annotated on its line with `# nosec <code>: <reason>`. Never suppress without a reason.
- A check that passes locally but fails in CI usually depends on local settings (`.env`, private data, GPU). Tests must pin any setting they rely on. Example (2026-10-12): Investigator history endpoints answered "disabled" before checking access, which only showed in CI because the local `.env` enabled history.
- Old failed runs stay in the GitHub history. What matters is the newest commit on `main` and the checks on an open pull request.

Run everything locally before pushing: `python check_all.py` (see [Validation and Operations](VALIDATION_AND_OPERATIONS.md)).

## 4. One-time setup on the operator's PC

### GitHub CLI (`gh`)

Installed 2026-10-12 as the portable build (no administrator rights needed) in `%LOCALAPPDATA%\Programs\GitHubCLI\bin`, added to the user `PATH`, after checking the download against GitHub's published SHA-256 checksum. The winget installer stalled on an administrator prompt that never appeared.

```powershell
gh auth login      # GitHub.com → HTTPS → Yes → Login with a web browser
gh auth status     # should show: Logged in to github.com account Jowharah
```
Open a new terminal after changing `PATH`. To update `gh`, repeat the portable install with the newer release, or use `winget install --id GitHub.cli -e` from your own PowerShell window and approve the administrator prompt.

### Kaspersky and Node.js tools (`claude rc`, Playwright downloads)

Kaspersky Anti-Virus scans encrypted connections by replacing site certificates with its own root ("Kaspersky Anti-Virus Personal Root Certificate"). Windows trusts that root, so browsers work, but Node.js tools do not, so they fail with `SELF_SIGNED_CERT_IN_CHAIN`. Symptoms seen: `claude rc` ("Couldn't verify Remote Control eligibility"), and the Playwright browser download.

The fix (applied 2026-10-12): export that root certificate (public part only) to `C:\Users\Aljawharah\.certs\kaspersky-root.pem` and set the user environment variable:
```
NODE_EXTRA_CA_CERTS = C:\Users\Aljawharah\.certs\kaspersky-root.pem
```
Node.js then trusts that certificate in addition to its normal list; nothing else is relaxed. Restart terminals and VS Code afterwards. If Kaspersky is uninstalled or its certificate changes, remove the variable and the `.certs` folder, or re-export.

**Never** use `NODE_TLS_REJECT_UNAUTHORIZED=0`: it turns off certificate checking for everything.

An alternative is to exclude `*.anthropic.com` and `claude.ai` from Kaspersky's encrypted-connection scanning (Settings → Network settings → Encrypted connections scanning → Manage exclusions).

### Claude Code Remote Control

After the certificate fix, `claude rc` starts a Remote Control session for this PC. If it fails, run `claude rc --debug` and check that `NODE_EXTRA_CA_CERTS` is set in the new terminal (`$env:NODE_EXTRA_CA_CERTS`).

### Running the app

See [`CLAUDE.md`](../CLAUDE.md) (Environment). Backend from the repository root; frontend from `presentation\frontend` (`npm run dev`, `npm run build`). Running `npm` in the root fails with "Could not read package.json".
