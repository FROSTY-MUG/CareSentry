# Request GUARD-0001: Missing Clinical Worktree and Test Suite

Target lane: clinical (OpenCode)

Observed:
- Worktree path `C:\Users\HP\app\CareSentry-wt\clinical` does not exist (`Test-Path` returned False).
- Branch `lane/clinical` is missing from `git worktree list` and local branches.
- Running `pytest clinical/tests -q` returns:
  ```text
  ERROR: file or directory not found: clinical/tests
  ```
- Track B features were merged to `main` under `plus/` rather than the required `clinical/` directory.

Impact on the guard lane:
- Guard lane cannot import official clinical invariant adapters from `clinical/` as defined in Track C contract specifications, and status checks cannot detect live clinical lane tests.

Suggested owner action:
- OpenCode should provision worktree `C:\Users\HP\app\CareSentry-wt\clinical` on branch `lane/clinical`, symlink or migrate `plus/` to `clinical/`, and provide the test suite at `clinical/tests`.

Fallback I am using meanwhile:
- Guard lane uses `caresentry_guard.adapters.a_linter` (wrapping core invariants) and reports clinical rules as uninstalled in `/ui/api/status`.
