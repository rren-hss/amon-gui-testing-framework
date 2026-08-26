# encoding: UTF-8

from objectmaphelper import *


polaris_Surgeon_GUI_QQuickApplicationWindow = {"type": "QQuickApplicationWindow", "unnamed": 1, "visible": True}
aWAITING_LOGIN_MyLabel = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "text": "AWAITING LOGIN", "type": "MyLabel", "unnamed": 1, "visible": True}
o_Rectangle = {"color": "#0c1118", "container": polaris_Surgeon_GUI_QQuickApplicationWindow, "type": "Rectangle", "unnamed": 1, "visible": True}
topBar_TopBar = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "objectName": "topBar", "type": "TopBar", "visible": True}
# Surgical timer value label (QA-T1139) -- see the matching comment in
# suite_amon_cart_attach/shared/scripts/names.py. Matched by shape
# (RegularExpression), not the literal text, since that changes every
# second.
sGUI_timer_MyLabel = {"container": topBar_TopBar, "text": RegularExpression(r"^\d{1,2}(:\d{2}){1,2}$"), "type": "MyLabel", "unnamed": 1, "visible": True}
surgeon_MyLabel = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "text": "Surgeon:", "type": "MyLabel", "unnamed": 1, "visible": True}
case_123_MyLabel = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "text": "Case: 123", "type": "MyLabel", "unnamed": 1, "visible": True}
eye_Laterality_OS_MyLabel = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "text": "Eye Laterality: OS", "type": "MyLabel", "unnamed": 1, "visible": True}
surgeonDropdown_ComboBox = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "id": "surgeonDropdown", "type": "ComboBox", "unnamed": 1, "visible": True}
start_Surgery_Text = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "text": "Start Surgery", "type": "Text", "unnamed": 1, "visible": True}
o_Overlay = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "type": "Overlay", "unnamed": 1, "visible": True}
confirm_Text = {"container": o_Overlay, "text": "Confirm", "type": "Text", "unnamed": 1, "visible": True}
apply_Docking_to_the_operative_eye_MyLabel = {"container": o_Overlay, "text": "Apply Docking to the operative eye", "type": "MyLabel", "unnamed": 1, "visible": True}
stepList_ListView = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "id": "stepList", "type": "ListView", "unnamed": 1, "visible": True}
stepList_Viscoat_ProcedureStepButton = {"checkable": False, "container": stepList_ListView, "text": "Viscoat", "type": "ProcedureStepButton", "unnamed": 1, "visible": True}
viscoat_Rectangle = {"color": "#000000", "container": stepList_Viscoat_ProcedureStepButton, "type": "Rectangle", "unnamed": 1, "visible": True}

polaris_sGUI_octPlayer_GstStreamPlayer = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "id": "octPlayer", "type": "GstStreamPlayer", "unnamed": 1, "visible": True}
polaris_sGUI_widePlayer_GstStreamPlayer = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "id": "widePlayer", "type": "GstStreamPlayer", "unnamed": 1, "visible": True}
polaris_sGUI_leftPlayer_GstStreamPlayer = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "id": "leftPlayer", "type": "GstStreamPlayer", "unnamed": 1, "visible": True}
polaris_sGUI_rightPlayer_GstStreamPlayer = {"container": polaris_Surgeon_GUI_QQuickApplicationWindow, "id": "rightPlayer", "type": "GstStreamPlayer", "unnamed": 1, "visible": True}
