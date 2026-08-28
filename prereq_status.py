"""Persisted last-known pass/fail status per test case, used to gate
test cases that declare a "requires" list of prerequisite test case IDs.

Deliberately outlives a single run (stored directly under OUTPUT_ROOT, not
inside a per-run timestamped directory): a test case run standalone via
--case still needs to know whether its prerequisites passed the last time
they ran, possibly in an earlier, separate invocation of this framework.

Tri-state model: PASS, FAIL, or absent ("not tested"). Absent does not
block -- only a known FAIL does. This means running an isolated case that
has never had its prerequisites tested is allowed to proceed (the operator
may have set up the right state by hand), while a case whose prerequisite
is on record as having actually failed gets blocked automatically.
"""

import json
import logging

from config import OUTPUT_ROOT
from utils import timestamp

STATUS_PATH = OUTPUT_ROOT / "prereq_status.json"


def _load():
    if not STATUS_PATH.exists():
        return {}

    try:
        with STATUS_PATH.open("r", encoding="utf-8") as status_file:
            return json.load(status_file)
    except (OSError, json.JSONDecodeError) as error:
        logging.warning(
            "Could not read %s (%s) -- treating all prereqs as not tested.",
            STATUS_PATH,
            error,
        )
        return {}


def _case_passed(case_results):
    """A case "passes" for prereq-gating purposes if every one of its
    step results is PASS or WARN -- FAIL/ABORTED/BLOCKED (from any step)
    count as an overall failure. A case with no results at all (e.g. it
    was itself blocked before any step ran) is not a pass.
    """

    if not case_results:
        return False

    for result in case_results:
        status = str(result.get("status", "")).strip().upper()
        if status.startswith("FAIL") or status.startswith("ABORT") or status.startswith("BLOCK"):
            return False

    return True


def record_result(test_case_id, case_results, run_id=None):
    """Records this test case's latest result, overwriting any previous
    entry for the same ID -- this file tracks "last known status", not a
    history log.
    """

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    statuses = _load()
    statuses[test_case_id] = {
        "status": "PASS" if _case_passed(case_results) else "FAIL",
        "timestamp": timestamp(),
        "run_id": run_id,
    }

    try:
        with STATUS_PATH.open("w", encoding="utf-8") as status_file:
            json.dump(statuses, status_file, indent=2)
    except OSError as error:
        logging.warning(
            "Could not write %s (%s) -- prereq status for %s not persisted.",
            STATUS_PATH,
            error,
            test_case_id,
        )


def get_status(test_case_id):
    """Returns "PASS", "FAIL", or None (not tested) for the given test
    case's last recorded result.
    """

    return _load().get(test_case_id, {}).get("status")


def blocking_prereqs(required_ids):
    """Returns the subset of required_ids whose last known status is an
    explicit FAIL. An empty list means nothing blocks this case --
    every requirement either passed or was never tested.
    """

    return [
        required_id
        for required_id in required_ids or []
        if get_status(required_id) == "FAIL"
    ]
