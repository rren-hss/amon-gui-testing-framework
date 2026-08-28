import json
import os
import subprocess
from pathlib import Path

from squish_runner import run_squish_step
from remote_runner import run_remote_step
from tests import APPLICATIONS
from utils import timestamp
from config import MANUAL_POPUP_PATH
from run_context import SCREENSHOT_DIR
from window_screenshot import capture_window

def resolve_application(test_case, step):
    gui = step.get(
        "gui",
        test_case.get("gui"),
    )
    if gui not in APPLICATIONS:
        raise KeyError(f"No application config exists for GUI: {gui}")
    
    application = APPLICATIONS[gui].copy()

    for key in(
        "aut",
        "host",
        "port",
        "suite",
        "testcase",
        "timeout",
    ):
        if key in test_case:
            application[key] = test_case[key]
        if key in step:
            application[key]=step[key]
    return application

def run_manual_step(test_case, step):
    popup_path = step.get(
    "manual_popup_path",
    test_case.get(
        "manual_popup_path",
        "",
    ),
)
    if not popup_path:
        return manual_failure(test_case, step, "No manual popup path was configured",)
    
    environment = os.environ.copy()
    environment.pop(
        "PYTHONHOME",
        None,
    )
    environment.pop(
        "PYTHONPATH",
        None,
    )
    environment.pop(
        "LD_PRELOAD",
        None
    )
    command = [
        "/usr/bin/python3",
        str(popup_path),
        "--test-case-id",
        test_case["id"],
        "--test-case-name",
        test_case["name"],
        "--step-id",
        step["step_id"],
        "--instruction",
        step["instruction"],
        "--expected",
        step["expected"],
    ]

    try:
        completed = subprocess.run(
            command,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    except Exception as error:
        return manual_failure(
            test_case,
            step,
            str(error),
        )

    output = (
        completed.stdout or ""
    ).strip()

    try:
        popup_result = json.loads(
            output
        )

    except json.JSONDecodeError:
        details = (
            completed.stderr
            or output
            or "No popup output"
        ).strip()

        return manual_failure(
            test_case,
            step,
            details,
        )

    status = str(
        popup_result.get(
            "status",
            "FAIL",
        )
    ).upper()

    action = str(
        popup_result.get(
            "action",
            "continue",
        )
    ).lower()

    if action == "abort":
        status = "ABORTED"

    elif status == "FAILED":
        status = "FAIL"

    screenshot_path = None
    if(
        status in ("PASS", "FAIL")
        and step.get("screenshot")
    ):
        screenshot_step = {
            **step,
            "type": "auto",
            "squish_step": "capture_current_screen",
            "name": (
                f"{step.get('name', step['step_id'])} "
                "Screenshot"
            )
        }
        application = resolve_application(test_case, step)
        screenshot_result = run_squish_step(test_case, screenshot_step, application,)
        screenshot_path = screenshot_result.get("screenshot")
        

    return {
    "test_case": test_case["id"],
    "test_name": test_case["name"],
    "gui": step.get(
        "gui",
        test_case.get(
            "gui",
            "Unknown",
        ),
    ),
    "step_id": step["step_id"],
    "step_type": "Manual",
    "instruction": step.get(
        "instruction",
        "",
    ),
    "expected": step.get(
        "expected",
        "",
    ),
    "actual": popup_result.get(
        "actual",
        "",
    ),
    "status": status,
    "screenshot": (
        screenshot_path
        or popup_result.get("screenshot")
        or step.get("screenshot")
    ),
    "notes": popup_result.get(
        "notes",
        "",
    ),
    "timestamp": timestamp(),
}

def _parse_timer_seconds(text):
    """Parses a "MM:SS" or "HH:MM:SS" timer reading into total seconds."""

    parts = str(text).strip().split(":")

    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)

    raise ValueError(f"Unrecognized timer format: {text!r}")


def run_compare_timers_step(test_case, step, case_results):
    """Compares surgical timer readings captured from multiple GUIs earlier
    in the same test case (QA-T1139) against a reference GUI's reading.

    Each prior capture step (see suite test.py's capture_*_timer functions)
    pairs its GUI's displayed timer text with a Python time.time() taken at
    the instant it was read. Squish can only attach to one AUT at a time,
    so these captures happen strictly one after another, not
    simultaneously -- comparing the raw values directly would conflate
    that sequential-capture gap with actual clock drift between the GUIs.
    Instead, each non-reference reading is projected onto the reference's
    capture instant using the wall-clock gap between the two captures,
    which cancels out the capture-order skew and isolates the GUIs' own
    timers from each other.

    Step fields:
        reference_gui: GUI whose reading the others are compared against
            (default "cartgui", case-insensitive match against each prior
            result's "gui" field).
        tolerance_seconds: max allowed projected delta to still pass
            (default 1.0, per QA-T1139's spec).
    """

    base_result = {
        "test_case": test_case["id"],
        "test_name": test_case["name"],
        "gui": step.get("gui", test_case.get("gui", "Multi-GUI")),
        "step_id": step.get("step_id", "UNKNOWN"),
        "step_type": "Framework",
        "instruction": step.get(
            "instruction",
            "Compare captured surgical timer readings across GUIs.",
        ),
        "expected": step.get(
            "expected",
            "All captured timers agree with the reference GUI within tolerance.",
        ),
        "screenshot": None,
        "notes": "",
        "timestamp": timestamp(),
    }

    timer_entries = {
        str(result.get("gui", "")).lower(): result
        for result in (case_results or [])
        if result.get("timer_value") is not None
        and result.get("capture_timestamp") is not None
    }

    reference_gui = str(step.get("reference_gui", "cartgui")).lower()
    tolerance_seconds = float(step.get("tolerance_seconds", 1.0))

    if reference_gui not in timer_entries:
        return {
            **base_result,
            "actual": (
                f"No captured timer reading found for reference GUI "
                f"'{reference_gui}'. Captured GUIs: "
                f"{sorted(timer_entries) or 'none'}."
            ),
            "status": "FAIL",
        }

    reference_result = timer_entries[reference_gui]

    try:
        reference_seconds = _parse_timer_seconds(reference_result["timer_value"])
    except ValueError as error:
        return {
            **base_result,
            "actual": f"Could not parse reference ({reference_gui}) timer reading: {error}",
            "status": "FAIL",
        }

    reference_capture_time = reference_result["capture_timestamp"]

    others = {
        gui: result
        for gui, result in timer_entries.items()
        if gui != reference_gui
    }

    if not others:
        return {
            **base_result,
            "actual": (
                f"Only the reference GUI ('{reference_gui}') has a "
                "captured timer reading -- nothing to compare it against."
            ),
            "status": "FAIL",
        }

    lines = [
        f"Reference ({reference_gui}): {reference_result['timer_value']} "
        f"captured at {reference_capture_time:.3f}"
    ]

    all_within_tolerance = True

    for gui, result in sorted(others.items()):
        try:
            gui_seconds = _parse_timer_seconds(result["timer_value"])
        except ValueError as error:
            lines.append(f"{gui}: could not parse timer reading -- {error}")
            all_within_tolerance = False
            continue

        gui_capture_time = result["capture_timestamp"]

        # Project this GUI's reading onto the reference's capture instant
        # using the wall-clock gap between the two captures.
        projected_seconds = gui_seconds + (
            reference_capture_time - gui_capture_time
        )
        delta = abs(projected_seconds - reference_seconds)
        within = delta <= tolerance_seconds
        all_within_tolerance = all_within_tolerance and within

        lines.append(
            f"{gui}: {result['timer_value']} captured at {gui_capture_time:.3f} "
            f"-> projected {projected_seconds:.2f}s vs reference "
            f"{reference_seconds}s (delta {delta:.2f}s, "
            f"{'within' if within else 'EXCEEDS'} {tolerance_seconds}s tolerance)"
        )

    return {
        **base_result,
        "actual": "\n".join(lines),
        "status": "PASS" if all_within_tolerance else "FAIL",
    }


def run_window_screenshot_step(test_case, step):
    """Screenshots a window Squish has no AUT for (e.g. Tech PC's rviz2),
    via window_screenshot.py's wmctrl+mss capture. Evidence only -- this
    step's pass/fail reflects whether the capture itself succeeded, not
    anything about what the window shows. The check that matters (did the
    GUI actually transition correctly) belongs to a real Squish assertion
    elsewhere in the case, e.g. QA-T1131's cart step already verifies the
    "ready for draping" text.
    """

    base_result = {
        "test_case": test_case["id"],
        "test_name": test_case["name"],
        "gui": step.get("gui", test_case.get("gui", "Unknown")),
        "step_id": step.get("step_id", "UNKNOWN"),
        "step_type": "Framework",
        "instruction": step.get(
            "instruction",
            "Capture a screenshot of a window outside Squish's reach.",
        ),
        "expected": step.get("expected", "Screenshot captured successfully."),
        "notes": "",
        "timestamp": timestamp(),
    }

    title_contains = step.get("window_title_contains")

    if not title_contains:
        return {
            **base_result,
            "actual": "No window_title_contains configured for this step.",
            "status": "FAIL",
            "screenshot": None,
        }

    screenshot_name = step.get("screenshot") or f"{test_case['id']}_{step.get('step_id', 'window')}.png"
    screenshot_path = Path(SCREENSHOT_DIR) / screenshot_name

    try:
        window = capture_window(title_contains, screenshot_path)
    except Exception as error:
        return {
            **base_result,
            "actual": f"Could not capture window screenshot: {error}",
            "status": "FAIL",
            "screenshot": None,
        }

    return {
        **base_result,
        "actual": f"Captured screenshot of window '{window['title']}' (matched '{title_contains}').",
        "status": "PASS",
        "screenshot": str(screenshot_path),
    }


def execute_step(test_case, step, case_results=None):

    step_type = str(
        step.get(
            "type",
            "",
        )
    ).lower()

    if step_type == "auto":
        application = resolve_application(
            test_case,
            step,
        )

        return run_squish_step(
            test_case,
            step,
            application,
        )

    if step_type == "manual":
        return run_manual_step(
            test_case,
            step,
        )
    if step_type in (
        "terminal",
        "ssh",
        "command",
    ):
        return run_remote_step(
            test_case,
            step,
        )

    if step_type == "compare_timers":
        return run_compare_timers_step(
            test_case,
            step,
            case_results,
        )

    if step_type == "window_screenshot":
        return run_window_screenshot_step(
            test_case,
            step,
        )

    return {
        "test_case": test_case["id"],
        "test_name": test_case["name"],
        "gui": step.get(
            "gui",
            test_case.get(
                "gui",
                "Unknown",
            ),
        ),
        "step_id": step.get(
            "step_id",
            "UNKNOWN",
        ),
        "step_type": "Framework",
        "instruction": step.get(
            "instruction",
            "",
        ),
        "expected": step.get(
            "expected",
            "",
        ),
        "actual": (
            "Unsupported step type: "
            f"{step.get('type')}"
        ),
        "status": "FAIL",
        "screenshot": None,
        "notes": "",
        "timestamp": timestamp(),
    }

def manual_failure(
    test_case,
    step,
    actual,
):
    return {
        "test_case": test_case["id"],
        "test_name": test_case["name"],
        "gui": step.get(
            "gui",
            test_case.get(
                "gui",
                "Unknown",
            ),
        ),
        "step_id": step["step_id"],
        "step_type": "Manual",
        "instruction": step.get(
            "instruction",
            "",
        ),
        "expected": step.get(
            "expected",
            "",
        ),
        "actual": (
            "Manual step framework error: "
            f"{actual}"
        ),
        "status": "FAIL",
        "screenshot": step.get(
            "screenshot"
        ),
        "notes": "",
        "timestamp": timestamp(),
    }
