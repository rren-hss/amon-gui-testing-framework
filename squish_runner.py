import json
import os
import subprocess
import tempfile
import paramiko
import logging


from config import (
    LOG_PATH,
    SCREENSHOT_DIR,
    SQUISHRUNNER,
)
from utils import timestamp

# def start_squish_server(host, port, username="horizon", password="horizon"):
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     client.connect(hostname=host, username=username, password=password)

#     cmd = (
#         f"nohup ~/squish-for-qt-9.2.2/bin/squishserver "
#         f"--port {port} --verbose "
#         f"> /tmp/squishserver_{port}.log 2>&1 &"
#     )
#     stdin, stdout, stderr = client.exec_command(cmd)

#     client.close()  # nohup detaches it, safe to close
#     return True


def run_squish_step(test_case, step, application,):
    logging.info(f"Running {step['step_id']} on {step['gui']}: {step['instruction']}")
    
    os.makedirs(
        SCREENSHOT_DIR,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=f"{step['step_id']}_"
    ) as temporary_directory:

        result_path = os.path.join(
            temporary_directory,
            "results.json",
        )

        environment = os.environ.copy()

        environment.update(
            {
                "RESULT_PATH": result_path,
                "SCREENSHOT_DIR": SCREENSHOT_DIR,

                "TEST_CASE_ID": test_case["id"],
                "TEST_CASE_NAME": test_case["name"],

                "TARGET_GUI": step.get(
                    "gui",
                    test_case.get(
                        "gui",
                        "Unknown",
                    ),
                ),

                "TARGET_AUT": application["aut"],

                "SQUISH_STEP": step["squish_step"],
                "STEP_ID": step["step_id"],
                "STEP_NAME": step["instruction"],

                "INSTRUCTION": step.get(
                    "instruction",
                    "",
                ),

                "EXPECTED": step.get(
                    "expected",
                    "",
                ),

                "SCREENSHOT_NAME": step.get(
                    "screenshot",
                    "",
                ),
            }
        )

        command = [
            SQUISHRUNNER,
            "--host",
            application["host"],
            "--port",
            str(application["port"]),
            "--testsuite",
            application["suite"],
            "--testcase",
            application["testcase"],
        ]

        try:
            completed = subprocess.run(
                command,
                env=environment,
                capture_output=True,
                text=True,
                timeout=application.get(
                    "timeout",
                    300,
                ),
                check=False,
            )

        except subprocess.TimeoutExpired as error:
            write_squish_log(
                test_case=test_case,
                step=step,
                returncode=None,
                stdout=normalize_output(
                    error.stdout
                ),
                stderr=normalize_output(
                    error.stderr
                ),
            )

            return create_failure(
                test_case,
                step,
                (
                    "Squish step timed out after "
                    f"{application.get('timeout', 300)} "
                    "seconds."
                ),
            )

        except Exception as error:
            write_squish_log(
                test_case=test_case,
                step=step,
                returncode=None,
                stdout="",
                stderr=str(error),
            )

            return create_failure(
                test_case,
                step,
                (
                    "Framework error while running "
                    f"Squish: {error}"
                ),
            )

        write_squish_log(
            test_case=test_case,
            step=step,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

        if not os.path.exists(
            result_path
        ):
            return create_failure(
                test_case,
                step,
                (
                    "Squish did not create result.json. "
                    "Check the Squish testcase and "
                    "Squish log."
                ),
            )

        try:
            with open(
                result_path,
                "r",
                encoding="utf-8",
            ) as result_file:
                result = json.load(
                    result_file
                )

        except Exception as error:
            return create_failure(
                test_case,
                step,
                (
                    "Could not read Squish result: "
                    f"{error}"
                ),
            )

        # Temporary compatibility if a Squish test
        # still writes a one-item list.
        if isinstance(
            result,
            list,
        ):
            if len(result) != 1:
                return create_failure(
                    test_case,
                    step,
                    (
                        "Each Squish invocation must "
                        "return exactly one result."
                    ),
                )

            result = result[0]

        if not isinstance(
            result,
            dict,
        ):
            return create_failure(
                test_case,
                step,
                (
                    "Squish result must be a "
                    "JSON object."
                ),
            )

        return normalize_results(
            test_case,
            step,
            result,
        )

def normalize_results(test_case, step, result):
    status = str(
        result.get(
            "status",
            "FAIL",
        )
    ).upper()

    if status == "ABORT":
        status = "ABORTED"

    if status == "FAILED":
        status = "FAIL"

    return {
        "test_case": result.get(
            "test_case",
            test_case["id"],
        ),
        "test_name": result.get(
            "test_name",
            test_case["name"],
        ),
        "gui": result.get(
            "gui",
            step.get(
                "gui",
                test_case.get(
                    "gui",
                    "Unknown",
                ),
            ),
        ),
        "step_id": result.get(
            "step_id",
            step.get(
                "step_id",
                "UNKNOWN",
            ),
        ),
        "step_type": result.get(
            "step_type",
            "Automated",
        ),
        "instruction": result.get(
            "instruction",
            step.get(
                "instruction",
                "",
            ),
        ),
        "expected": result.get(
            "expected",
            step.get(
                "expected",
                "",
            ),
        ),
        "actual": result.get(
            "actual",
            "",
        ),
        "status": status,
        "screenshot": result.get(
            "screenshot"
        ),
        "notes": result.get(
            "notes",
            "",
        ),
        "timestamp": result.get(
            "timestamp",
            timestamp(),
        ),
    }

def create_failure(test_case, step, actual,):
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
        "actual": actual,
        "status": "FAIL",
        "screenshot": None,
        "notes": "",
        "timestamp": timestamp(),
    }


def normalize_output(output):
    if output is None:
        return ""

    if isinstance(output, bytes):
        return output.decode(
            "utf-8",
            errors="replace",
        )

    return str(output)

def write_squish_log(test_case, step, returncode, stdout, stderr):
    log_directory = os.path.dirname(
        LOG_PATH
    )

    if log_directory:
        os.makedirs(
            log_directory,
            exist_ok=True,
        )

    with open(
        LOG_PATH,
        "a",
        encoding="utf-8",
    ) as log_file:
        log_file.write(
            "\n" + "-" * 80 + "\n"
        )

        log_file.write(
            f"{timestamp()} | Squish output for "
            f"{test_case['id']} / "
            f"{step['step_id']}\n"
        )

        log_file.write(
            f"GUI: {step.get('gui', 'Unknown')}\n"
        )

        log_file.write(
            "Squish step: "
            f"{step.get('squish_step', '')}\n"
        )

        log_file.write(
            f"Return code: {returncode}\n"
        )

        log_file.write(
            "\nSTDOUT:\n"
        )

        log_file.write(
            stdout or ""
        )

        log_file.write(
            "\n\nSTDERR:\n"
        )

        log_file.write(
            stderr or ""
        )

        log_file.write(
            "\n"
        )
        