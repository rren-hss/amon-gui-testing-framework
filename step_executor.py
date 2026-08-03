import json
import os
import subprocess

from squish_runner import run_squish_step
from tests import APPLICATIONS
from utils import timestamp
from config import MANUAL_POPUP_PATH

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
        popup_path,
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

def execute_step(test_case, step):

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
