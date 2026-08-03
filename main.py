import logging
import traceback
from config import (
    ANSIBLE_HOST_GROUP, 
    ANSIBLE_INVENTORY_PATH,
    ANSIBLE_VERSION_TIMEOUT,
    DEMO_MODE)

from report_generator import (
    generate_html_report,
    open_report_prompt,
    print_summary,
)
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


def main():
    setup_logging()
    results = []


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

        for test_case in TEST_STEPS:
            logging.info(
                "Starting test case %s - %s",
                test_case["id"],
                test_case["name"],
            )

            for step in test_case.get("steps", []):
                step_result = execute_step(test_case, step)
                results.append(step_result)

                if DEMO_MODE and step.get("demo_pause", "False"):
                    demo_action = pause_for_demo(
                        test_case_name=test_case["name"],
                        step_id=step["step_id"],
                        step_name=step.get("name", step.get("instruction", "UNKNOWN"))
                    )
                if demo_action == "ABORT":
                    abort_execution = True
                    logging.info("Demo aborted by presenter")
                    break
                

                logging.info(
                    "Completed %s with status %s",
                    step["step_id"],
                    step_result["status"],
                )

                if should_stop_after_step(test_case, step_result):
                    abort_execution = True
                    if step_result.get("status") in ("ABORT", "ABORTED"):
                        logging.info("Execution aborted by the operator")
                    else:
                        logging.info("Execution stopped because test case %s uses the abort failure policy", test_case["id"])
                    break

            if abort_execution:
                break

        overall_result = determine_overall_result(results)

    except Exception as error:
        logging.exception("Unhandled framework error.")
        add_framework_failure(results, error)
        overall_result = "FAILED"

    print_summary(results)
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

    report_path = generate_html_report(results, overall_result, report_metadata)

    logging.info("Test execution completed: %s", overall_result)
    logging.info("Report generated: %s", report_path)

    open_report_prompt(report_path)


if __name__ == "__main__":
    main()
