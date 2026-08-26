import json
import os
import subprocess
import time
import names

GUI_STATE_TIMEOUT_MS = 15000
SCREENSHOT_RENDER_DELAY_SECONDS = 0.5

RESULT_PATH = os.environ["RESULT_PATH"]
SCREENSHOT_DIR = os.environ["SCREENSHOT_DIR"]
TARGET_AUT = os.environ.get("TARGET_AUT", "cart_gui")
SQUISH_STEP = os.environ["SQUISH_STEP"]
STEP_ID = os.environ["STEP_ID"]
STEP_NAME = os.environ.get("STEP_NAME", SQUISH_STEP)
TEST_CASE_ID = os.environ["TEST_CASE_ID"]
TEST_CASE_NAME = os.environ.get("TEST_CASE_NAME", "Amon Cart GUI Test")
TARGET_GUI = os.environ.get("TARGET_GUI", "cartGUI")
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
        # Only set by timer-capture steps (QA-T1139) -- see
        # capture_cgui_timer()/capture_agui_timer().
        "timer_value": timer_value,
        "capture_timestamp": capture_timestamp,
        "read_latency": read_latency,
    }

    result_directory = os.path.dirname(RESULT_PATH)

    if result_directory:
        os.makedirs(result_directory, exist_ok=True)

    with open(RESULT_PATH, "w", encoding="utf-8") as result_file:
        json.dump(result, result_file, indent=2)

def _window_object_for_aut():
    if TARGET_AUT == "assistant_gui":
        return names.polaris_aGUI_QQuickApplicationWindow
    return names.polaris_cGUI_QQuickApplicationWindow

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

    window = waitForObject(_window_object_for_aut(), GUI_STATE_TIMEOUT_MS)

    bring_to_front(window)

    image = object.grabScreenshot(window)
    image.save(screenshot_path)

    return screenshot_path
# def capture_screenshot():
#     if not SCREENSHOT_NAME:
#         return None

#     os.makedirs(SCREENSHOT_DIR, exist_ok=True)
#     screenshot_path = os.path.join(SCREENSHOT_DIR, SCREENSHOT_NAME)

#     window = waitForObject(
#         names.polaris_Surgeon_GUI_QQuickApplicationWindow,
#         GUI_STATE_TIMEOUT_MS,
#     )

#     bring_to_front(window)

#     image = object.grabScreenshot(window)
#     image.save(screenshot_path)

#     return screenshot_path

def capture_current_screen():
    if TARGET_AUT == "assistant_gui":
        verify_assistant_gui_window()
    else:
        verify_cart_gui_window()

# --------------------------------------------------
# Cart / Assistant GUI actions
# --------------------------------------------------

#Verify Polaris C Displays are on
def verify_cart_gui_window():
    window = waitForObject(
        names.polaris_cGUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    if not window.visible:
        raise RuntimeError("Cart GUI window was not visible.")

def verify_assistant_gui_window():
    window = waitForObject(
        names.polaris_aGUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    if not window.visible:
        raise RuntimeError("Assistant GUI window was not visible.")

#Prelogin status verification
def verify_agui_prelogin():
    awaiting_login_label = waitForObject(
        names.polaris_aGUI_AwaitingLoginLabel,
        GUI_STATE_TIMEOUT_MS
    )
    test.compare(
        awaiting_login_label.text,
        "AWAITING LOGIN",
        "Verify aGUI is awaiting login",
    )
    test.verify(
        awaiting_login_label.visible,
        "Verify aGUI displays the AWAITING LOGIN pre-login screen",
    )

def _dismiss_system_ready_screen():
    """cGUI can come up either on the System Ready screen (needs a tap on
    the logo to advance) or straight on the login screen, depending on
    timing right after a boot/reset -- confirmed live: a fresh reset lands
    on System Ready, and any login attempt that skips this wait/click gets
    stuck since the username field doesn't exist yet on that screen.
    """
    try:
        waitForObject(names.polaris_cGUI_logo_Image, 3000)
        test.warning("Launch Deviation: cGUI opened on the System Ready screen. Clicking on the logo to continue to login.")
        mouseClick(waitForObject(names.polaris_cGUI_logo_Image), 205, 53, Qt.LeftButton)
    except LookupError:
        test.log("System Ready screen did not appear. cGUI proceeded directly to login.")


def verify_cgui_prelogin():
    _dismiss_system_ready_screen()

    label = waitForObject(
    names.polaris_cGUI_UserLoginLabel,
    15000,
    )

    test.compare(
    label.text,
    "User login",
    "Verify cGUI displays User login",
)

#Login & post login verification
def cgui_login():
    _dismiss_system_ready_screen()

    waitForObject(names.polaris_cGUI_UserLoginLabel, 15000)

    mouseClick(
        waitForObject(names.usernameField_TextField),
        82,
        41,
        Qt.LeftButton,
    )
    type(
        waitForObject(names.usernameField_TextField),
        "user",
    )

    mouseClick(
        waitForObject(names.passwordField_TextField),
        82,
        38,
        Qt.LeftButton,
    )
    type(
        waitForObject(names.passwordField_TextField),
        "horizon",
    )

    mouseClick(
        waitForObject(names.login_MyLabel)
    )

    test.log("Submitted cGUI login credentials.")

def verify_cgui_post_login():
    cgui_login()
    
    main_label = waitForObject(names.polaris_cGUI_Main_MyLabel, GUI_STATE_TIMEOUT_MS)

    test.compare(
        main_label.text,
        "Main",
        "Verify cGUI successfully reached the Main screen after login",
    )

def verify_agui_post_login():
    surgeon_label = waitForObject(names.polaris_aGUI_Surgeon_MyLabel)

    test.verify(
        surgeon_label.visible,
        "Verify aGUI Surgeon label in top bar is visible after login",
    )

# --------------------------------------------------
# Verify Surgical Case Setup & Initialization
# --------------------------------------------------
def cart_gui_case_setup():
    mouseClick(waitForObject(names.case_Setup_Text))
    mouseClick(waitForObject(names.caseIdInput_TextField), 73, 30, Qt.LeftButton)
    type(waitForObject(names.caseIdInput_TextField), "123")
    mouseClick(waitForObject(names.surgeonDropdown_ComboBox), 205, 28, Qt.LeftButton)
    mouseClick(waitForObject(names.dr_Smith_ItemDelegate), 129, 28, Qt.LeftButton)
    mouseClick(waitForObject(names.oS_Text))
    mouseClick(waitForObject(names.move_to_Draping_Text))
    test.log("Entered Case Setup details ")

def verify_cart_case_setup():
    cart_gui_case_setup()
    snooze(1)
    ready_label = waitForObject(
        names.the_system_is_in_the_Draping_position_Before_scrubbing_in_complete_the_following_steps_MyLabel,
        GUI_STATE_TIMEOUT_MS
    )
    
    test.compare(
        ready_label.text,
        "The system is in the Draping position. Before scrubbing in, complete the following steps:",
        "Verify Cart GUI indicates the system is ready for draping",
    )

def agui_case_setup_verify():
    case_label = waitForObject(
        names.polaris_aGUI_Case_123_MyLabel, GUI_STATE_TIMEOUT_MS
    )
    test.compare(
        case_label.text,
        "Case: 123",
        "Verify Assistant GUI displays the correct case ID",
    )

    laterality_label = waitForObject(
        names.polaris_aGUI_Eye_Laterality_OS_MyLabel, GUI_STATE_TIMEOUT_MS
    )
    test.compare(
        laterality_label.text,
        "Eye Laterality: OS",
        "Verify Assistant GUI displays the correct eye laterality",
    )

    surgeon_label = waitForObject(
        names.polaris_aGUI_Dr_Smith_MyLabel, GUI_STATE_TIMEOUT_MS
    )
    test.compare(
        surgeon_label.text,
        "Dr. Smith",
        "Verify Assistant GUI displays the correct surgeon",
    )

    draping_instructions = waitForObject(
        names.polaris_aGUI_DrapingInstructions, GUI_STATE_TIMEOUT_MS
    )


# --------------------------------------------------
# Surgical Case Flow Verification Test
# --------------------------------------------------

def agui_init_case_button():
    initialize_case_button = waitForObject(
        names.polaris_aGUI_Initialize_Case_Text,
        GUI_STATE_TIMEOUT_MS
    )

def cgui_ready_draping():
    ready_label = waitForObject(
            names.the_system_is_in_the_Draping_position_Before_scrubbing_in_complete_the_following_steps_MyLabel,
            GUI_STATE_TIMEOUT_MS
        )

def agui_click_ini_case():
    mouseClick(waitForObject(names.polaris_aGUI_Initialize_Case_Text))

def verify_cgui_waiting_for_surgeon():
    label = waitForObject(
        names.ready_for_Surgery_Waiting_for_surgeon_to_start_MyLabel,
        GUI_STATE_TIMEOUT_MS
    )
    test.compare(
        label.text,
        "Ready for Surgery. Waiting for surgeon to start.",
        "Verify that cgui says that controlled is passed on to surgeon"
    )

def agui_main_screen():
    label = waitForObject(
        names.polaris_aGUI_Assistant_Active_MyLabel,
        GUI_STATE_TIMEOUT_MS
    )

def cgui_active_case():
    label = waitForObject(
        names.case_is_Active_MyLabel,
        GUI_STATE_TIMEOUT_MS
    )

    label_2 = waitForObject(
        names.control_assigned_to_Surgeon_and_Assistant_GUIs_MyLabel,
        GUI_STATE_TIMEOUT_MS
    )

def agui_confirmations_side_inc():
    mouseClick(waitForObject(names.polaris_aGUI_Confirm_Text_2))
    mouseClick(waitForObject(names.polaris_aGUI_Confirm_Text))

    surgeon_active_label = waitForObject(
        names.polaris_aGUI_Surgeon_Active_MyLabel,
        GUI_STATE_TIMEOUT_MS
    )

def preflight_attach():
    # No-op: main() already called attachToApplication(TARGET_AUT) before
    # dispatching here, so reaching this handler proves the AUT is attachable.
    pass

def verify_agui_viscoat_step():
    viscoat_rectangle = waitForObject(names.viscoat_Rectangle)

    test.verify(
        viscoat_rectangle.visible,
        "Verify Viscoat is displayed as a Rectangle"
    )

    confirm_text = waitForObject(names.polaris_aGUI_Confirm_Text)
    confirm_button = confirm_text.parent

    test.verify(
        confirm_button.enabled == True,
        "Verify Confirm button is pressable"
    )

def verify_agui_telecentric_camera_feed():
    window = waitForObject(
        names.polaris_aGUI_QQuickApplicationWindow,
        GUI_STATE_TIMEOUT_MS,
    )

    bring_to_front(window)

    video_player = waitForObject(
        names.polaris_aGUI_videoPlayer_GstStreamPlayer,
        GUI_STATE_TIMEOUT_MS,
    )

    test.verify(
        video_player.visible,
        "Verify telecentric video player is visible",
    )

    test.verify(
        video_player.enabled,
        "Verify telecentric video player is enabled",
    )

    test.verify(
        video_player.width > 0 and video_player.height > 0,
        "Verify telecentric video player has a valid display area",
    )

    test.verify(
        getattr(video_player, "connectedOnce", False),
        "Verify telecentric video player has connected to a video source",
    )

    video_sink = waitForObject(
        names.polaris_aGUI_videoSink_Qt6GLVideoItem,
        GUI_STATE_TIMEOUT_MS,
    )

    test.verify(
        video_sink.visible,
        "Verify telecentric video sink is visible",
    )

    test.verify(
        video_sink.width > 0 and video_sink.height > 0,
        "Verify telecentric video sink has a valid display area",
    )

# --------------------------------------------------
# Surgical timer sync check (QA-T1139)
# --------------------------------------------------
def _capture_timer(timer_names_entry):
    """Waits for the timer value label (matched directly by shape via
    RegularExpression in the object map -- no anchor/sibling lookup
    needed) and reads its text.

    Reading `.text` isn't local: it's an IPC round-trip to the Squish hook
    inside the AUT process, so it takes real (if usually small) time. A
    single time.time() taken right after the read would silently bias
    every capture_timestamp slightly late by however long that round-trip
    took. Bracketing the read with a timestamp before and after, and using
    the midpoint, turns that unknown bias into a bounded, roughly-centered
    estimate -- and read_latency (the bracket width) is returned too, so
    an unusually slow read is visible in the report rather than silently
    absorbed into the comparison's tolerance.
    """
    value_label = waitForObject(timer_names_entry, GUI_STATE_TIMEOUT_MS)

    before = time.time()
    text = str(value_label.text)
    after = time.time()

    capture_time = (before + after) / 2
    read_latency = after - before

    return text, capture_time, read_latency


def capture_cgui_timer():
    text, capture_time, read_latency = _capture_timer(names.cGUI_timer_MyLabel)

    return {
        "timer_value": text,
        "capture_timestamp": capture_time,
        "read_latency": read_latency,
        "actual": (
            f"Captured Cart GUI surgical timer reading: {text} "
            f"(read took {read_latency * 1000:.1f} ms)"
        ),
    }


def capture_agui_timer():
    text, capture_time, read_latency = _capture_timer(
        names.polaris_aGUI_timer_MyLabel
    )

    return {
        "timer_value": text,
        "capture_timestamp": capture_time,
        "read_latency": read_latency,
        "actual": (
            f"Captured Assistant GUI surgical timer reading: {text} "
            f"(read took {read_latency * 1000:.1f} ms)"
        ),
    }

# Define this after all handler functions exist.
STEP_HANDLERS = {

    "cart_gui_window": verify_cart_gui_window,
    "assistant_gui_window": verify_assistant_gui_window,
    "capture_current_screen": capture_current_screen,
    "agui_prelogin_verify": verify_agui_prelogin,
    "cgui_prelogin_verify": verify_cgui_prelogin,
    "cart_gui_login": verify_cgui_post_login,
    "agui_post_login": verify_agui_post_login,
    "verify_cart_case_setup": verify_cart_case_setup,
    "agui_case_setup_verify": agui_case_setup_verify,
    "verify_agui_ini_case": agui_init_case_button,
    "verify_cgui_draping_ready": cgui_ready_draping,
    "click_agui_ini_case": agui_click_ini_case,
    "verify_cgui_surgeon_control": verify_cgui_waiting_for_surgeon,
    
    "verify_agui_main_screen": agui_main_screen,
    "verify_cgui_active_case": cgui_active_case,
    "agui_confirmations_side_inc": agui_confirmations_side_inc,
    "verify_agui_viscoat_step": verify_agui_viscoat_step,
    "preflight_attach": preflight_attach,
    "verify_agui_telecentric_camera_feed": verify_agui_telecentric_camera_feed,
    "capture_cgui_timer": capture_cgui_timer,
    "capture_agui_timer": capture_agui_timer,
}




def main():
    screenshot = None
    app_context = None
    testSettings.throwOnFailure = True

    try:
        test.log(f"Attaching to {TARGET_AUT}")
        app_context = attachToApplication(TARGET_AUT)

        handler = STEP_HANDLERS.get(SQUISH_STEP)

        if handler is None:
            supported_steps = ", ".join(sorted(STEP_HANDLERS))
            raise RuntimeError(
                f"Unknown Squish step '{SQUISH_STEP}'. "
                f"Supported steps: {supported_steps}"
            )

        test.log(f"Executing Squish step: {SQUISH_STEP}")
        handler_result = handler()

        screenshot = capture_screenshot()

        # A handler may optionally return a dict of extra write_result()
        # kwargs (e.g. timer_value/capture_timestamp for QA-T1139's timer
        # capture steps, or a more specific "actual" message) -- every
        # other handler returns None and this is a no-op for them.
        extra_fields = dict(handler_result) if isinstance(handler_result, dict) else {}
        actual = extra_fields.pop(
            "actual",
            f"Completed Squish step '{SQUISH_STEP}' successfully.",
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

        try:
            write_result(
                status="FAIL",
                actual=str(error),
                screenshot=screenshot,
            )
        except Exception as result_error:
            test.warning(f"Could not write the step result: {result_error}")

        test.fail(str(error))

    finally:
        if app_context is not None:
            try:
                app_context.detach()
                test.log(f"Detached from {TARGET_AUT}")
            except Exception as detach_error:
                test.warning(
                    f"Could not detach from {TARGET_AUT}: {detach_error}"
                )

