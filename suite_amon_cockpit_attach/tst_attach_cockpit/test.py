import json
import os
import subprocess
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


def write_result(
    status,
    actual,
    screenshot=None,
    notes="",
    timer_value=None,
    capture_timestamp=None,
    read_latency=None,
):
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
        # Only set by the timer-capture step (QA-T1139) -- see
        # capture_sgui_timer().
        "timer_value": timer_value,
        "capture_timestamp": capture_timestamp,
        "read_latency": read_latency,
    }

    result_directory = os.path.dirname(RESULT_PATH)

    if result_directory:
        os.makedirs(result_directory, exist_ok=True)

    with open(RESULT_PATH, "w", encoding="utf-8") as result_file:
        json.dump(result, result_file, indent=2)


def bring_to_front(window):
    # Qt's own raise()/requestActivate() succeed without error but are
    # silently ignored by GNOME/Mutter's focus-stealing prevention on the
    # host (confirmed live on 2026-08-24 -- DISPLAY is shared with the host
    # via the docker-compose bind mount, so Mutter, not a containerized
    # Openbox, is what actually controls window stacking here). wmctrl
    # sends an EWMH _NET_ACTIVE_WINDOW client message, which Mutter treats
    # as a legitimate external request (like a taskbar click) rather than
    # the app self-raising, so it actually works where the raw Qt call
    # doesn't. This script runs on the host (squishrunner is a host
    # binary), so wmctrl is directly callable here.
    # window.title comes back as a Squish "QString" wrapper, not a native
    # Python str -- confirmed live on 2026-08-24 (passing it straight to
    # subprocess/str-introspection broke with "'QString' Squish object has
    # no attribute '__class__'"). str() it immediately so everything below
    # deals with a real Python string.
    title = None
    try:
        title = str(window.title)
    except Exception:
        pass

    raised_via_wmctrl = False
    if title:
        try:
            completed = subprocess.run(
                ["wmctrl", "-a", title],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raised_via_wmctrl = completed.returncode == 0
        except Exception as error:
            test.warning(f"wmctrl failed to raise window '{title}': {error}")

    if not raised_via_wmctrl:
        # Fallback for when wmctrl isn't installed -- "raise" is a Python
        # keyword, so QWindow.raise() must be invoked via getattr. Best
        # effort: an overlapping window shouldn't fail the step, just make
        # its screenshot unreliable.
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
    surgeon_label = waitForObject(names.surgeon_MyLabel, GUI_STATE_TIMEOUT_MS)
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

def verify_sgui_oct_camera_feed():
    _bring_surgeon_window_to_front()

    oct_player = waitForObject(
        names.polaris_sGUI_octPlayer_GstStreamPlayer,
        GUI_STATE_TIMEOUT_MS,
    )

    _verify_stream_player(oct_player, "OCT camera feed")

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

# --------------------------------------------------
# Surgical timer sync check (QA-T1139)
# --------------------------------------------------
def capture_sgui_timer():
    # Matched directly by shape via RegularExpression in the object map
    # (names.sGUI_timer_MyLabel) -- no anchor/sibling lookup needed.
    #
    # Bracket the read with timestamps before/after rather than taking a
    # single one afterward: reading .text is an IPC round-trip to the
    # Squish hook inside the AUT, not a local operation, so a single
    # post-read timestamp would silently bias capture_timestamp late by
    # however long that round-trip took. The midpoint centers the
    # estimate; read_latency (the bracket width) is reported too, so an
    # unusually slow read is visible rather than silently absorbed into
    # the comparison's tolerance. See the fuller comment on
    # suite_amon_cart_attach/tst_attach_cart/test.py's _capture_timer().
    value_label = waitForObject(names.sGUI_timer_MyLabel, GUI_STATE_TIMEOUT_MS)

    before = time.time()
    text = str(value_label.text)
    after = time.time()

    capture_time = (before + after) / 2
    read_latency = after - before

    return {
        "timer_value": text,
        "capture_timestamp": capture_time,
        "read_latency": read_latency,
        "actual": (
            f"Captured Surgeon GUI surgical timer reading: {text} "
            f"(read took {read_latency * 1000:.1f} ms)"
        ),
    }

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
    "verify_sgui_oct_camera_feed": verify_sgui_oct_camera_feed,
    "verify_sgui_wide_camera_feed": verify_sgui_wide_camera_feed,
    "verify_sgui_side_camera_left_feed": verify_sgui_side_camera_left_feed,
    "verify_sgui_side_camera_right_feed": verify_sgui_side_camera_right_feed,
    "preflight_attach": preflight_attach,
    "capture_sgui_timer": capture_sgui_timer,
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

        handler_result = handler()

        screenshot = capture_screenshot()

        # A handler may optionally return a dict of extra write_result()
        # kwargs (e.g. timer_value/capture_timestamp for QA-T1139's timer
        # capture step, or a more specific "actual" message) -- every
        # other handler returns None and this is a no-op for them.
        extra_fields = dict(handler_result) if isinstance(handler_result, dict) else {}
        actual = extra_fields.pop(
            "actual",
            f"Completed Surgeon step '{SQUISH_STEP}' successfully.",
        )

        write_result(
            status="PASS",
            actual=actual,
            screenshot=screenshot,
            **extra_fields,
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
