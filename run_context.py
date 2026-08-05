from datetime import datetime
from pathlib import Path
import secrets

from config import OUTPUT_ROOT

def _random_token(length=6):
    return secrets.token_hex(length)[:length]

RUN_STARTED = datetime.now()

RUN_ID = (
    f"test_run_"
    f"{RUN_STARTED:%Y-%m-%d_%H%M%S}_"
    f"{_random_token()}"
)

RUN_DIR = Path(OUTPUT_ROOT) / RUN_ID
REPORT_DIR = RUN_DIR / "reports"
SCREENSHOT_DIR = RUN_DIR / "screenshots"
LOG_PATH = RUN_DIR / "run.log"

def initialize_run_directories():
    for path in (
        RUN_DIR,
        REPORT_DIR,
        SCREENSHOT_DIR,
    ):
        path.mkdir(
            parents=True,
            exist_ok=True,
        )


def unique_artifact_name(
    test_id,
    suffix="",
    extension="html",
):
    safe_id = "".join(
        character
        if character.isalnum()
        or character in "-_"
        else "_"
        for character in str(test_id)
    )

    now = datetime.now()

    return (
        f"{safe_id}_"
        f"{now:%Y-%m-%d}_"
        f"{now:%H%M%S}_"
        f"{_random_token()}"
        f"{suffix}."
        f"{extension.lstrip('.')}"
    )