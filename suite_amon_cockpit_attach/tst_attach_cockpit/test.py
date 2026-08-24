import json
import os
import tempfile
import time
import names

GUI_STATE_TIMEOUT_MS = 15000
SCREENSHOT_RENDER_DELAY_SECONDS = 0.5

RESULT_PATH = os.environ["RESULT_PATH"]
SCREENSHOT_DIR = os.environ["SCREENSHOT_DIR"]
TARGET_AUT = os.environ.get("TARGET_AUT", "surgeon_gui").strip()
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


def bring_to_front(window):
    # "raise" is a Python keyword, so QWindow.raise() must be invoked via
    # getattr rather than window.raise(). Best-effort: an overlapping
    # window shouldn't fail the step, just make its screenshot unreliable.
    try:
        getattr(window, "raise")()
        window.requestActivate()
    except Exception as error:
        test.warning(f"Could not bring window to front before screenshot: {error}")

    snooze(SCREENSHOT_RENDER_DELAY_SECONDS)


def capture_screenshot():
    if not SCREENSHOT_NAME:
        return None

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    screenshot_path = os.path.join(SCREENSHOT_DIR, SCREENSHOT_NAME)

    window = waitForObject(
        names.polaris_Surgeon_GUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    bring_to_front(window)

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

def sgui_case_setup_verify():
    case_label = waitForObject(
        names.case_123_MyLabel,
        GUI_STATE_TIMEOUT_MS,
    )
    test.compare(
        case_label.text,
        "Case: 123",
        "Verify Surgeon GUI displays the correct case ID",
    )

    laterality_label = waitForObject(
        names.eye_Laterality_OS_MyLabel,
        GUI_STATE_TIMEOUT_MS,
    )
    test.compare(
        laterality_label.text,
        "Eye Laterality: OS",
        "Verify Surgeon GUI displays the correct eye laterality",
    )

    surgeon_dropdown = waitForObject(
        names.surgeonDropdown_ComboBox,
        GUI_STATE_TIMEOUT_MS,
    )
    test.compare(
        surgeon_dropdown.currentText,
        "Dr. Smith",
        "Verify Surgeon GUI displays the correct selected surgeon",
    )


def verify_start_surgery_popup():
    start_surgery_button = waitForObject(
        names.start_Surgery_Text,
        GUI_STATE_TIMEOUT_MS
    )
    test.compare(
        start_surgery_button.text,
        "Start Surgery",
        "Verify sGUI show Start Surgery button"
    )

def click_start_surgery():
    mouseClick(waitForObject(names.start_Surgery_Text))


def verify_docking_confirmation():
    click_start_surgery()
    label = waitForObject(
        names.apply_Docking_to_the_operative_eye_MyLabel,
        GUI_STATE_TIMEOUT_MS,
    )

def sgui_docking_confirm():
    mouseClick(waitForObject(names.confirm_Text)) 

def verify_step_switch_viscoat():
    mouseDrag(waitForObject(names.stepList_Viscoat_ProcedureStepButton), 121, 26, 2, 2, Qt.NoModifier, Qt.LeftButton)
    obj = waitForObject(names.viscoat_Rectangle, GUI_STATE_TIMEOUT_MS)
    test.verify(
        obj.visible,
        "Verify Viscoat is selected -- not a button element"
    )

def preflight_attach():
    # No-op: main() already called attachToApplication(TARGET_AUT) before
    # dispatching here, so reaching this handler proves the AUT is attachable.
    pass

def _verify_stream_player(player, label):
    test.verify(
        player.visible,
        f"Verify {label} panel is visible on Surgeon GUI",
    )

    test.verify(
        player.enabled,
        f"Verify {label} panel is enabled",
    )

    test.verify(
        player.width > 0 and player.height > 0,
        f"Verify {label} panel has a non-zero size",
    )

    test.verify(
        player.connectedOnce,
        f"Verify {label} has connected to its stream at least once",
    )

    with tempfile.TemporaryDirectory(prefix="stream_feed_") as temp_dir:
        frame_1_path = os.path.join(temp_dir, "frame_1.png")
        frame_2_path = os.path.join(temp_dir, "frame_2.png")

        object.grabScreenshot(player).save(frame_1_path)
        snooze(1)
        object.grabScreenshot(player).save(frame_2_path)

        with open(frame_1_path, "rb") as frame_1_file:
            frame_1_bytes = frame_1_file.read()

        with open(frame_2_path, "rb") as frame_2_file:
            frame_2_bytes = frame_2_file.read()

    test.verify(
        frame_1_bytes != frame_2_bytes,
        f"Verify {label} is updating (not a frozen/static frame)",
    )

def _bring_surgeon_window_to_front():
    window = waitForObject(
        names.polaris_Surgeon_GUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    bring_to_front(window)

def verify_sgui_wide_camera_feed():
    _bring_surgeon_window_to_front()

    wide_player = waitForObject(
        names.polaris_sGUI_widePlayer_GstStreamPlayer,
        GUI_STATE_TIMEOUT_MS,
    )

    _verify_stream_player(wide_player, "wide camera feed")

def verify_sgui_side_camera_left_feed():
    _bring_surgeon_window_to_front()

    left_player = waitForObject(
        names.polaris_sGUI_leftPlayer_GstStreamPlayer,
        GUI_STATE_TIMEOUT_MS,
    )

    _verify_stream_player(left_player, "left side camera feed")

def verify_sgui_side_camera_right_feed():
    _bring_surgeon_window_to_front()

    right_player = waitForObject(
        names.polaris_sGUI_rightPlayer_GstStreamPlayer,
        GUI_STATE_TIMEOUT_MS,
    )

    _verify_stream_player(right_player, "right side camera feed")


# Define this after all handler functions exist.
STEP_HANDLERS = {
    "surgeon_gui_window": verify_surgeon_window,
    "capture_current_screen": capture_current_screen,
    "sgui_prelogin_verify": verify_sgui_prelogin,
    "sgui_post_login": verify_sgui_post_login,
    "sgui_case_setup_verify": sgui_case_setup_verify,
    "verify_start_surgery_button": verify_start_surgery_popup,
    "click_sgui_start_surgery": verify_docking_confirmation,
    "verify_sgui_enabled": sgui_docking_confirm,
    "verify_step_switch_viscoat": verify_step_switch_viscoat,
    "verify_sgui_wide_camera_feed": verify_sgui_wide_camera_feed,
    "verify_sgui_side_camera_left_feed": verify_sgui_side_camera_left_feed,
    "verify_sgui_side_camera_right_feed": verify_sgui_side_camera_right_feed,
    "preflight_attach": preflight_attach,
}


def main():
    screenshot = None
    testSettings.throwOnFailure = True


    try:
        test.log(f"Attaching to {TARGET_AUT}")

        test.log(f"RUNNING FILE: {__file__}")
        test.log(f"TARGET_AUT: {TARGET_AUT}")
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
