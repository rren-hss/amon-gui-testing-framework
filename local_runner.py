import argparse
import logging
import re
import subprocess
import sys
from datetime import datetime

from config import (
    ANSIBLE_HOST_GROUP,
    ANSIBLE_INSTALL_TIMEOUT,
    ANSIBLE_INVENTORY_PATH,
    ANSIBLE_PLAYBOOK_PATH,
    ANSIBLE_POLARIS_VERSION_PREFIX,
    ANSIBLE_SYSTEM_MODE,
)


# YYYYMMDD build-date format required by the "polaris_version=<prefix>-YYYYMMDD" extra-var.
DATE_PATTERN = re.compile(r"^\d{8}$")

# Matches one host's line in ansible-playbook's trailing "PLAY RECAP" summary, e.g.
# "cart-pc  : ok=5  changed=2  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0".
PLAY_RECAP_PATTERN = re.compile(
    r"^(?P<host>\S+)\s*:\s*"
    r"ok=(?P<ok>\d+)\s+"
    r"changed=(?P<changed>\d+)\s+"
    r"unreachable=(?P<unreachable>\d+)\s+"
    r"failed=(?P<failed>\d+)",
    flags=re.MULTILINE,
)


# Configures console logging for this script when run standalone
# (main.py sets up its own logging/log file, so this isn't reused there).
def setup_standalone_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Lets the build date be supplied non-interactively (e.g. from a scheduled job).
def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Install an Amon nightly build on the "
            "remote hosts via Ansible."
        ),
    )

    parser.add_argument(
        "--date",
        help=(
            "Nightly build date as YYYYMMDD. If omitted, "
            "you'll be prompted interactively."
        ),
    )

    return parser.parse_args()


# Interactive fallback when --date wasn't passed on the command line.
def prompt_build_date():
    default_date = datetime.now().strftime("%Y%m%d")

    answer = input(
        f"Enter nightly build date [YYYYMMDD] "
        f"(default {default_date}): "
    ).strip()

    return answer or default_date


# Resolves the build date from the CLI flag or the interactive prompt,
# then validates it's an actual YYYYMMDD calendar date before it's
# baked into the ansible-playbook extra-vars.
def resolve_build_date(cli_date):
    build_date = cli_date or prompt_build_date()

    if not DATE_PATTERN.match(build_date):
        raise ValueError(
            f"Build date '{build_date}' is not in "
            f"YYYYMMDD format."
        )

    try:
        datetime.strptime(build_date, "%Y%m%d")

    except ValueError as error:
        raise ValueError(
            f"Build date '{build_date}' is not a "
            f"valid calendar date."
        ) from error

    return build_date


# Interactive y/N gate before touching the remote hosts, per the
# roadmap requirement to "ask permission" before installing.
def prompt_install_confirmation(
    host_group,
    polaris_version,
):
    answer = input(
        f"Install Polaris '{polaris_version}' on host "
        f"group '{host_group}' now? [y/N]: "
    ).strip().lower()

    return answer in ("y", "yes")


# Parses ansible-playbook's PLAY RECAP into a per-host pass/fail
# summary; a host is FAIL if it reported any failed or unreachable tasks.
def parse_playbook_output(output):
    hosts = {}

    for match in PLAY_RECAP_PATTERN.finditer(output):
        failed = int(match.group("failed"))
        unreachable = int(match.group("unreachable"))

        hosts[match.group("host")] = {
            "ok": int(match.group("ok")),
            "changed": int(match.group("changed")),
            "unreachable": unreachable,
            "failed": failed,
            "status": (
                "FAIL"
                if (failed or unreachable)
                else "PASS"
            ),
        }

    return hosts


def install_nightly_build(
    build_date,
    inventory_path=ANSIBLE_INVENTORY_PATH,
    playbook_path=ANSIBLE_PLAYBOOK_PATH,
    host_group=ANSIBLE_HOST_GROUP,
    version_prefix=ANSIBLE_POLARIS_VERSION_PREFIX,
    system_mode=ANSIBLE_SYSTEM_MODE,
    timeout=ANSIBLE_INSTALL_TIMEOUT,
):
    polaris_version = f"{version_prefix}-{build_date}"

    # ansible-playbook -i inventory.yaml playbooks/upgrade.yaml --limit amon
    #   -e "polaris_version=<prefix>-<date>" -e "system_mode-<mode>"
    command = [
        "ansible-playbook",
        "-i",
        str(inventory_path),
        str(playbook_path),
        "--limit",
        host_group,
        "-e",
        f"polaris_version={polaris_version}",
        "-e",
        f"system_mode-{system_mode}",
    ]

    logging.info(
        "Running Ansible playbook '%s' to install "
        "Polaris '%s' on host group '%s'.",
        playbook_path,
        polaris_version,
        host_group,
    )

    # Run the command, treating a missing ansible-playbook binary or
    # a run that overruns the timeout as framework-level errors.
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    except FileNotFoundError:
        return {
            "status": "ERROR",
            "summary": "ansible-playbook command not found.",
            "hosts": {},
            "raw_output": "",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "ERROR",
            "summary": (
                f"Nightly build install timed out after "
                f"{timeout}s."
            ),
            "hosts": {},
            "raw_output": "",
        }

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    # Parse per-host results out of the PLAY RECAP section.
    hosts = parse_playbook_output(stdout)

    if not hosts:
        return {
            "status": "ERROR",
            "summary": (
                stderr
                or stdout
                or (
                    "No PLAY RECAP was found in the "
                    "playbook output."
                )
            ),
            "hosts": {},
            "raw_output": stdout,
        }

    failed_hosts = sorted(
        host
        for host, result in hosts.items()
        if result["status"] == "FAIL"
    )

    if failed_hosts or completed.returncode != 0:
        status = "FAIL"
        summary = (
            f"Nightly build install failed on: "
            f"{', '.join(failed_hosts) or 'unknown host(s)'} "
            f"(exit code {completed.returncode})."
        )

    else:
        status = "PASS"
        summary = (
            f"Polaris '{polaris_version}' installed on: "
            f"{', '.join(sorted(hosts))}."
        )

    return {
        "status": status,
        "summary": summary,
        "hosts": hosts,
        "raw_output": stdout,
    }


def main():
    setup_standalone_logging()
    args = parse_args()

    # Resolve and validate the build date before anything else runs.
    try:
        build_date = resolve_build_date(args.date)

    except ValueError as error:
        logging.error(str(error))
        return 1

    polaris_version = (
        f"{ANSIBLE_POLARIS_VERSION_PREFIX}-{build_date}"
    )

    # Announce what's about to happen before asking for confirmation.
    logging.info("Amon nightly build installer")
    logging.info(
        "Target host group: %s",
        ANSIBLE_HOST_GROUP,
    )
    logging.info(
        "Polaris version: %s",
        polaris_version,
    )

    # Bail out without touching any hosts if the operator declines.
    if not prompt_install_confirmation(
        ANSIBLE_HOST_GROUP,
        polaris_version,
    ):
        logging.info("Install cancelled by operator.")
        return 1

    result = install_nightly_build(build_date)

    if result["status"] == "PASS":
        logging.info(result["summary"])
    else:
        logging.error(result["summary"])

    # Log each host's individual outcome for quick scanning.
    for host, host_result in result["hosts"].items():
        logging.info(
            "%s: %s",
            host,
            host_result["status"],
        )

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
