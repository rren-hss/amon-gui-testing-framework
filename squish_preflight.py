import logging
import socket

from squish_runner import run_squish_step
from step_executor import resolve_application

SERVER_CHECK_TIMEOUT_SECONDS = 5
ATTACH_CHECK_TIMEOUT_SECONDS = 30


def check_server_reachable(host, port, timeout=SERVER_CHECK_TIMEOUT_SECONDS):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_aut_attachable(gui_name, application):
    preflight_case = {
        "id": "PREFLIGHT",
        "name": f"Squish Preflight - {gui_name}",
    }

    preflight_step = {
        "step_id": "PREFLIGHT",
        "gui": gui_name,
        "squish_step": "preflight_attach",
        "instruction": f"Attach to '{application['aut']}' to confirm it is running.",
        "expected": f"'{application['aut']}' is attachable.",
    }

    preflight_application = {
        **application,
        "timeout": ATTACH_CHECK_TIMEOUT_SECONDS,
    }

    result = run_squish_step(
        preflight_case,
        preflight_step,
        preflight_application,
    )

    return result["status"] == "PASS", result.get("actual", "")


def guis_used_by(test_cases):
    """Resolves the distinct (gui_name -> application config) pairs used by
    every "auto" step across the given test cases, in first-seen order."""
    applications = {}

    for test_case in test_cases:
        for step in test_case.get("steps", []):
            if str(step.get("type", "")).lower() != "auto":
                continue

            gui_name = step.get("gui", test_case.get("gui"))

            if gui_name in applications:
                continue

            applications[gui_name] = resolve_application(test_case, step)

    return applications


def run_preflight(test_cases):
    """Checks, for every GUI referenced by an "auto" step in test_cases,
    that its Squish Server is reachable and its AUT is attachable.

    Returns a list of (gui_name, reason) failures - empty if everything
    checked out.
    """
    failures = []

    for gui_name, application in guis_used_by(test_cases).items():
        host = application["host"]
        port = application["port"]

        logging.info(
            "Squish preflight: checking %s Squish Server at %s:%s",
            gui_name, host, port,
        )

        if not check_server_reachable(host, port):
            reason = f"Squish Server unreachable at {host}:{port}."
            logging.error("Squish preflight FAILED for %s: %s", gui_name, reason)
            failures.append((gui_name, reason))
            continue

        logging.info(
            "Squish preflight: attaching to '%s' for %s",
            application["aut"], gui_name,
        )

        attachable, reason = check_aut_attachable(gui_name, application)

        if attachable:
            logging.info(
                "Squish preflight OK for %s ('%s' is attachable).",
                gui_name, application["aut"],
            )
        else:
            logging.error(
                "Squish preflight FAILED for %s: could not attach to '%s' (%s)",
                gui_name, application["aut"], reason,
            )
            failures.append((gui_name, reason))

    return failures
