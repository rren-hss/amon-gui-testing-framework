import argparse
import logging
import traceback
from config import (
    ANSIBLE_HOST_GROUP,
    ANSIBLE_INVENTORY_PATH,
    ANSIBLE_VERSION_TIMEOUT,
    DEMO_MODE,
    TARGET_ENVIRONMENT)

from baseline_reset import return_to_baseline
from case_picker import pick_test_cases
from squish_preflight import run_preflight
import prereq_status
from report_generator import (
    generate_reports,
    generate_rollup_report,
    open_reports,
    print_summary,
)
from run_context import RUN_DIR, RUN_ID
from step_executor import execute_step
from tests import TEST_STEPS
from utils import setup_logging, timestamp
from system_metadata import get_polaris_version_metadata
from demo_pause import pause_for_demo
# from squish_runner import start_squish_server


def determine_overall_result(results):
    if any(
        result.get("status") in ("ABORT", "ABORTED")
        for result in results
    ):
        return "ABORTED"

    if any(result.get("status") == "FAIL" for result in results):
        return "FAILED"

    return "PASSED"


def should_stop_after_step(test_case, result):
    status = result.get("status", "").upper()

    failure_policy = test_case.get(
        "failure_policy",
        "continue",
    ).lower()

    if status in ("ABORT", "ABORTED"):
        return True

    return status == "FAIL" and failure_policy == "abort"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the Amon GUI testing framework.",
    )

    parser.add_argument(
        "--case",
        nargs="*",
        default=None,
        metavar="TEST_CASE_ID",
        help=(
            "One or more test case IDs to run (e.g. --case QA-T1137 "
            "QA-T1127), skipping the interactive picker. Omit to pick "
            "cases interactively."
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every test case in TEST_STEPS, skipping the interactive picker.",
    )

    return parser.parse_args()


def select_test_cases(test_steps, case_ids):
    if not case_ids:
        return test_steps

    known_ids = {test_case["id"] for test_case in test_steps}
    unknown_ids = [
        case_id for case_id in case_ids if case_id not in known_ids
    ]

    if unknown_ids:
        raise ValueError(
            f"Unknown test case ID(s): {', '.join(unknown_ids)}. "
            f"Available: {', '.join(sorted(known_ids))}"
        )

    return [
        test_case
        for test_case in test_steps
        if test_case["id"] in case_ids
    ]


def warn_about_physical_only_cases(test_cases, target_environment):
    if target_environment == "physical":
        return

    for test_case in test_cases:
        if test_case.get("requires_physical_hardware"):
            logging.warning(
                "Test case %s (%s) requires physical Amon hardware but "
                "TARGET_ENVIRONMENT is '%s' - it will likely fail.",
                test_case["id"], test_case["name"], target_environment,
            )


def add_framework_failure(results, error):
    results.append(
        {
            "test_case": "FRAMEWORK",
            "test_name": "Framework Execution",
            "gui": "N/A",
            "step_id": "FRAMEWORK-ERROR",
            "step_type": "Framework",
            "instruction": "Execute the Amon multistep test framework.",
            "expected": "The framework completes without an unhandled error.",
            "actual": f"{error}\n{traceback.format_exc()}",
            "status": "FAIL",
            "screenshot": None,
            "notes": "",
            "timestamp": timestamp(),
        }
    )


def add_baseline_reset_failure(results, test_case):
    """Records why a test case's steps never ran when its pre-case
    return_to_baseline() call fails. Uses ABORTED (not FAIL): the case
    itself was never attempted, so it isn't a step failure -- see
    report_generator.py's status priority (BLOCKED > ABORTED > FAIL > WARN)
    for how this ranks against other outcomes in a case's overall result.
    """
    results.append(
        {
            "test_case": test_case["id"],
            "test_name": test_case["name"],
            "gui": test_case.get("gui", "N/A"),
            "step_id": "BASELINE-RESET-BEFORE",
            "step_type": "Framework",
            "instruction": (
                f"Return to baseline before running test case {test_case['id']}."
            ),
            "expected": (
                "reset_surgical_sequence.sh completes and the ROS control "
                "graph (control_mux + both controller managers) is ready."
            ),
            "actual": (
                "Baseline reset failed, or the system did not become ready "
                "in time -- see the console log for reset_surgical_sequence.sh's "
                "own output. Test case skipped rather than run against an "
                "unready baseline."
            ),
            "status": "ABORTED",
            "screenshot": None,
            "notes": "",
            "timestamp": timestamp(),
        }
    )


def add_blocked_result(results, test_case, blocking_ids):
    """Records why a test case's steps never ran because a prerequisite
    (test_case["requires"]) is on record as having failed -- see
    prereq_status.py. Uses the dedicated BLOCKED status: this isn't a step
    failure or an infrastructure problem (ABORTED), it's a case that was
    never attempted because something it explicitly depends on didn't pass.
    """
    ids = ", ".join(blocking_ids)
    results.append(
        {
            "test_case": test_case["id"],
            "test_name": test_case["name"],
            "gui": test_case.get("gui", "N/A"),
            "step_id": "PREREQ-BLOCKED",
            "step_type": "Framework",
            "instruction": (
                f"Requires {', '.join(test_case.get('requires', []))} to "
                "have passed before running."
            ),
            "expected": "All required prerequisite test cases passed.",
            "actual": (
                f"Blocked: prerequisite(s) {ids} are on record as FAILED "
                "(see prereq_status.json). Test case skipped rather than "
                "run on top of a known-bad prerequisite."
            ),
            "status": "BLOCKED",
            "screenshot": None,
            "notes": "",
            "timestamp": timestamp(),
        }
    )


def main():
    args = parse_args()

    if args.all:
        selected_test_cases = TEST_STEPS
    elif args.case:
        try:
            selected_test_cases = select_test_cases(TEST_STEPS, args.case)
        except ValueError as error:
            print(error)
            return
    else:
        selected_test_cases = pick_test_cases(TEST_STEPS)
        if selected_test_cases is None:
            print("Cancelled - no test cases run.")
            return

    if not selected_test_cases:
        print("No test cases selected. Nothing to run.")
        return

    setup_logging()
    all_results = []
    test_results = []

    logging.info("Target environment: %s", TARGET_ENVIRONMENT.upper())
    warn_about_physical_only_cases(selected_test_cases, TARGET_ENVIRONMENT)

    logging.info("Running Squish preflight checks.")
    preflight_failures = run_preflight(selected_test_cases)

    if preflight_failures:
        logging.error("Squish preflight failed - aborting before any test cases run:")
        for gui_name, reason in preflight_failures:
            logging.error("  %s: %s", gui_name, reason)
        return

    polaris_metadata = get_polaris_version_metadata(
        inventory_path=ANSIBLE_INVENTORY_PATH,
        host_group=ANSIBLE_HOST_GROUP,
        timeout=ANSIBLE_VERSION_TIMEOUT
    )

    if polaris_metadata["status"] != "PASS":
        logging.warning("Could not determine Polaris version %s", polaris_metadata["summary"])

    # start_squish_server("172.16.0.103", 4322)  # cockpit / Surgeon
    # logging.info("Starting Squish server on amon-cockpit, port 4322")

    # start_squish_server("172.16.0.102", 4322)  # cart
    # logging.info("Starting Squish server on amon-cart, port 4322")


    logging.info("Starting Amon multistep GUI testing run.")
    logging.info(
        "cartGUI, assistantGUI, and surgeonGUI must already be running!"
    )

    try:
        abort_execution = False

        for test_case in selected_test_cases:
            case_results = []
            logging.info(
                "Starting test case %s - %s",
                test_case["id"],
                test_case["name"],
            )

            blocking_ids = prereq_status.blocking_prereqs(
                test_case.get("requires")
            )
            if blocking_ids:
                logging.error(
                    "Test case %s blocked - prerequisite(s) %s are on "
                    "record as failed.",
                    test_case["id"],
                    ", ".join(blocking_ids),
                )
                add_blocked_result(case_results, test_case, blocking_ids)
                all_results.extend(case_results)
                test_results.append((test_case, case_results))
                prereq_status.record_result(
                    test_case["id"], case_results, run_id=RUN_ID
                )
                continue

            if test_case.get("reset_before"):
                logging.info(
                    "Returning to baseline before test case %s.",
                    test_case["id"],
                )
                if not return_to_baseline(
                    restart_techpc=test_case.get("restart_techpc", False)
                ):
                    logging.error(
                        "Baseline reset before test case %s failed - "
                        "skipping this test case.",
                        test_case["id"],
                    )
                    add_baseline_reset_failure(case_results, test_case)
                    all_results.extend(case_results)
                    test_results.append((test_case, case_results))
                    prereq_status.record_result(
                        test_case["id"], case_results, run_id=RUN_ID
                    )
                    continue

            for step in test_case.get("steps", []):
                step_result = execute_step(test_case, step, case_results)
                case_results.append(step_result)
                all_results.append(step_result)

                if DEMO_MODE and step.get("demo_pause", False):
                    demo_action = pause_for_demo(
                        test_case_name=test_case["name"],
                        step_id=step["step_id"],
                        step_name=step.get("name", step.get("instruction", "UNKNOWN")),
                        status =step_result["status"],
                    )
                    if demo_action == "ABORT":
                        abort_execution = True
                        logging.info("Demo aborted by presenter")
                        break
                

                if should_stop_after_step(test_case, step_result):
                    abort_execution = True
                    if step_result.get("status") in ("ABORT", "ABORTED"):
                        logging.info("Execution aborted by the operator")
                    else:
                        logging.info("Execution stopped because test case %s uses the abort failure policy", test_case["id"])
                    break

            if test_case.get("reset_after"):
                logging.info(
                    "Returning to baseline after test case %s.",
                    test_case["id"],
                )
                if not return_to_baseline(
                    restart_techpc=test_case.get("restart_techpc", False)
                ):
                    logging.error(
                        "Baseline reset after test case %s failed.",
                        test_case["id"],
                    )

            test_results.append(
                (test_case,
                case_results,
                )
            )
            prereq_status.record_result(
                test_case["id"], case_results, run_id=RUN_ID
            )

            if abort_execution:
                break

        overall_result = determine_overall_result(all_results)

    except Exception as error:
        logging.exception("Unhandled framework error.")
        framework_results = []
        add_framework_failure(framework_results, error)
        all_results.extend(framework_results)
        test_results.append(
            (
                {
                    "id": "FRAMEWORK",
                    "name": "FRAMEWORK Execution",
                    "gui": "N/A"
                },
                framework_results
            )
        )
        overall_result = "FAILED"

    print_summary(all_results)
    report_metadata = {
        "system_name": "Amon",
        "units_under_test": [
            "Cart",
            "Cockpit",
        ],
        "software_test_articles": [
            "Squish for Qt 9.2.2",
        ],
        "hardware_test_articles": ["TBD"],
        "polaris_version": polaris_metadata["summary"],
        "polaris_version_status": polaris_metadata["status"],
        "polaris_packages_by_host": polaris_metadata["hosts"],
    }

    report_paths = generate_reports(test_results, report_metadata,)

    rollup_path = generate_rollup_report(
        test_results,
        selected_test_cases,
        report_metadata,
    )
    report_paths.append(rollup_path)

    logging.info("Running artifacts stored in: %s", RUN_DIR,)
    logging.info("Rollup report generated: %s", rollup_path,)
    for report_path in report_paths:
        logging.info(
            "Test report generated: %s",
            report_path,
        )
    open_reports(report_paths)


if __name__ == "__main__":
    main()
