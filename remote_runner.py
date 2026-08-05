import getpass
import re

import paramiko

from config import (
    SSH_CONNECT_TIMEOUT,
    SSH_USER,
)
from utils import timestamp


_SSH_PASSWORD = None


BOOTCHECK_ROW_PATTERN = re.compile(
    r"^(?P<check_id>\d+)_(?P<check_name>.*?)"
    r"\s+\[(?P<status>PASS|WARN|FAIL)\]"
    r"(?:\s+(?P<details>.*))?$",
    flags=re.MULTILINE,
)


def get_ssh_password():
    global _SSH_PASSWORD

    if _SSH_PASSWORD is None:
        _SSH_PASSWORD = getpass.getpass(
            f"Enter SSH password for {SSH_USER}: "
        )

    return _SSH_PASSWORD


def parse_bootcheck_output(
    output,
    exit_code,
):
    checks = []

    for match in BOOTCHECK_ROW_PATTERN.finditer(output):
        checks.append(
            {
                "id": match.group("check_id"),
                "name": match.group("check_name").strip(),
                "status": match.group("status"),
                "details": (
                    match.group("details") or ""
                ).strip(),
            }
        )

    total_failures_match = re.search(
        r"Total failures:\s*(\d+)",
        output,
        flags=re.IGNORECASE,
    )

    total_failures = None

    if total_failures_match:
        total_failures = int(
            total_failures_match.group(1)
        )

    pass_count = sum(
        check["status"] == "PASS"
        for check in checks
    )

    warn_count = sum(
        check["status"] == "WARN"
        for check in checks
    )

    failed_modules = sum(
        check["status"] == "FAIL"
        for check in checks
    )

    if exit_code != 0:
        status = "FAIL"
        reason = (
            f"Boot check command exited with code "
            f"{exit_code}."
        )

    elif total_failures is None:
        status = "FAIL"
        reason = (
            "Boot check ran, but the final failure "
            "count could not be parsed."
        )

    elif total_failures > 0:
        status = "FAIL"
        reason = (
            f"Boot check completed with "
            f"{total_failures} reported failure(s)."
        )

    else:
        status = "PASS"
        reason = (
            "Boot check completed with zero failures."
        )

    return {
        "status": status,
        "reason": reason,
        "checks": checks,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "failed_modules": failed_modules,
        "total_failures": total_failures,
    }


def format_bootcheck_summary(parsed):
    lines = [
        parsed["reason"],
        "",
        f"Passed modules: {parsed['pass_count']}",
        f"Warning modules: {parsed['warn_count']}",
        f"Failed modules: {parsed['failed_modules']}",
        (
            "Boot-check reported failures: "
            f"{parsed['total_failures']}"
        ),
    ]

    failed_checks = [
        check
        for check in parsed["checks"]
        if check["status"] == "FAIL"
    ]

    warning_checks = [
        check
        for check in parsed["checks"]
        if check["status"] == "WARN"
    ]

    if failed_checks:
        lines.extend(
            [
                "",
                "Failed checks:",
            ]
        )

        for check in failed_checks:
            lines.append(
                f"- {check['id']}_{check['name']}: "
                f"{check['details']}"
            )

    if warning_checks:
        lines.extend(
            [
                "",
                "Warnings:",
            ]
        )

        for check in warning_checks:
            lines.append(
                f"- {check['id']}_{check['name']}: "
                f"{check['details']}"
            )

    return "\n".join(lines)


def terminal_failure(
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
        "step_id": step.get(
            "step_id",
            "UNKNOWN",
        ),
        "step_type": "Terminal / SSH",
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


def run_remote_step(
    test_case,
    step,
):
    host = step.get(
        "host",
        test_case.get("host"),
    )

    remote_command = step.get("command")

    username = step.get(
        "username",
        test_case.get(
            "username",
            SSH_USER,
        ),
    )

    timeout = int(
        step.get(
            "timeout",
            test_case.get(
                "timeout",
                300,
            ),
        )
    )

    if not host or not remote_command:
        return terminal_failure(
            test_case,
            step,
            (
                "Terminal step requires both "
                "'host' and 'command'."
            ),
        )

    password = get_ssh_password()

    client = paramiko.SSHClient()

    client.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    try:
        client.connect(
            hostname=host,
            username=username,
            password=password,
            timeout=SSH_CONNECT_TIMEOUT,
            auth_timeout=SSH_CONNECT_TIMEOUT,
            banner_timeout=SSH_CONNECT_TIMEOUT,
            look_for_keys=False,
            allow_agent=False,
        )

        stdin, stdout, stderr = client.exec_command(
            remote_command,
            timeout=timeout,
        )

        exit_code = stdout.channel.recv_exit_status()

        stdout_text = stdout.read().decode(
            "utf-8",
            errors="replace",
        )

        stderr_text = stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        output = "\n".join(
            filter(
                None,
                [
                    stdout_text.strip(),
                    stderr_text.strip(),
                ],
            )
        ).strip()

        if not output:
            output = "No terminal output."

    except paramiko.AuthenticationException:
        return terminal_failure(
            test_case,
            step,
            (
                f"SSH authentication failed for "
                f"{username}@{host}."
            ),
        )

    except paramiko.SSHException as error:
        return terminal_failure(
            test_case,
            step,
            f"SSH error for {host}: {error}",
        )

    except TimeoutError:
        return terminal_failure(
            test_case,
            step,
            (
                f"SSH connection or command timed out "
                f"for {host}."
            ),
        )

    except Exception as error:
        return terminal_failure(
            test_case,
            step,
            (
                f"Unexpected SSH execution error "
                f"for {host}: {error}"
            ),
        )

    finally:
        client.close()

    parser_type = (
        step.get(
            "parser",
            {},
        ).get("type")
    )

    if parser_type == "bootcheck":
        parsed = parse_bootcheck_output(
            output,
            exit_code,
        )

        status = parsed["status"]
        summary = format_bootcheck_summary(
            parsed
        )

    else:
        status = (
            "PASS"
            if exit_code == 0
            else "FAIL"
        )

        summary = (
            f"Remote command exited with code "
            f"{exit_code}."
        )

    return {
        "test_case": test_case["id"],
        "test_name": test_case["name"],
        "gui": step.get(
            "gui",
            test_case.get(
                "gui",
                host,
            ),
        ),
        "step_id": step.get(
            "step_id",
            "UNKNOWN",
        ),
        "step_type": "Terminal / SSH",
        "instruction": step.get(
            "instruction",
            remote_command,
        ),
        "expected": step.get(
            "expected",
            (
                "Remote command completes "
                "successfully."
            ),
        ),
        "actual": (
            f"{summary}\n\n"
            f"Host: {host}\n"
            f"Command: {remote_command}\n"
            f"Exit code: {exit_code}\n\n"
            f"Complete terminal output:\n"
            f"{output}"
        ),
        "status": status,
        "screenshot": None,
        "notes": "",
        "timestamp": timestamp(),
    }