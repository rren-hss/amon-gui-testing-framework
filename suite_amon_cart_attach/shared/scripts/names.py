# encoding: UTF-8

from objectmaphelper import *

polaris_cGUI_QQuickApplicationWindow = {"title": "Polaris® - cGUI", "type": "QQuickApplicationWindow", "unnamed": 1, "visible": True}
polaris_cGUI_Login = {"container": polaris_cGUI_QQuickApplicationWindow, "type": "Login", "unnamed": 1, "visible": True}
usernameField_TextField = {"container": polaris_cGUI_Login, "echoMode": 0, "id": "usernameField", "type": "TextField", "unnamed": 1, "visible": True}
passwordField_TextField = {"container": polaris_cGUI_Login, "echoMode": 2, "id": "passwordField", "passwordCharacter": "•", "type": "TextField", "unnamed": 1, "visible": True}
login_MyLabel = {"container": polaris_cGUI_Login, "text": "Login", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_QQuickApplicationWindow = {"title": "Polaris® - aGUI", "type": "QQuickApplicationWindow", "unnamed": 1, "visible": True}
polaris_aGUI_AwaitingLoginLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "AWAITING LOGIN", "type": "MyLabel", "unnamed": 1, "visible": True,}
polaris_cGUI_UserLoginLabel = {"container": polaris_cGUI_Login, "text": "User login", "type": "MyLabel", "unnamed": 1, "visible": True,}
polaris_cGUI_Main_MyLabel = {"container": polaris_cGUI_QQuickApplicationWindow, "text": "Main", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_Rectangle = {"color": "#0c1118", "container": polaris_aGUI_QQuickApplicationWindow, "type": "Rectangle", "unnamed": 1, "visible": True}
polaris_cGUI_System_Ready_Text = {"container": polaris_cGUI_QQuickApplicationWindow, "text": "System Ready", "type": "Text", "unnamed": 1, "visible": True}
    
polaris_cGUI_logo_Image = {"container": polaris_cGUI_QQuickApplicationWindow, "id": "logo", "source": "qrc:/HSS logo.svg", "type": "Image", "unnamed": 1, "visible": True}
polaris_aGUI_topBar_TopBar = {"container": polaris_aGUI_QQuickApplicationWindow, "objectName": "topBar", "type": "TopBar", "visible": True}
polaris_cGUI_ActiveCase = {"container": polaris_cGUI_QQuickApplicationWindow, "type": "ActiveCase", "unnamed": 1, "visible": True}
o_Rectangle = {"color": "#121a26", "container": polaris_cGUI_ActiveCase, "type": "Rectangle", "unnamed": 1, "visible": True}
polaris_aGUI_Surgeon_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Surgeon:", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_cGUI_MainPage = {"container": polaris_cGUI_QQuickApplicationWindow, "type": "MainPage", "unnamed": 1, "visible": True}
case_Setup_Text = {"container": polaris_cGUI_MainPage, "text": "Case Setup", "type": "Text", "unnamed": 1, "visible": True}
polaris_cGUI_CaseSetup = {"container": polaris_cGUI_QQuickApplicationWindow, "type": "CaseSetup", "unnamed": 1, "visible": True}
caseIdInput_TextField = {"container": polaris_cGUI_CaseSetup, "echoMode": 0, "id": "caseIdInput", "type": "TextField", "unnamed": 1, "visible": True}
surgeonDropdown_ComboBox = {"container": polaris_cGUI_CaseSetup, "id": "surgeonDropdown", "type": "ComboBox", "unnamed": 1, "visible": True}
polaris_cGUI_Overlay = {"container": polaris_cGUI_QQuickApplicationWindow, "type": "Overlay", "unnamed": 1, "visible": True}
dr_Smith_ItemDelegate = {"checkable": False, "container": polaris_cGUI_Overlay, "text": "Dr. Smith", "type": "ItemDelegate", "unnamed": 1, "visible": True}
oS_Text = {"container": polaris_cGUI_CaseSetup, "text": "OS", "type": "Text", "unnamed": 1, "visible": True}
move_to_Draping_Text = {"container": polaris_cGUI_CaseSetup, "text": "Move to Draping", "type": "Text", "unnamed": 1, "visible": True}
polaris_aGUI_Initialize_Case_Text = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Initialize Case", "type": "Text", "unnamed": 1, "visible": True}
polaris_cGUI_companyLogo_Image = {"container": polaris_cGUI_QQuickApplicationWindow, "id": "companyLogo", "source": "qrc:/HSS logo.svg", "type": "Image", "unnamed": 1, "visible": True}
moving_to_Draping_position_MyLabel = {"container": polaris_cGUI_CaseSetup, "text": "Moving to Draping position…", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_Case_123_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Case: 123", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_Eye_Laterality_OS_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Eye Laterality: OS", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_Dr_Smith_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Dr. Smith", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_cGUI_MyToolButton = {"checkable": False, "container": polaris_cGUI_QQuickApplicationWindow, "id": "backButton", "text": "", "type": "MyToolButton", "unnamed": 1, "visible": True}
system_is_ready_for_Draping_MyLabel = {"container": polaris_cGUI_CaseSetup, "text": "System is ready for Draping", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_System_is_ready_for_draping_Before_scrubbing_in_please_complete_the_following_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "System is ready for draping. Before scrubbing in, please complete the following:", "type": "MyLabel", "unnamed": 1, "visible": True}
the_system_is_in_the_Draping_position_Before_scrubbing_in_complete_the_following_steps_MyLabel = {"container": polaris_cGUI_CaseSetup, "text": "The system is in the Draping position. Before scrubbing in, complete the following steps:", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_DrapingInstructions = {"color": "#121a26", "container": polaris_aGUI_QQuickApplicationWindow, "type": "DrapingInstructions", "unnamed": 1, "visible": True}
ready_for_Surgery_Waiting_for_surgeon_to_start_MyLabel = {"container": polaris_cGUI_CaseSetup, "text": "Ready for Surgery. Waiting for surgeon to start.", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_Assistant_Active_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Assistant Active", "type": "MyLabel", "unnamed": 1, "visible": True}
case_is_Active_MyLabel = {"container": polaris_cGUI_ActiveCase, "text": "Case is Active", "type": "MyLabel", "unnamed": 1, "visible": True}
control_assigned_to_Surgeon_and_Assistant_GUIs_MyLabel = {"container": polaris_cGUI_ActiveCase, "text": "Control assigned to Surgeon and Assistant GUIs", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_Confirm_Text = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Confirm", "type": "Text", "unnamed": 1, "visible": True}
polaris_aGUI_Confirm_Text_2 = {"container": polaris_aGUI_QQuickApplicationWindow, "occurrence": 2, "text": "Confirm", "type": "Text", "unnamed": 1, "visible": True}
polaris_aGUI_Surgeon_Active_MyLabel = {"container": polaris_aGUI_QQuickApplicationWindow, "text": "Surgeon Active", "type": "MyLabel", "unnamed": 1, "visible": True}
polaris_aGUI_stepList_ListView = {"container": polaris_aGUI_QQuickApplicationWindow, "id": "stepList", "type": "ListView", "unnamed": 1, "visible": True}
stepList_Viscoat_ProcedureStepButton = {"checkable": False, "container": polaris_aGUI_stepList_ListView, "text": "Viscoat", "type": "ProcedureStepButton", "unnamed": 1, "visible": True}
viscoat_Rectangle = {"color": "#000000", "container": stepList_Viscoat_ProcedureStepButton, "type": "Rectangle", "unnamed": 1, "visible": True}
