import os

from config import (
    AMON_CART_HOST,
    AMON_CART_PORT,
    AMON_COCKPIT_HOST,
    AMON_COCKPIT_PORT,
    MANUAL_POPUP_PATH
)

FRAMEWORK_ROOT = os.path.dirname(os.path.abspath(__file__))


APPLICATIONS = {
    "cartGUI": {
        "aut": "cart_gui",
        "host": AMON_CART_HOST,
        "port": AMON_CART_PORT,
        "suite": os.path.join(FRAMEWORK_ROOT, "suite_amon_cart_attach"),
        "testcase": "tst_attach_cart",
        "timeout": 120,
    },
    "assistantGUI": {
        "aut": "assistant_gui",
        "host": AMON_CART_HOST,
        "port": AMON_CART_PORT,
        "suite": os.path.join(FRAMEWORK_ROOT, "suite_amon_cart_attach"),
        "testcase": "tst_attach_cart",
        "timeout": 120,
    },
    "surgeonGUI": {
        "aut": "surgeon_gui",
        "host": AMON_COCKPIT_HOST,
        "port": AMON_COCKPIT_PORT,
        "suite": os.path.join(FRAMEWORK_ROOT, "suite_amon_cockpit_attach"),
        "testcase": "tst_attach_cockpit",
        "timeout": 120,
    },
}

TEST_STEPS = [
    {
        "id": "QA-T1128",
        "name": "Verify Core Polaris C System Health on Amon Cart",
        "gui": "",
        "failure_policy": "continue",
        "requires_physical_hardware": True,
        "steps": [
            {
                "step_id": "1 of 2",
                "type": "terminal",
                "host": AMON_CART_HOST,
                "command": "~/bootcheck3.0/run_bootcheck.sh",
                "timeout": 300,
                "instruction": "SSH into Amon Cart PC and run the bootcheck script",
                "expected": "Boot check execute and reports zero failed checks.",
                "parser": {
                    "type": "bootcheck"
                }
            },
            {
                "step_id": "2 of 2",
                "type": "terminal",
                "host": AMON_COCKPIT_HOST,
                "command": "~/bootcheck3.0/run_bootcheck.sh",
                "timeout": 300,
                "instruction": "SSH into Amon Cockpit PC and run the bootcheck script",
                "expected": "Boot check executes and reports zero failed checks.",
                "parser": {
                    "type": "bootcheck"
                }

            }
        ]
    },
        

    
     {
         "id": "QA-T1127",
         "name": "Verify All Polaris C Displays Are On",
         "gui": "Multi-GUI",
         "failure_policy": "continue",
         "steps": [
             {
                 "step_id": "1 of 4",
                 "type": "auto",
                 "gui": "cartGUI",
                 "squish_step": "cart_gui_window",
                 "screenshot": "cart_gui_window.png",
                 "instruction": "Verify Cart GUI touch screen is on",
                 "expected": "Squish attaches to the running Cart GUI and verifies that there is a visible application window",
             },
             {
                 "step_id": "2 of 4",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "assistant_gui_window",
                 "screenshot": "assistant_gui_window.png",
                 "instruction": "Verify Assistant GUI touch screen is on",
                 "expected": "Squish attaches to the running Assistant GUI and verifies that there is a visible application window",
             },
             {
                 "step_id": "3 of 4",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "surgeon_gui_window",
                 "screenshot": "surgeon_gui_window.png",
                 "instruction": "Verify surgeon GUI touchscreen is on",
                 "expected": "Squish attaches to the running Surgeon GUI and verifies that there is a visible application window.",
             },
             {
                 "step_id": "4 of 4",
                 "type": "manual",
                 "gui": "lindirGUI",
                 "instruction": "Lindir 3D TV is on",
                 "expected": "lindir GUI is running and there is a visible application window",
                 "manual_popup_path": MANUAL_POPUP_PATH,
             }
         ],
     },

#PRE LOGIN CHECKS
    {
        "id": "QA-T1132",
        "name": "Assistant GUI - Pre Login Status Verification",
        "gui": "assistantGUI",
        "failure_policy": "continue",
        "steps": [
            {
                "step_id": "QA-T1132",
                "type": "auto",
                "gui": "assistantGUI",
                "squish_step": "agui_prelogin_verify",
                "screenshot": "agui_prelogin_verify.png",
                "instruction": "Verify that assistantGUI is in the pre login state",
                "expected": "Assistant GUI shows waiting for login.",
                "demo_pause": True,
            }
        ]
    },
    {
        "id": "QA-T1129",
        "name": "Verify That Cart GUI Loads And Shows The Login Screen After Reboot",
        "gui": "cartGUI",
        "failure_policy": "continue",
        "steps": [
            {
                "step_id": "QA-T1129",
                "type": "auto",
                "gui": "cartGUI",
                "squish_step": "cgui_prelogin_verify",
                "screenshot": "cgui_prelogin_verify.png",
                "instruction": "Verify cart GUI - Pre-Login State & behavior.",
                "expected": "Cart GUI shows login state",
            }
        ]
    },
    {
        "id": "QA-T1133",
        "name": "Verify That Surgeon GUI Loads And Shows Waiting Login Screen After Reboot",
        "gui": "surgeonGUI",
        "failure_policy": "continue",
        "steps": [
            {
                "step_id": "QA-T1133",
                "type": "auto",
                "gui": "surgeonGUI",
                "squish_step": "sgui_prelogin_verify",
                "screenshot": "sgui_prelogin_verify.png",
                "instruction": "Verify Surgeon GUI - Pre-Login State & behavior.",
                "expected": "Surgeon GUI shows waiting for login" 
            }
        ]

    },

#POST LOGIN CHECKS
     {
         "id": "QA-T1130",
         "name": "Verify That Cart GUI Can Log In And Unlock Other GUIs",
         "gui": "Multi-GUI",
         "failure_policy": "continue",
         "reset_before": True,
         "reset_after": True,
         "steps": [
             {
                 "step_id": "1 of 3",
                 "type": "auto",
                 "gui": "cartGUI",
                 "squish_step": "cart_gui_login",
                 "screenshot": "cart_gui_login.png",
                 "instruction": "Login as a valid user on Cart GUI. Type a valid username and password. Verify Cart GUI enters main screen after login.",
                 "expected": "Login success.",
                 "demo_pause": True,
             },
             {
                 "step_id": "2 of 3",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "agui_post_login",
                 "screenshot": "agui_post_login.png",
                 "instruction": "Verify Assistant GUI changes from the waiting-for-login screen to a grayed-out main screen after Cart GUI login success.",
                 "expected": "Other GUIs show a grayed-out main screen after Cart GUI login success, and remain grayed out until the surgical case starts",
             },
             {
                 "step_id": "3 of 3",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "sgui_post_login",
                 "screenshot": "sgui_post_login.png",
                 "instruction": "Verify Surgeon GUI changes from the waiting-for-login screen to a grayed-out main screen after Cart GUI login success.",
                 "expected": "Other GUIs show a grayed-out main screen after Cart GUI login success, and remain grayed out until the surgical case starts",
             },
         
         ]
     },

    #CASE SETUP
     {
          "id": "QA-T1131",
          "name": "Verify Surgical Case Setup & Initialization",
          "gui": "Multi-GUI",
          "failure_policy": "abort",
          "steps": [
              {
                  "step_id": "1 of 3",
                  "type": "auto",
                  "gui": "cartGUI",
                  "squish_step": "verify_cart_case_setup",
                  "screenshot": True,
                  "instruction": "Initialize a case with ID: 123, Laterality: OS, Surgeon: Dr. Smith. Verify that System is ready for draping.",
                  "expected": "Appropriate fields are entered and submitted. Cart GUI indicates that the System is ready for draping.",
                  "demo_pause": True,
              },
              {
                  "step_id": "2 of 3",
                  "type": "auto",
                  "gui": "assistantGUI",
                  "squish_step": "agui_case_setup_verify",
                  "screenshot": "verify_agui_case_setup.png",
                  "instruction":"Verify Assistant GUI displays the initialized case information and ready-for-draping instructions.",
                  "expected": "Assistant GUI displays Case: 123, Eye Laterality: OS, Dr. Smith, and the ready-for-draping instructions.",
              },
              {
                  "step_id": "3 of 3",
                  "type": "auto",
                  "gui": "surgeonGUI",
                  "squish_step": "sgui_case_setup_verify",
                  "screenshot": "verify_sgui_case_setup.png",
                  "instruction": "Verify Surgeon GUI displays the initialized case information.",
                  "expected": "Surgeon GUI displays Case: 123, Eye Laterality: OS, and Dr. Smith as the selected surgeon."
              },
          ]
     },

     {
         "id": "QA-T1156",
         "name": "Surgical Case Flow Verification Test",
         "gui": "Multi-GUI",
         "failure_policy": "continue",
         "steps": [
             {
                 "step_id": "1 of 20",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "verify_agui_ini_case",
                 "screenshot": True,
                 "instruction": "Check if Assistant GUI shows 'Initialize Case' button",
                 "expected": "'Initialize Case button' shows on Assistant GUI.",
             },
             {
                 "step_id": "2 of 20",
                 "type": "auto",
                 "gui": "cartGUI",
                 "squish_step": "verify_cgui_draping_ready",
                 "screenshot": True,
                 "instruction": "Check if Cart GUI shows the message 'System is ready for Draping...",
                 "expected": "Cart GUI shows the message 'System is ready for Draping...",
             },
             {
                 "step_id": "3 of 20",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "click_agui_ini_case",
                 "screenshot": True,
                 "instruction": "Click 'initialize case' on Assistant GUI",
                 "expected": "'Initialize Case' was clicked on the Assistant GUI",
             },
             {
                 "step_id": "4 of 20",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "verify_start_surgery_button",
                 "screenshot": True,
                 "instruction": "Control is transferred to Surgeon for Starting the Case. 'Start Surgery' popup is displayed on the sGUI waiting for Surgeon's response",
                 "expected": "'Start Surgery' Pop up is displayed on the Surgeon GUI - Waiting for the Surgeon's Response.",
                 
             },
            
             {
                 "step_id": "5 of 20",
                 "type": "auto",
                 "gui": "cartGUI",
                 "squish_step": "verify_cgui_surgeon_control",
                 "screenshot": True,
                 "instruction": "Control is transferred to Surgeon for Starting the Case. 'Ready for Surgery' text is displayed on the cGUI waiting for Surgeon's response",
                 "expected": "'Ready for Surgery' text is displayed on the cGUI waiting for Surgeon's response",
             },
             {
                 "step_id": "6 of 20",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "click_sgui_start_surgery",
                 "screenshot": True,
                 "instruction": "On the SGUI: Press the Start Surgery Button.",
                 "expected": "Screen displays a prompting of the application of the docking to Operator Eye"
             },
           
             {
                 "step_id": "7 of 20",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "verify_sgui_enabled",
                 "screenshot": True,
                 "instruction": "On the sGUI: Press the confirm button. Wait for the transition of the sGUI to an enabled (not grayed out) screen",
                 "expected": "sGUI transitions to an enabled screen"
             },
             {
                 "step_id": "8 of 20",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "verify_agui_main_screen",
                 "screenshot": True,
                 "instruction": "Verify Assistant GUI is on main surgery scene. Should display 'Assistant Active'",
                 "expected": "Assistant GUI is on main surgery scene. Displays 'Assistant Active'",
             },
             {
                 "step_id": "9 of 20",
                 "type": "auto",
                 "gui": "cartGUI",
                 "squish_step": "verify_cgui_active_case",
                 "screenshot": True,
                 "instruction": "Verify Cart GUI shows 'Case is Active Screen'",
                 "expected": "Cart GUI displays that the Case is Active and that Control assigned to Surgeon and Assistant GUIs",
             },
             {
                 "step_id": "10 of 20",
                 "type": "manual",
                 "gui": "lindirGUI",
                 "instruction": "Verify 3D Lindir shows the main screen with video channels. Note: No need to verify incoming stream",
                 "expected": "Lindir 3D shows the main screen with video channels",
                 "manual_popup_path": MANUAL_POPUP_PATH,
             },
             {
                 "step_id": "11 of 20",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "agui_confirmations_side_inc",
                 "instruction": "On the Assistant GUI, click confirm buttons on Secondary and Primary arm for step: “Side Incision”. Verify that aGUI says that Surgeon Active.",
                 "expected": "Upon pressing the confimation buttons on the Secondary and Primary arms on 'Side Incision'. The Assistant GUI says 'Surgeon Active'",

             },
             {
                 "step_id": "12 of 20",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "verify_step_switch_viscoat",
                 "instruction": "On the Surgeon GUI, switch to step ‘Viscoat’. Verify that ‘Viscoat’ tab is selected.",
                 "expected": "'Viscoat step is selected and highlighted",
             },
             {
                 "step_id": "13 of 20",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step":"verify_agui_viscoat_step",
                 "instruction": "On aGUI verify that step switched to step ‘Viscoat’. Verify that the secondary arm has a ‘Confirm’ button ready to be pressed - showcasing tool exchange.",
                 "expected": "Viscoat step is selected. Secondary arm showcase a confirmation for tool exchange.", 
             }
         ],

     },
    #  Need to check
     {
         "id": "QA-T1137",
         "name": "Verify wide camera feed on surgeon GUI",
         "gui": "surgeonGUI",
         "failure_policy": "continue",
         "reset_before": True,
         "reset_after": True,
         "steps": [
                     {
                         "step_id": "QA-T1137",
                         "type": "auto",
                         "gui": "surgeonGUI",
                         "squish_step": "verify_sgui_wide_camera_feed",
                         "screenshot": "verify_sgui_wide_camera_feed.png",
                         "instruction": "On the Surgeon GUI, verify the wide camera feed panel is displaying a live video stream.",
                         "expected": "Wide camera feed is visible and updating (not frozen/blank)"
                     }
                 ]
     },

     {
         "id": "QA-T1138",
         "name": "Verify Side Camera Feeds on Surgeon GUI",
         "gui": "surgeonGUI",
         "failure_policy": "continue",
         "steps": [
             {
                 "step_id": "1 of 2",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "verify_sgui_side_camera_left_feed",
                 "screenshot": "verify_sgui_side_camera_left_feed.png",
                 "instruction": "On the Surgeon GUI, verify the left side camera feed panel is displaying a live video stream.",
                 "expected": "Left side camera feed is visible and updating (not frozen/blank)",
             },
             {
                 "step_id": "2 of 2",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "verify_sgui_side_camera_right_feed",
                 "screenshot": "verify_sgui_side_camera_right_feed.png",
                 "instruction": "On the Surgeon GUI, verify the right side camera feed panel is displaying a live video stream.",
                 "expected": "Right side camera feed is visible and updating (not frozen/blank)",
             },
         ]
     }
]
