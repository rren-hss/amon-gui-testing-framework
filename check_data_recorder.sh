#!/usr/bin/env bash
# Check whether the data_recorder process is alive on this machine, against an
# expected state named by the caller (cart and cockpit run it continuously;
# perception never does -- see COMPUTER_EXPECTATION in data_recorder_suite.py).
#
# data_recorder is a persistent node that watches the SurgicalState topic and
# only starts/stops a recording *session* around a case; the process itself is
# not spawned or killed at case boundaries, so this is a plain liveness check
# and needs no case to be active.
#
# Prints POLARIS_DATA_RECORDER_OK on stdout if the process's presence matches
# what was expected. Prints POLARIS_DATA_RECORDER_FAILED: <reason> and exits 1
# otherwise.
# Usage: check_data_recorder.sh <running|not-running>
set -euo pipefail

EXPECT="$1"
case "$EXPECT" in
    running|not-running) ;;
    *)
        echo "Usage: check_data_recorder.sh <running|not-running>" >&2
        exit 1
        ;;
esac

PIDS=$(pgrep -f data_recorder || true)

if [ "$EXPECT" = "running" ]; then
    if [ -z "$PIDS" ]; then
        echo "POLARIS_DATA_RECORDER_FAILED: data_recorder is expected to be running here, but no matching process was found"
        exit 1
    fi
else
    if [ -n "$PIDS" ]; then
        echo "POLARIS_DATA_RECORDER_FAILED: data_recorder is expected to not be running here, but found pid(s): $(echo "$PIDS" | tr '\n' ' ')"
        exit 1
    fi
fi

echo "POLARIS_DATA_RECORDER_OK"
