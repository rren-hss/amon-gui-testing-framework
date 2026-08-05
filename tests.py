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
    # {
    #     "id": "QA-T1128",
    #     "name": "Verify Core Polaris C System Health on Amon Cart",
    #     "gui": "",
    #     "failure_policy": "continue",
    #     "steps": [
    #         {
    #             "step_id": "1 of 2",
    #             "type": "terminal",
    #             "host": AMON_CART_HOST,
    #             "command": "~/bootcheck3.0/run_bootcheck.sh",
    #             "timeout": 300,
    #             "instruction": "SSH into Amon Cart PC and run the bootcheck script",
    #             "expected": "Boot check execute and reports zero failed checks.",
    #             "parser": {
    #                 "type": "bootcheck"
    #             }
    #         },
    #         {
    #             "step_id": "2 of 2",
    #             "type": "terminal",
    #             "host": AMON_COCKPIT_HOST,
    #             "command": "~/bootcheck3.0/run_bootcheck.sh",
    #             "timeout": 300,
    #             "instruction": "SSH into Amon Cockpit PC and run the bootcheck script",
    #             "expected": "Boot check executes and reports zero failed checks.",
    #             "parser": {
    #                 "type": "bootcheck"
    #             }

    #         }
    #     ]
    # },
        

    
     {
         "id": "QA-T1127",
         "name": "Verify All Polaris C Displays Are On",
         "gui": "Multi-GUI",
         "failure_policy": "abort",
         "steps": [
             {
                 "step_id": "1 of 4",
                 "type": "auto",
                 "gui": "cartGUI",
                 "squish_step": "cart_gui_window",
                 "screenshot": "cart_gui_window.png",
                 "instruction": "Cart GUI touch screen is on",
                 "expected": "Squish attaches to the running Cart GUI and verifies that there is a visible application window",
             },
             {
                 "step_id": "2 of 4",
                 "type": "auto",
                 "gui": "assistantGUI",
                 "squish_step": "assistant_gui_window",
                 "screenshot": "assistant_gui_window.png",
                 "instruction": "Assistant GUI touch screen is on",
                 "expected": "Squish attaches to the running Assistant GUI and verifies that there is a visible application window",
             },
             {
                 "step_id": "3 of 4",
                 "type": "auto",
                 "gui": "surgeonGUI",
                 "squish_step": "surgeon_gui_window",
                 "screenshot": "surgeon_gui_window.png",
                 "instruction": "Surgeon GUI touchscreen is on",
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
        "failure_policy": "abort",
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
         "failure_policy": "abort",
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

#     #CASE SETUP
#      {
#          "id": "QA-T1131",
#           "name": "Verify Surgical Case Setup & Initialization",
#           "gui": "Multi-GUI",
#           "failure_policy": "continue",
#           "steps": [
#               {
#                   "step_id": "1 of 3",
#                   "type": "auto",
#                   "gui": "cartGUI",
#                   "squish_step": "verify_cart_case_setup",
#                   "screenshot": "verify_cart_case_setup.png",
#                   "instruction": "Initialize a case with ID: 123, Laterality: OS, Surgeon: Dr. Smith. Verify that System is ready for draping.",
#                   "expected": "Appropriate fields are entered and submitted. Cart GUI indicates that the System is ready for draping.",
#                   "demo_pause": True,
#               },
#               {
#                   "step_id": "2 of 3",
#                   "type": "auto",
#                   "gui": "assistantGUI",
#                   "squish_step": "agui_case_setup_verify",
#                   "screenshot": "verify_agui_case_setup.png",
#                   "instruction":"Verify Assistant GUI displays the initialized case information and ready-for-draping instructions.",
#                   "expected": "Assistant GUI displays Case: 123, Eye Laterality: OS, Dr. Smith, and the ready-for-draping instructions.",
#               },
#               {
#                   "step_id": "3 of 3",
#                   "type": "auto",
#                   "gui": "surgeonGUI",
#                   "squish_step": "sgui_case_setup_verify",
#                   "screenshot": "verify_sgui_case_setup.png",
#                   "instruction": "Verify Surgeon GUI displays the initialized case information.",
#                   "expected": "Surgeon GUI displays Case: 123, Eye Laterality: OS, and Dr. Smith as the selected surgeon."
#               },
#           ]
#      }
]
