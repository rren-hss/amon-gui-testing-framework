# CLAUDE.md

Guidance for Claude Code when working in this repo. See `README.md` for full
architecture/setup docs — this file stays short and adds a running session
log so context survives across conversations.

## Project in one paragraph

Python test-orchestration framework for the **Amon** ophthalmic surgical
system. `main.py` runs an ordered test plan (`tests.py`: `TEST_STEPS`)
against three GUIs (Cart, Assistant, Surgeon/Cockpit) via three step types:
Squish-driven GUI automation (`squish_runner.py` + `suite_amon_cart_attach/`,
`suite_amon_cockpit_attach/`), SSH/terminal checks (`remote_runner.py`), and
Tkinter manual-confirmation popups (`manual_popup.py`). Results render to
per-test-case HTML reports (`report_generator.py`). Can target either a
physical rig or a Docker environment; `reset_surgical_sequence.sh` /
`baseline_reset.py` reset the GUIs to a known-fresh state between cases.

## Conventions worth knowing

- Squish `test.py` handlers live in a `STEP_HANDLERS` dict keyed by the
  `squish_step` name referenced from `tests.py`. New automated steps need a
  handler there *and* a `tests.py` entry *and* any new object-map entries in
  that suite's `shared/scripts/names.py`.
- Squish object attributes (e.g. `window.title`) come back as Squish
  wrapper types, not native Python — `str()`/cast before using them outside
  Squish APIs (e.g. passing to `subprocess`).
- On the Docker test environment, window stacking is controlled by the
  *host's* Mutter (DISPLAY is bind-mounted in), not a containerized WM —
  Qt's own `raise()`/`requestActivate()` are silently ignored by
  focus-stealing prevention there. `wmctrl -a <title>` works because Mutter
  treats it as an external request. `squishrunner` itself runs on the host,
  so `wmctrl` is directly callable from `test.py`.
- `control_mux` and `rtmod_surgical_planner` (cart, Docker) never respond to
  SIGTERM — confirmed via source and live testing. `reset_surgical_sequence.sh`
  skips the SIGTERM+wait for just those two and goes straight to SIGKILL.

## Session log

Append a dated entry each session summarizing what was worked on. Keep
entries terse — a few bullets, not prose.

### 2026-08-24
- Session started with pre-existing uncommitted changes already in the
  working tree (no memory of the conversation that produced them — likely a
  prior session). Reconstructed intent from the diff rather than asking the
  user to re-explain:
  - `reset_surgical_sequence.sh`: added `CART_FORCE_KILL_PATTERNS`
    (`control_mux`, `rtmod_surgical_planner`) — go straight to SIGKILL, no
    SIGTERM/wait, since they never exit gracefully.
  - `suite_amon_cart_attach/`, `suite_amon_cockpit_attach/` `test.py`:
    reworked `bring_to_front()` to try `wmctrl -a <title>` before falling
    back to the raw Qt `raise()`/`requestActivate()` call.
  - New Squish handler `verify_agui_telecentric_camera_feed` (cart suite)
    + object-map entries for `videoPlayer`/`videoSink` in
    `suite_amon_cart_attach/shared/scripts/names.py`.
  - New test case `QA-T1136` in `tests.py` exercising the above.
  - None of this was committed yet as of this entry.
- Created this CLAUDE.md at the user's request, to serve as a persistent
  session log/handoff doc across conversations (this repo previously had
  none — `README.md` covers architecture/setup but not session continuity).

### 2026-08-25
- User recreated the Docker test environment (`~/Desktop/polaris-v3`,
  sibling project — `docker-compose.yaml`/`docker-entrypoint.sh` live there,
  not in this repo) with a full volume wipe. `make run cart` then failed:
  `system_manager` couldn't create `ROS_LOG_DIR` (`/home/rren/log`).
  - Root cause: `docker-entrypoint.sh`'s `useradd` (no `-m`, since the image
    already bakes in a root-owned `/home/$USER_NAME`) never chowns that
    home dir to the runtime UID — only `/horizon/*` and the Squish log dir
    were explicitly chowned. Invisible on a normal `--force-recreate`
    (named volume persists); only surfaces after a full volume wipe.
  - Fixed live via `docker exec -u 0 <container> chown rren:rren /home/rren`
    on `docker-cart`/`docker-cockpit` to unblock immediately.
  - Patched `~/Desktop/polaris-v3/docker-entrypoint.sh` to `chown
    "$USER_ID":"$GROUP_ID" "/home/$USER_NAME"` unconditionally after the
    `useradd` block. Rebuilt (`make build cart` — all 4 services share one
    image, `horizonsurgical/polaris-v3:latest`, so one build covers all),
    recreated cart+cockpit, verified the fix holds post-rebuild.
  - Relevant if `reset_surgical_sequence.sh`'s docker path or the Squish
    suites start failing right after someone else does a full Docker
    volume wipe on that project.
