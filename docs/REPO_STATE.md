# REPO_STATE — CareSentry repository inspection (Gate 1)

**Date checked:** 2026-10-10
**Inspector:** CORE lane (integrator)
**Commands run (all read-only):** `git status`, `git remote -v`, `git fetch origin`, `git branch -r`, `git log --oneline origin/main -n 20`, `git ls-tree --name-only origin/main`, `git ls-tree --name-only main`, `git diff --name-only main origin/main`

---

## 1. Remote

- `origin` = `https://github.com/FROSTY-MUG/CareSentry.git` (already configured, fetch + push URLs identical). No URL change needed.
- `git fetch origin` succeeded; remote is reachable.

## 2. Does origin/main exist?

**Yes.** `origin/HEAD -> origin/main` and `origin/main` both resolve.

## 3. Commits on origin/main

**1 commit.**

```
0f0fc2b feat: initial release of CareSentry-AI v1.0.0-rc1
```

## 4. Top-level names on origin/main (12 entries)

```
.agents
.gitignore
CODE_OF_CONDUCT.md
LICENSE
README.md
SECURITY.md
benchmark_results.json
data
demo
harness
pyproject.toml
requirements.txt
tests
```

## 5. Top-level name conflicts with our layout?

Our layout paths: `harness/`, `guard/`, `clinical/`, `studio/`, `eval/`, `ops/`, `contracts/`, `docs/`, `data/`, `tests/`, `demo/`, `.agents/`, `.github/`.

| Our path | On origin/main? | Conflict? |
|---|---|---|
| `harness/` | Yes | Shared, same content (origin/main == local main for tracked files) |
| `data/` | Yes | Shared |
| `tests/` | Yes | Shared |
| `demo/` | Yes | Shared |
| `.agents/` | Yes (but only `skills/` tracked) | Shared; local adds `skills/caresentry-guard/` untracked |
| `guard/` | **No** | None — local untracked work, not on remote |
| `clinical/` | **No** | None — local untracked work, not on remote |
| `studio/` | **No** | None — local untracked work, not on remote |
| `eval/` | **No** | None |
| `ops/` | **No** | None |
| `contracts/` | **No** | None |
| `docs/` | **No** | None |
| `.github/` | **No** | None (local adds `workflows/guard-ci.yml` untracked) |

**Verdict: no path conflicts.** Every path on origin/main that overlaps our layout (`harness/`, `data/`, `tests/`, `demo/`, `.agents/`) is byte-identical to local main — `git diff --name-only main origin/main` returned only untracked guard/clinical/studio/.agents/.github additions, zero tracked-file differences.

## 6. Local state vs remote

- Local `main` == `origin/main` for all **tracked** files (branch "up to date").
- Local working tree additionally contains **untracked** lane work (not on remote):
  - `guard/` — full Codex guard lane (src, tests, tools, docs, bench, data_guard, evals)
  - `clinical/` — OpenCode clinical lane (adapters, sources, rule_packs, src, tests, docs)
  - `studio/` — Hermes studio lane (appears to be a near-full repo copy: harness, clinical, data, demo, docs, eval, ops, pyproject, requirements, studio, tests)
  - `.agents/skills/caresentry-guard/SKILL.md`
  - `.github/workflows/guard-ci.yml`
- Existing local branch: `track-c/guard` (checked out earlier this session; not on remote).
- Existing worktree created this session: `C:\Users\HP\app\CareSentry-wt\core` on branch `lane/core` (uncommitted, no pushes).

## 7. Interpretation

Remote `origin/main` is the **v1.0.0-rc1 baseline** — the original single-commit release (harness, tests, data, demo, .agents). It does **not** contain any lane work (guard/clinical/studio). All lane work exists only in the local working tree as untracked files.

This matches the **"Commits exist, same project"** row of the path table: the remote is the same project at its baseline, not an unrelated fork. No force-push, no unrelated-history merge needed.

## 8. Recommendation

**Path: "Commits exist, same project"** — fetch and review diffs; merge only after approval; never force-push.

Rationale:
- Remote is not empty and is not an unrelated layout — it is our own v1.0.0-rc1 baseline.
- Local tracked state already equals `origin/main`, so there is nothing to merge at this moment; the reconciliation work is to *add* CORE's new files (`.gitignore`, `GIT_WORKFLOW.md`, `docs/REPO_STATE.md`, contracts, etc.) on top of the baseline and push that.
- The untracked lane directories (guard/clinical/studio) must **not** be committed by CORE — they belong to their owning lanes and are read-only here.