import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Framework paths
# ---------------------------------------------------------------------------

FRAMEWORK_ROOT = Path(__file__).resolve().parent

OUTPUT_ROOT = Path(
    os.environ.get(
        "AMON_TEST_OUTPUT_ROOT",
        str(FRAMEWORK_ROOT / "test_outputs"),
    )
).expanduser().resolve()

MANUAL_POPUP_PATH = Path(
    os.environ.get(
        "MANUAL_POPUP_PATH",
        str(FRAMEWORK_ROOT / "manual_popup.py"),
    )
).expanduser().resolve()


# # ---------------------------------------------------------------------------
# # Amon connection settings (uncomment when connecting to actual system)
# # ---------------------------------------------------------------------------

# AMON_CART_HOST = os.environ.get(
#     "AMON_CART_IP",
#     "172.16.0.102",
# )

# AMON_CART_PORT = int(
#     os.environ.get(
#         "AMON_CART_PORT",
#         "4322",
#     )
# )

# AMON_COCKPIT_HOST = os.environ.get(
#     "AMON_COCKPIT_IP",
#     "172.16.0.103",
# )

# AMON_COCKPIT_PORT = int(
#     os.environ.get(
#         "AMON_COCKPIT_PORT",
#         "4322",
#     )
# )
# ---------------------------------------------------------------------------
# Docker connection settings (uncomment when connecting to Docker container)
# ---------------------------------------------------------------------------
AMON_CART_HOST = os.environ.get(
    "AMON_CART_IP",
    "127.0.0.1",
)

AMON_CART_PORT = int(
    os.environ.get(
        "AMON_CART_PORT",
        "14322",
    )
)

AMON_COCKPIT_HOST = os.environ.get(
    "AMON_COCKPIT_IP",
    "127.0.0.1",
)

AMON_COCKPIT_PORT = int(
    os.environ.get(
        "AMON_COCKPIT_PORT",
        "24322",
    )
)

# ---------------------------------------------------------------------------
# SSH settings
# ---------------------------------------------------------------------------

SSH_USER = os.environ.get(
    "AMON_SSH_USER",
    "horizon",
)

SSH_KEY_PATH = os.environ.get(
    "AMON_SSH_KEY_PATH",
    "",
).strip()

SSH_CONNECT_TIMEOUT = int(
    os.environ.get(
        "AMON_SSH_CONNECT_TIMEOUT",
        "15",
    )
)

# ---------------------------------------------------------------------------
# Squish settings
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Target environment detection
# ---------------------------------------------------------------------------

# Derived, not separately configured: AMON_CART_HOST above already declares
# which environment a run targets (loopback == the Docker containers'
# host-mapped ports, anything else == real Amon hardware), so this just
# names that fact instead of tracking it a second time.
TARGET_ENVIRONMENT = (
    "docker"
    if AMON_CART_HOST in ("127.0.0.1", "localhost")
    else "physical"
)

SQUISHRUNNER = os.environ.get(
    "SQUISHRUNNER",
    str(
        Path.home()
        / "squish-for-qt-9.2.2_68x"
        / "bin"
        / "squishrunner"
    ),
)

# ---------------------------------------------------------------------------
# Software-version lookup
# ---------------------------------------------------------------------------

ANSIBLE_INVENTORY_PATH = Path(
    os.environ.get(
        "ANSIBLE_INVENTORY_PATH",
        str(
            FRAMEWORK_ROOT
            / "ansible"
            / "inventory.yaml"
        ),
    )
).expanduser().resolve()

ANSIBLE_HOST_GROUP = "amon"
ANSIBLE_VERSION_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Nightly build install settings
# ---------------------------------------------------------------------------

ANSIBLE_PLAYBOOK_PATH = Path(
    os.environ.get(
        "ANSIBLE_PLAYBOOK_PATH",
        str(
            FRAMEWORK_ROOT
            / "ansible"
            / "playbooks"
            / "upgrade.yaml"
        ),
    )
).expanduser().resolve()

ANSIBLE_POLARIS_VERSION_PREFIX = os.environ.get(
    "ANSIBLE_POLARIS_VERSION_PREFIX",
    "3",
)

ANSIBLE_SYSTEM_MODE = os.environ.get(
    "ANSIBLE_SYSTEM_MODE",
    "prod",
)

ANSIBLE_INSTALL_TIMEOUT = int(
    os.environ.get(
        "ANSIBLE_INSTALL_TIMEOUT",
        "600",
    )
)


# ---------------------------------------------------------------------------
# Runtime behavior
# ---------------------------------------------------------------------------

DEMO_MODE = os.environ.get(
    "DEMO_MODE",
    "false",
).lower() == "true"

OPEN_REPORTS = os.environ.get(
    "OPEN_REPORTS",
    "false",
).lower() == "true"