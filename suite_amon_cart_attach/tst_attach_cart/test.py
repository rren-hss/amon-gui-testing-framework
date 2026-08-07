import json
import os
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

def _window_object_for_aut():
    if TARGET_AUT == "assistant_gui":
        return names.polaris_aGUI_QQuickApplicationWindow
    return names.polaris_cGUI_QQuickApplicationWindow

def capture_screenshot():
    if not SCREENSHOT_NAME:
        return None

    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    screenshot_path = os.path.join(SCREENSHOT_DIR, SCREENSHOT_NAME)

    window = waitForObject(_window_object_for_aut(), GUI_STATE_TIMEOUT_MS)

    snooze(SCREENSHOT_RENDER_DELAY_SECONDS)

    image = object.grabScreenshot(window)
    image.save(screenshot_path)

    return screenshot_path

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

def verify_cgui_prelogin():
    try:
        waitForObject(names.polaris_cGUI_logo_Image, 3000)
        test.warning("Launch Deviation: cGUI opened on the System Ready screen. Clicking on the logo to continue to login.")
        mouseClick(waitForObject(names.polaris_cGUI_logo_Image), 205, 53, Qt.LeftButton)
    except LookupError:
        test.log("System Ready screen did not appear. cGUI proceeded directly to login.")

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
    "verify_agui_viscoat_step": verify_agui_viscoat_step

    

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
        handler()

        screenshot = capture_screenshot()

        write_result(
            status="PASS",
            actual=f"Completed Squish step '{SQUISH_STEP}' successfully.",
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

