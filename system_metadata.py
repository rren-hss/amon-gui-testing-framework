import logging
import re
import subprocess

#To get software version from Ansible script output

def get_polaris_version_metadata(
    inventory_path,
    host_group="amon",
    timeout=60,
):
    command = [
        "ansible",
        host_group,
        "-i",
        inventory_path,
        "-m",
        "shell",
        "-a",
        (
            "apt list --installed 2>/dev/null "
            "| grep polaris"
        ),
    ]

    logging.info(
        "Checking installed Polaris packages using Ansible."
    )

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
            "summary": "Ansible command not found.",
            "hosts": {},
            "raw_output": "",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "ERROR",
            "summary": "Polaris version check timed out.",
            "hosts": {},
            "raw_output": "",
        }

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if completed.returncode != 0:
        return {
            "status": "ERROR",
            "summary": (
                stderr
                or stdout
                or "Ansible version check failed."
            ),
            "hosts": {},
            "raw_output": stdout,
        }

    hosts = parse_ansible_apt_output(stdout)

    if not hosts:
        return {
            "status": "UNKNOWN",
            "summary": "No installed Polaris packages were found.",
            "hosts": {},
            "raw_output": stdout,
        }

    versions = sorted(
        {
            package_data["version"]
            for packages in hosts.values()
            for package_data in packages
        }
    )

    if len(versions) == 1:
        summary = versions[0]
    else:
        summary = ", ".join(versions)

    return {
        "status": "PASS",
        "summary": summary,
        "hosts": hosts,
        "raw_output": stdout,
    }

def parse_ansible_apt_output(output):
    hosts = {}
    current_host = None

    header_pattern = re.compile(
        r"^([^|\s]+)\s+\|\s+"
        r"(?:CHANGED|SUCCESS|FAILED)"
    )

    package_pattern = re.compile(
        r"^([^/\s]+)/\S+\s+"
        r"([^\s]+)\s+"
    )

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        header_match = header_pattern.match(line)

        if header_match:
            current_host = header_match.group(1)
            hosts.setdefault(current_host, [])
            continue

        if current_host is None:
            continue

        package_match = package_pattern.match(line)

        if not package_match:
            continue

        package_name = package_match.group(1)
        version = package_match.group(2)

        if not package_name.startswith("polaris"):
            continue

        hosts[current_host].append(
            {
                "package": package_name,
                "version": version,
            }
        )

    return {
        host: packages
        for host, packages in hosts.items()
        if packages
    }