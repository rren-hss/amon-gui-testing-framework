import os

AMON_CART_HOST = os.environ.get("AMON_CART_IP", "172.16.0.102")
AMON_CART_PORT = int(os.environ.get("AMON_CART_PORT", "4322"))

AMON_COCKPIT_HOST = os.environ.get("AMON_COCKPIT_IP", "172.16.0.103")
AMON_COCKPIT_PORT = int(os.environ.get("AMON_COCKPIT_PORT", "4322"))

SQUISHRUNNER = os.environ.get(
    "SQUISHRUNNER",
    "/home/cerie/squish-for-qt-9.2.2/bin/squishrunner",
)
REPORT_PATH = os.environ.get(
    "REPORT_PATH",
    "/home/cerie/amon_test_report.html",
)
SCREENSHOT_DIR = "/home/cerie/amon_screenshots"
LOG_PATH = "/home/cerie/amon_test.log"

MANUAL_POPUP_PATH = "/home/cerie/Amon_GUI_Testing_Framework/manual_popup.py"

#To extract software version
ANSIBLE_INVENTORY_PATH = ("/home/cerie/polaris-v3/ansible/inventory.yaml")
ANSIBLE_HOST_GROUP = "amon"
ANSIBLE_VERSION_TIMEOUT = 60


DEMO_MODE = os.environ.get(
    "DEMO_MODE",
    "false",
).lower() == "true"


