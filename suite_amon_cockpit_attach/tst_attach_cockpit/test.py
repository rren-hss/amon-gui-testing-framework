import json
import os
import time
import names

GUI_STATE_TIMEOUT_MS = 15000
SCREENSHOT_RENDER_DELAY_SECONDS = 0.5

RESULT_PATH = os.environ["RESULT_PATH"]
SCREENSHOT_DIR = os.environ["SCREENSHOT_DIR"]
TARGET_AUT = os.environ.get("TARGET_AUT", "appSurgeon")
SQUISH_STEP = os.environ["SQUISH_STEP"]
STEP_ID = os.environ["STEP_ID"]
STEP_NAME = os.environ.get("STEP_NAME", SQUISH_STEP)
TEST_CASE_ID = os.environ["TEST_CASE_ID"]
TEST_CASE_NAME = os.environ.get("TEST_CASE_NAME", "Amon Surgeon GUI Test")
TARGET_GUI = os.environ.get("TARGET_GUI", "surgeonGUI")
INSTRUCTION = os.environ.get("INSTRUCTION", "")
EXPECTED = os.environ.get("EXPECTED", "")
SCREENSHOT_NAME = os.environ.get("SCREENSHOT_NAME", "")


def current_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def write_result(status, actual, screenshot=None, notes=""):
    result = {
        "test_case": TEST_CASE_ID,
        "test_name": TEST_CASE_NAME,
        "gui": TARGET_GUI,
        "step_id": STEP_ID,
        "step_type": "Automated",
        "name": STEP_NAME,
        "instruction": INSTRUCTION,
        "expected": EXPECTED,
        "actual": actual,
        "status": status,
        "screenshot": screenshot,
        "notes": notes,
        "timestamp": current_timestamp(),
    }

    result_directory = os.path.dirname(RESULT_PATH)

    if result_directory:
        os.makedirs(result_directory, exist_ok=True)

    with open(RESULT_PATH, "w", encoding="utf-8") as result_file:
        json.dump(result, result_file, indent=2)


def capture_screenshot():
    if not SCREENSHOT_NAME:
        return None

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    screenshot_path = os.path.join(SCREENSHOT_DIR, SCREENSHOT_NAME)

    window = waitForObject(
        names.polaris_Surgeon_GUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    snooze(SCREENSHOT_RENDER_DELAY_SECONDS)

    image = object.grabScreenshot(window)
    image.save(screenshot_path)

    return screenshot_path


# --------------------------------------------------
# Surgeon GUI actions
# --------------------------------------------------

def verify_surgeon_window():
    window = waitForObject(
        names.polaris_Surgeon_GUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    if not window.visible:
        raise RuntimeError("Surgeon GUI window was not visible.")
    

def capture_current_screen():
    verify_surgeon_window()

def verify_sgui_prelogin():
    label = waitForObject(
        names.aWAITING_LOGIN_MyLabel)
    test.compare(
        label.text,
        "AWAITING LOGIN",
        "Verify sGUI displays the AWAITING LOGIN message",
    )

def verify_sgui_post_login():
    surgeon_label = waitForObject(names.surgeon_MyLabel)
    test.verify(
        surgeon_label.visible,
        "Verify sGUI Surgeon label in the top bar is visible",
    )



# Define this after all handler functions exist.
STEP_HANDLERS = {
    "surgeon_gui_window": verify_surgeon_window,
    "capture_current_screen": capture_current_screen,
    "sgui_prelogin_verify": verify_sgui_prelogin,
    "sgui_post_login": verify_sgui_post_login,

}


def main():
    screenshot = None

    try:
        test.log(f"Attaching to {TARGET_AUT}")

        attachToApplication(TARGET_AUT)

        handler = STEP_HANDLERS.get(SQUISH_STEP)

        if handler is None:
            supported_steps = ", ".join(sorted(STEP_HANDLERS))

            raise RuntimeError(
                "Unknown Surgeon Squish step "
                f"'{SQUISH_STEP}'. "
                f"Supported steps: {supported_steps}"
            )

        test.log(f"Executing Squish step: {SQUISH_STEP}")

        handler()

        screenshot = capture_screenshot()

        write_result(
            status="PASS",
            actual=f"Completed Surgeon step '{SQUISH_STEP}' successfully.",
            screenshot=screenshot,
        )

        test.passes(f"{STEP_ID} completed successfully.")

    except Exception as error:
        test.warning(f"{STEP_ID} failed: {error}")

        try:
            screenshot = capture_screenshot()
        except Exception as screenshot_error:
            test.warning(
                f"Could not capture a failure screenshot: {screenshot_error}"
            )

        # Always try to create result.json, even when
        # attachment or screenshot capture fails.
        try:
            write_result(
                status="FAIL",
                actual=str(error),
                screenshot=screenshot,
            )
        except Exception as result_error:
            test.warning(f"Could not write the step result: {result_error}")

        test.fail(str(error))
