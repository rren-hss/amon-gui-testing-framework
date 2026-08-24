# Amon GUI Testing Framework

A Python test-orchestration framework for the **Amon** ophthalmic surgical system. It drives end-to-end regression tests across three physical/GUI stations — the **Cart GUI**, **Assistant GUI**, and **Surgeon GUI** — plus SSH-based host health checks, and produces browsable HTML test reports.

The framework itself does not talk to the application UIs directly. It orchestrates three kinds of test steps:

1. **Automated GUI steps**, driven by [Squish for Qt](https://www.qt.io/squish) test scripts running against the live applications.
2. **Terminal / SSH steps**, run on remote hosts via Paramiko (e.g. boot-check scripts).
3. **Manual steps**, where a human operator confirms a GUI state through a Tkinter popup (used for devices Squish cannot inspect, like a 3D video monitor).

Results from all three step types are normalized into a common schema and rendered into a self-contained HTML report per test case.

---

## Architecture Overview

```
main.py                    Entry point / orchestration loop
  ├─ tests.py               Test case & step definitions (the "test plan")
  ├─ step_executor.py        Dispatches each step to the right runner
  │    ├─ squish_runner.py    Runs Squish steps ("type": "auto")
  │    │    └─ suite_amon_cart_attach/     Squish suite: cartGUI + assistantGUI
  │    │    └─ suite_amon_cockpit_attach/  Squish suite: surgeonGUI
  │    ├─ remote_runner.py    Runs SSH/terminal steps ("type": "terminal"/"ssh"/"command")
  │    └─ manual_popup.py     Runs manual steps ("type": "manual") as a subprocess
  │         └─ multistep_guis.py   Tkinter popup UI shown to the operator
  ├─ demo_pause.py           Optional pause/inspect dialog between steps (DEMO_MODE)
  ├─ system_metadata.py      Looks up installed Polaris software version via Ansible
  ├─ report_generator.py     Renders HTML reports + console summary
  ├─ run_context.py          Per-run output directory & unique artifact naming
  ├─ utils.py                 Logging setup & timestamp helper
  └─ config.py                Central configuration (hosts, ports, paths, env overrides)
```

### Execution flow

1. `main.py` sets up logging/output directories, then looks up the installed Polaris software version over Ansible (best-effort — a failure here only produces a warning, it does not stop the run).
2. It iterates the ordered list of test cases in `tests.py` (`TEST_STEPS`), and within each test case, iterates its steps in order.
3. Each step is handed to `step_executor.execute_step()`, which looks at the step's `"type"` and dispatches it to `squish_runner`, `remote_runner`, or `manual_popup`.
4. Every runner returns a normalized result dict (`test_case`, `step_id`, `status`, `actual`, `expected`, `screenshot`, `notes`, `timestamp`, …).
5. After each step, `main.py` decides whether to stop:
   - If the step aborted (operator/demo abort), execution stops immediately.
   - If the step failed and the test case's `failure_policy` is `"abort"`, execution stops for that run.
   - Otherwise (`"continue"`, the default), execution proceeds to the next step/test case.
6. If `DEMO_MODE` is enabled and a step is flagged `"demo_pause": True`, a Tkinter dialog pauses the run after that step so a presenter can inspect the physical displays (e.g. over VNC) before continuing or aborting.
7. Once all test cases finish (or the run is aborted), `main.py` prints a console summary and generates one HTML report per test case via `report_generator.py`.

### Test plan model (`tests.py`)

- `APPLICATIONS`: maps a logical GUI name (`cartGUI`, `assistantGUI`, `surgeonGUI`) to the Squish AUT (Application Under Test) alias, host/port, Squish suite directory, default test case, and timeout.
- `TEST_STEPS`: an ordered list of **test cases**, each with an `id`, `name`, `gui`, `failure_policy` (`continue` or `abort`), and a list of **steps**. Each step declares a `type` (`auto`, `manual`, `terminal`/`ssh`/`command`) plus type-specific fields (e.g. `squish_step`, `command`, `manual_popup_path`).

This file is effectively the test plan — adding a new test case or step means editing the `TEST_STEPS` list (and, for automated steps, adding a matching handler in the relevant Squish suite's `test.py`).

---

## Functional Breakdown

### `main.py`
The orchestrator. Loads the test plan, runs every step in order, applies stop/abort/continue policy per test case, handles demo pauses, and triggers report generation at the end. Also wraps the whole run in a top-level exception handler so an unhandled framework error still produces a report (as a synthetic `FRAMEWORK` failure) instead of crashing silently.

### `config.py`
Central configuration module. Defines framework paths (output root, manual popup path), Amon Cart/Cockpit host+port, SSH user/timeout, the local `squishrunner` binary path, Ansible inventory path/host group for version lookups, and two runtime toggles: `DEMO_MODE` and `OPEN_REPORTS`. Every value can be overridden via environment variable (see Setup below), with sane defaults baked in.

### `tests.py`
The test plan and application registry described above (`APPLICATIONS`, `TEST_STEPS`). This is the file you edit to add, remove, or reorder tests.

### `step_executor.py`
Routes each step to the correct runner based on its `"type"`:
- `"auto"` → resolves the target application config (merging step/test-case overrides with the `APPLICATIONS` defaults) and calls `squish_runner.run_squish_step`.
- `"manual"` → calls `run_manual_step`, which launches `manual_popup.py` as a subprocess, passes step details as CLI args, and parses the JSON result the popup prints to stdout.
- `"terminal"` / `"ssh"` / `"command"` → calls `remote_runner.run_remote_step`.
- Unknown types produce a synthetic `FAIL` result rather than crashing the run.
Also defines the failure-result builders (`manual_failure`) used when the manual-step subprocess itself misbehaves (bad JSON, missing popup path, etc).

### `squish_runner.py`
Runs one Squish GUI step by shelling out to `squishrunner` with the suite/testcase from the resolved application config, passing step context (test case id/name, GUI, instruction, expected result, screenshot filename) to the Squish script via environment variables. It then reads back a `results.json` file the Squish script is expected to write, normalizes it into the common result schema, and appends a detailed log entry (stdout/stderr/return code) to the run log. Handles subprocess timeouts and malformed/missing results as framework failures rather than exceptions.

### `remote_runner.py`
Runs SSH/terminal steps via Paramiko. Prompts once (interactively, cached in-process) for the SSH password the first time it's needed. Connects to the step's target host, executes the configured shell command, and captures stdout/stderr/exit code. Has a special-cased **boot-check parser** (`parser.type == "bootcheck"`) that regex-parses the Amon boot-check script's row-per-module output (`PASS`/`WARN`/`FAIL` + a "Total failures" count) into a structured pass/warn/fail summary; any other terminal step is judged purely on exit code.

### `manual_popup.py`
A small CLI entry point invoked as a subprocess by `step_executor.run_manual_step`. Parses step details from argv, shows the Tkinter popup (via `multistep_guis.show_manual_popup`), prints the resulting JSON to stdout, and exits with a status code (`0` pass, `1` fail, `2` unknown, `3` abort) so the parent process can also infer outcome from the exit code if needed.

### `multistep_guis.py`
The actual Tkinter UI for manual verification steps — shown when a step can't be checked via Squish (e.g. confirming a 3D monitor is displaying video). Displays the instruction and expected result, lets the operator attach a file (e.g. a manual screenshot), add free-text notes, and mark the step **Pass** or **Fail**. On Fail, a comment is required and a follow-up dialog asks whether to continue the run or abort it.

### `demo_pause.py`
A lightweight Tkinter dialog used only when `DEMO_MODE=true` and a step is tagged `"demo_pause": True`. Pauses execution after that step so a live demo presenter can visually inspect the real displays before choosing **Continue** or **Abort Demo**.

### `system_metadata.py`
Looks up the installed Polaris software version across the Amon hosts by running `apt list --installed | grep polaris` over Ansible against the configured inventory/host group, then parses the per-host `ansible ... -m shell` output into a normalized `{status, summary, hosts, raw_output}` structure. This is informational — used to stamp the generated report with the software version under test — and a lookup failure only produces a warning, never stops the run.

### `report_generator.py`
Builds one self-contained, styled HTML report per test case (in `REPORT_DIR`) plus a plain-text console summary (`print_summary`). Each report includes a test-configuration/metadata section (system name, subsystems, software/hardware test articles, Polaris version), a results summary (pass/fail/warn/aborted counts, step-type breakdown), and a full step-by-step results table with clickable screenshots. Reports include client-side JS to toggle an "edit notes" mode and re-download the annotated report — useful for a reviewer adding comments after the run. `open_reports()` optionally auto-opens generated reports via `xdg-open` when `OPEN_REPORTS=true`.

### `run_context.py`
Computes a unique run ID (timestamp + random token) at import time and derives the per-run directory layout (`RUN_DIR`, `REPORT_DIR`, `SCREENSHOT_DIR`, `LOG_PATH`) under `OUTPUT_ROOT`. Also provides `unique_artifact_name()`, used to generate collision-free screenshot and report filenames.

### `utils.py`
Small shared helpers: `timestamp()` for consistent timestamp formatting, and `setup_logging()`, which initializes the run's output directories and configures logging to both the run's log file and stdout (and quiets Paramiko's noisy default logging).

### Squish test suites (`suite_amon_cart_attach/`, `suite_amon_cockpit_attach/`)
Squish IDE test suites invoked by `squish_runner.py`. Each suite's `tst_*` folder contains a `test.py` that:
- Reads step context from environment variables set by `squish_runner.py` (`SQUISH_STEP`, `TARGET_AUT`, `STEP_ID`, etc).
- Attaches to the already-running application under test (Squish does **not** launch the app — it must already be running, as `main.py` logs on startup).
- Dispatches to a per-step handler function via a `STEP_HANDLERS` dict (e.g. `verify_cart_gui_window`, `cgui_login`, `verify_agui_viscoat_step`), each of which uses Squish's `waitForObject`/`test.compare`/`test.verify` APIs against objects defined in `shared/scripts/names.py` (the Squish object map).
- Writes a `results.json` (via `write_result`) that `squish_runner.py` reads back, and optionally captures a screenshot.
- `suite_amon_cart_attach` drives both **cartGUI** and **assistantGUI** (they run on the same host); `suite_amon_cockpit_attach` drives **surgeonGUI**.
- `tst_development_cart` and `tst_draft_cockpit` are scratch/dev test cases (e.g. `tst_development_cart` just attaches to both apps and drops into `test.breakpoint()`) used for interactive Squish development, not part of the automated run.
- `run_test.sh` is a standalone shell helper to invoke `squishrunner` directly against `tst_attach_cart` outside of the Python framework (useful for debugging a suite in isolation).

---

## Setup Instructions

### Prerequisites
- **Python 3** with the following third-party packages: `paramiko` (SSH). Everything else used (`tkinter`, `argparse`, `json`, `subprocess`, `logging`, `secrets`, `getpass`) is part of the Python standard library.
  ```bash
  pip install paramiko
  ```
  `tkinter` is required for the manual-step popup and demo-pause dialog — on Linux it's usually a separate OS package (e.g. `sudo apt install python3-tk`).
- **Squish for Qt 9.2.2** installed locally, with `squishrunner` reachable (default expected at `~/squish-for-qt-9.2.2/bin/squishrunner`, overridable — see below). A running **Squish Server** on each target GUI host, reachable on the configured host/port.
- **Ansible** installed and on `PATH`, with an inventory file describing the `amon` host group, if you want the Polaris-version lookup step to succeed. This is optional — the run still proceeds (with a warning) if Ansible or the inventory is unavailable.
- SSH access (password auth) to the Cart and Cockpit hosts for the terminal/boot-check steps — the framework will prompt interactively for the password the first time it's needed.
- The three GUIs under test (**cartGUI**, **assistantGUI**, **surgeonGUI**) must already be running on their target hosts before starting a run — the framework attaches to them via Squish, it does not launch them.

### Configuration
All configuration lives in `config.py` and is overridable via environment variables — nothing needs to be hardcoded/edited for a different environment:

| Variable | Purpose | Default |
|---|---|---|
| `AMON_TEST_OUTPUT_ROOT` | Where per-run output (reports, screenshots, logs) is written | `./test_outputs` |
| `MANUAL_POPUP_PATH` | Path to the manual-step popup script | `./manual_popup.py` |
| `AMON_CART_IP` / `AMON_CART_PORT` | Cart host Squish server address | `172.16.0.102` / `4322` |
| `AMON_COCKPIT_IP` / `AMON_COCKPIT_PORT` | Cockpit host Squish server address | `172.16.0.103` / `4322` |
| `AMON_SSH_USER` | SSH username for terminal steps | `horizon` |
| `AMON_SSH_KEY_PATH` | SSH private key path (currently unused by `remote_runner.py`, which uses password auth) | *(empty)* |
| `AMON_SSH_CONNECT_TIMEOUT` | SSH connect timeout (seconds) | `15` |
| `SQUISHRUNNER` | Path to the `squishrunner` binary | `~/squish-for-qt-9.2.2/bin/squishrunner` |
| `ANSIBLE_INVENTORY_PATH` | Ansible inventory used for the Polaris version lookup | `./ansible/inventory.yaml` |
| `DEMO_MODE` | Enables the demo-pause popup on flagged steps | `false` |
| `OPEN_REPORTS` | Auto-open generated HTML reports after the run | `false` |

### Running a test run
1. Ensure cartGUI, assistantGUI, and surgeonGUI are running and reachable via their Squish servers.
2. From the repo root:
   ```bash
   python3 main.py
   ```
3. You'll be prompted once for the SSH password if any terminal/boot-check steps are in the plan.
4. Progress streams to the console and to `test_outputs/<run_id>/run.log`. When the run finishes, an HTML report per test case is written to `test_outputs/<run_id>/reports/`, and screenshots to `test_outputs/<run_id>/screenshots/`. Set `OPEN_REPORTS=true` to have them open automatically.

### Modifying the test plan
- Add/edit test cases and steps in `tests.py` (`TEST_STEPS`).
- For a new automated (`"auto"`) step, add a corresponding handler function to the appropriate Squish suite's `test.py` (`suite_amon_cart_attach` for cartGUI/assistantGUI, `suite_amon_cockpit_attach` for surgeonGUI), register it in that file's `STEP_HANDLERS` dict, and reference its key as `squish_step` in `tests.py`. Add any new object-map entries it needs to `shared/scripts/names.py`.
- For a new manual step, set `"type": "manual"` and provide `manual_popup_path` (defaults to `MANUAL_POPUP_PATH`/`manual_popup.py`).
- For a new terminal/SSH step, set `"type": "terminal"` (or `"ssh"`/`"command"`) with `host` and `command`; add `"parser": {"type": "bootcheck"}` if the command is the boot-check script.
