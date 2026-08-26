#!/usr/bin/env bash
# Purpose: end whatever surgical case is active on this system, so the next run
# of a case-setup test starts from a system with none.
#
# Runs on the cart, which is where the surgical sequencer is. This is the one
# thing the GUI suite changes that no GUI can change back: a case that has moved
# to the draping position locks the Case Setup form, survives a logout, and the
# cart shows no control that ends it -- "Edit Case" (CaseSetup.qml) is only
# visible one step later, at docking, and appEng's unconditional "End Case" is
# not a deployed service on any rig. So cleanup asks the backend directly.
#
# That is a deliberate exception, not the pattern. Everything else the suite
# does goes through a GUI because a person has to be able to do it too; this
# does not, so a green cleanup here does NOT say a person could recover the
# same system by hand. Issue #166 is the request for a control at draping, and
# when it lands this script should be replaced by the GUI step that clicks it.
#
# What it does, in three claims rather than one:
#
#   1. reads the case status off /surgical_state before doing anything, so a
#      system with no case is a pass with nothing done rather than a command
#      the sequencer rejects
#   2. publishes END_SURGICAL_CASE on the command bus and reads the status code
#      the sequencer answered with, matched by invocation id
#   3. reads the case status back, because a command the sequencer accepted and
#      a case that actually ended are different claims
#
# The sequencer refuses the command while a client is actively controlling an
# arm, and refuses it when no case is ongoing (surgical_sequencer.cpp:1244).
# Both come back as BAD_COMMAND, which is why step 1 tells them apart: with no
# case there is nothing to undo, and with motion engaged there is something a
# human has to deal with.
#
# The echoes run --no-daemon and with their QoS spelled out, for the reason
# written up in sm_peer_watch.sh: left to itself `ros2 topic echo` asks the
# ros2cli daemon what the publishers offer, and a dead daemon answers with a
# fault and captures nothing, which reads as a silent topic. The values are not
# a guess either -- /surgical_state is published BEST_EFFORT/VOLATILE and the
# command bus RELIABLE/VOLATILE (read off `ros2 topic info -v` on amon-cart,
# 2026-08-21) -- so these subscriptions match their publishers and an empty
# capture means a missing publisher.
#
# Prints POLARIS_CASE_STATUS_BEFORE: <n>, POLARIS_END_CASE_STATUS_CODE: <n> and
# POLARIS_CASE_STATUS_AFTER: <n> as it goes, then POLARIS_END_CASE_OK: <what it
# did>. Prints POLARIS_END_CASE_FAILED: <reason> and exits 1 otherwise.
# Usage: end_surgical_case.sh [response_timeout_seconds]
set -uo pipefail

RESPONSE_TIMEOUT="${1:-15}"

REQUEST_TOPIC=/command_requests
RESPONSE_TOPIC=/command_responses
STATE_TOPIC=/surgical_state

# From polaris_interfaces/command_bus.hpp: the entity enum is positional, and
# the sequencer's command ids run from BEGIN_SURGICAL_CASE at 59.
END_SURGICAL_CASE=60
ENTITY_E_GUI=5
ENTITY_SURGICAL_SEQUENCER=13

# surgical_state::case_status. UNDEFINED is "no case has been started", which is
# the state this script exists to get back to.
CASE_STATUS_UNDEFINED=0

# How long to wait for a state sample before calling the topic silent. The
# sequencer publishes it continuously, so this is generous.
STATE_TIMEOUT=15

RESPONSE_FILE=/dev/shm/polaris_end_case_responses.yaml
RESPONSE_ERR=/dev/shm/polaris_end_case_responses.err

STATUS=0
LISTENER_PID=""

fail() {
    echo "POLARIS_END_CASE_FAILED: $1"
    STATUS=1
}

# --- Environment
# `set +u` around the sources: ROS's setup.bash reads AMENT_TRACE_SETUP_FILES
# unguarded and takes the whole script down under `set -u` before it has done
# anything.
set +u
source /opt/ros/humble/setup.bash
source /horizon/polaris/setup.bash
set -u

# --- Read One Case Status
# Prints the status byte, or nothing if no sample arrived.
read_case_status() {
    timeout "$STATE_TIMEOUT" ros2 topic echo "$STATE_TOPIC" \
        --once --no-daemon \
        --qos-reliability best_effort --qos-durability volatile \
        --field current_case.status 2>/dev/null | head -1 | tr -dc '0-9'
}

stop_listener() {
    [ -n "$LISTENER_PID" ] || return 0
    kill "$LISTENER_PID" 2>/dev/null
    wait "$LISTENER_PID" 2>/dev/null
    LISTENER_PID=""
}

# --- The Status Code For Our Invocation
# The responses of every client on the bus land in one capture, so the block
# carrying our invocation id is the only one that answers our request.
response_status_code() {
    awk -v uuid="$1" '
        /^---$/ { delete block; next }
        /invocation_uuid:/ { block["uuid"] = $2 }
        /status_code:/ { block["code"] = $2 }
        block["uuid"] == uuid && "code" in block { print block["code"]; exit }
    ' "$RESPONSE_FILE" 2>/dev/null
}

BEFORE=$(read_case_status)

if [ -z "$BEFORE" ]; then
    fail "no sample arrived on $STATE_TOPIC within ${STATE_TIMEOUT}s, so the case status could not be read"
elif [ "$BEFORE" -eq "$CASE_STATUS_UNDEFINED" ]; then
    # Idempotent, which is what lets cleanup run this without knowing whether
    # the run got as far as setting a case up.
    echo "POLARIS_CASE_STATUS_BEFORE: $BEFORE"
    echo "POLARIS_END_CASE_OK: no case was active, so nothing was ended"
else
    echo "POLARIS_CASE_STATUS_BEFORE: $BEFORE"

    # --- Listen Before Asking
    # The response topic is VOLATILE, so a subscription made after the reply was
    # published never sees it.
    : >"$RESPONSE_FILE"
    stdbuf -oL ros2 topic echo "$RESPONSE_TOPIC" \
        --no-daemon --qos-reliability reliable --qos-durability volatile \
        >"$RESPONSE_FILE" 2>"$RESPONSE_ERR" &
    LISTENER_PID=$!
    # Discovery is not instant, and a request published before the subscription
    # is matched is answered into nothing.
    sleep 3

    if ! kill -0 "$LISTENER_PID" 2>/dev/null; then
        fail "the response listener exited immediately: $(head -3 "$RESPONSE_ERR" 2>/dev/null | tr '\n' ' ')"
    else
        # --- Ask
        INVOCATION=$(( (RANDOM << 15 | RANDOM) + 1 ))
        REQUEST="{command_id: $END_SURGICAL_CASE, invocation_uuid: $INVOCATION,"
        REQUEST="$REQUEST source_id: $ENTITY_E_GUI, target_id: $ENTITY_SURGICAL_SEQUENCER, arguments: []}"
        # No --no-daemon here, unlike the echoes: `ros2 topic pub` does not take
        # that flag ("unrecognized arguments") and does not need it -- the
        # message type is spelled out on the command line, so nothing is asked
        # of the daemon that a dead one could answer wrongly.
        if ! ros2 topic pub -1 --qos-reliability reliable \
            "$REQUEST_TOPIC" polaris_interfaces/msg/CommandRequest "$REQUEST" >/dev/null 2>&1; then
            fail "could not publish END_SURGICAL_CASE on $REQUEST_TOPIC"
        else
            # --- Wait For The Answer To Our Invocation
            CODE=""
            WAITED=0
            while [ "$WAITED" -lt "$RESPONSE_TIMEOUT" ]; do
                CODE=$(response_status_code "$INVOCATION")
                [ -n "$CODE" ] && break
                sleep 1
                WAITED=$(( WAITED + 1 ))
            done
            stop_listener

            if [ -z "$CODE" ]; then
                fail "the sequencer did not answer invocation $INVOCATION within ${RESPONSE_TIMEOUT}s"
            else
                echo "POLARIS_END_CASE_STATUS_CODE: $CODE"

                # --- Did The Case Actually End
                AFTER=$(read_case_status)
                if [ -z "$AFTER" ]; then
                    fail "the command answered with status code $CODE, but no sample arrived on $STATE_TOPIC afterwards"
                else
                    echo "POLARIS_CASE_STATUS_AFTER: $AFTER"
                    if [ "$AFTER" -eq "$CASE_STATUS_UNDEFINED" ]; then
                        echo "POLARIS_END_CASE_OK: ended the case that was active (status $BEFORE), status code $CODE"
                    else
                        fail "the case is still active (status $AFTER) after a command that answered $CODE"
                    fi
                fi
            fi
        fi
    fi
    stop_listener
fi

# A single exit at the bottom: a script piped over SSH under `set -e` reports a
# mid-file exit as a failure of the whole pipe, whatever code it carried.
exit "$STATUS"
