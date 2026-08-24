import logging
import os
import subprocess

from config import FRAMEWORK_ROOT

RESET_SCRIPT_PATH = FRAMEWORK_ROOT / "reset_surgical_sequence.sh"


def attempt_soft_reset(system="amon"):
    """Graceful, Squish-driven reset (e.g. logging out through the GUI back
    to the pre-login baseline) tried before falling back to the hard reset.

    Not implemented yet - always returns False, which sends
    return_to_baseline() straight to the hard reset below.
    """
    logging.info("Soft reset is not implemented yet - skipping to hard reset.")
    return False


def hard_reset(system="amon"):
    """Hard-resets the GUIs and system_manager (or their Docker
    equivalents, auto-detected by the script itself) back to a known
    baseline via reset_surgical_sequence.sh.

    Runs with inherited stdio rather than capturing output: the script
    prompts for a y/N confirmation before touching anything, and in
    physical mode reads SUDO_PASSWORD from the environment, so this needs
    to be run interactively, not silently in the background.

    Returns True if the reset succeeded, False otherwise.
    """
    logging.info("Hard-resetting via %s", RESET_SCRIPT_PATH)

    completed = subprocess.run(
        [str(RESET_SCRIPT_PATH), system],
        env=os.environ.copy(),
    )

    if completed.returncode != 0:
        logging.error(
            "hard_reset failed (exit code %s).",
            completed.returncode,
        )
        return False

    logging.info("Hard reset succeeded.")
    return True


def return_to_baseline(system="amon"):
    """Returns the GUIs/system_manager to a known baseline: tries a soft,
    Squish-driven reset first, falling back to the hard reset only if the
    soft reset doesn't work (or isn't implemented yet).

    Returns True if either reset succeeded, False otherwise.
    """
    if attempt_soft_reset(system):
        logging.info("Returned to baseline via soft reset.")
        return True

    return hard_reset(system)
