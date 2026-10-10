# Request GUARD-0002: Studio Worktree Misplacement and Missing Tests

Target lane: studio (Hermes Agent)

Observed:
- Worktree is registered at `C:\Users\HP\app\CareSentry\studio` instead of `C:\Users\HP\app\CareSentry-wt\studio`.
- Branch `lane/studio` has 0 lane-specific commits since the initial release (`0f0fc2b`).
- 8 untracked directories/files exist in `studio/` without commits.
- Running `pytest studio/tests -q` returns:
  ```text
  rc=5 (no tests collected / studio/tests not found)
  ```
- Running `pytest eval/tests -q` returns:
  ```text
  rc=4 (directory eval/tests not found)
  ```

Impact on the guard lane:
- Guard Console UI footer probes port 7860 to link to the Studio workbench; because Studio services and test suites are not committed and runnable, the studio link remains disabled.

Suggested owner action:
- Hermes Agent should move or register the worktree at `C:\Users\HP\app\CareSentry-wt\studio`, commit staged features to `lane/studio`, and provide tests under `studio/tests`.

Fallback I am using meanwhile:
- Guard Console UI performs socket polling on `127.0.0.1:7860` with a graceful fallback, keeping the link hidden when Studio is unavailable.
