#!/usr/bin/env bash
# Manual operator tool: get a system's GUIs and system_manager back to a known
# state when the surgical sequence has advanced too far to repeat a GUI action
# against. Kills the GUIs, kills system_manager on the cart and cockpit,
# brings system_manager back up, then relaunches the GUIs.
#
# Deliberately does not touch perception. The surgical sequence state this
# script resets lives in cart/cockpit-side processes (system_manager's own
# cgroup there holds data_recorder, ros2_control_node, robot_state_publisher
# and friends) -- perception's system_manager instead runs the camera/AI
# pipeline (legolas, oct_helper_daemon, led_cli), which has nothing to do with
# sequence state, and restarting it costs real time (OCT warmup) and carries
# its own flaky startup-timeout risk unrelated to this script's actual job.
# The one thing perception's absence costs: the telecentric (tDM) video feed
# in assistant_gui/surgeon_gui streams from perception, so it will show
# "Reconnecting..."/"Video Signal Lost" until perception is restarted
# separately -- irrelevant unless whatever GUI action you're repeating
# depends on that feed specifically.
#
# Not part of the automated suite/pipeline and not run through
# harness/ssh.py's ssh_run_script(): every sudo command reads its password
# from SUDO_PASSWORD (see below) rather than a tty prompt, but that is still a
# secret this script deliberately does not carry itself -- ssh_run_script's
# scripts are meant to run unattended with nothing to supply, which is not
# true here.
#
# Usage: SUDO_PASSWORD=<password> scripts/reset_surgical_sequence.sh [system]
#   e.g. SUDO_PASSWORD=<password> scripts/reset_surgical_sequence.sh amon
#
# SUDO_PASSWORD is read from the environment, never written to this file or
# anywhere on disk: it is piped to each remote sudo -S over the SSH session's
# stdin, which is why -S is used at all -- unlike a password given as a
# command-line argument, stdin never shows up in a `ps` listing, local or
# remote. The residual risk this still carries, versus setting up passwordless
# sudo instead: the password sits in this shell's environment (and its
# history, if exported by hand rather than sourced from a file) for as long as
# the session lives, and nothing here confirms you meant to run with it set --
# accepted here because nothing on the amon machines themselves gets touched
# to make this work. Only required in physical mode -- see below.
#
# Environment detection: this script targets either the real Amon hardware
# (SSH + systemd, "physical") or the docker-cart/docker-cockpit dev containers
# ("docker") -- it auto-detects which by checking for running docker-cart/
# docker-cockpit containers first, falling back to an SSH reachability probe
# against <system>-cart/<system>-cockpit. Override the guess with
# RESET_MODE=docker or RESET_MODE=physical if auto-detection picks wrong (e.g.
# containers are up but you specifically want to test the physical rig, or
# vice versa).
#
# techpc (eng_gui + rviz2) is a pure ROS subscriber with no system_manager
# involved, and most test cases never look at it, so reset_docker prompts
# ("Restart techpc (eng_gui/rviz2) too? [y/N]") rather than always paying the
# cost -- reset_docker's process teardown/relaunch doesn't always leave
# rviz's subscriptions in a state that self-heals via DDS rediscovery, so
# say yes for cases that rely on watching motion in rviz. Pre-set
# RESTART_TECHPC=1 or =0 to skip the prompt for scripted/non-interactive runs.
#
# Set RESET_ASSUME_YES=1 to bypass the main "Continue?" confirmation
# (both modes) entirely -- baseline_reset.py's hard_reset() always sets
# this when the test framework triggers a reset via reset_before/
# reset_after, since a test case already opting into a reset is itself
# the decision; a second confirmation at the shell level would just block
# automation. Manual/interactive runs are unaffected by default.
set -euo pipefail

SYSTEM="${1:-amon}"

CART="${SYSTEM}-cart"
COCKPIT="${SYSTEM}-cockpit"

DOCKER_CART_CONTAINER="docker-cart"
DOCKER_COCKPIT_CONTAINER="docker-cockpit"
DOCKER_TECHPC_CONTAINER="docker-techpc"

# Left unset by default -- see the techpc note above. reset_docker prompts
# for this interactively when it's unset, so scripted/automated callers can
# still bypass the prompt by pre-setting RESTART_TECHPC=1 or 0.

CART_GUI_UNITS="cart_gui.service assistant_gui.service"
COCKPIT_GUI_UNITS="surgeon_gui.service"

# 45s (was 15s): confirmed via src/common/app/include/application_bootstrap.hpp
# that these apps do a designed graceful SIGTERM -> flag flip -> run-loop
# exit -> RAII destructor -> clean rclcpp/DDS shutdown. SIGKILL bypasses that
# entirely (can't be caught, destructors never run, no DDS goodbye sent) --
# confirmed live on 2026-08-24 that escalating to SIGKILL after only 15s is
# what actually caused the DDS ghost-registration problem, not the graceful
# path itself. Giving SIGTERM more room before ever escalating (docker mode's
# wait_for_stopped) is the fix; reset_physical only warns at this timeout
# rather than escalating, so this also just delays a possibly-premature
# warning there, not a behavior change.
WAIT_TIMEOUT_SECONDS=45
VERIFY_TIMEOUT_SECONDS=20
SSH_PROBE_TIMEOUT_SECONDS=5

confirm() {
    # RESET_ASSUME_YES bypasses the prompt entirely -- set unconditionally
    # by baseline_reset.py's hard_reset() whenever the test framework
    # invokes this script, since reaching that point already means a test
    # case explicitly requested the reset (reset_before/reset_after: True
    # in tests.py). A human confirming again at that point isn't adding
    # safety, just blocking automation. Manual/interactive use (running
    # this script directly from a terminal) is unaffected by default --
    # RESET_ASSUME_YES is only set by that one caller.
    if [ "${RESET_ASSUME_YES:-0}" = "1" ]; then
        echo "$1 [auto-confirmed via RESET_ASSUME_YES]"
        return 0
    fi

    read -r -p "$1 [y/N] " reply
    case "$reply" in
        y|Y) return 0 ;;
        *) echo "Aborted." >&2; exit 1 ;;
    esac
}

# Checks docker-cart/docker-cockpit first (cheap, no network round-trip), then
# falls back to probing SSH reachability against the physical hostnames. Never
# raises under set -e on its own -- every check here is allowed to fail, the
# caller decides what "neither detected" means.
detect_mode() {
    if command -v docker >/dev/null 2>&1; then
        local cart_running cockpit_running
        cart_running=$(docker inspect -f '{{.State.Running}}' "$DOCKER_CART_CONTAINER" 2>/dev/null || echo "false")
        cockpit_running=$(docker inspect -f '{{.State.Running}}' "$DOCKER_COCKPIT_CONTAINER" 2>/dev/null || echo "false")

        if [ "$cart_running" = "true" ] && [ "$cockpit_running" = "true" ]; then
            echo "docker"
            return 0
        fi
    fi

    if ssh -o BatchMode=yes -o ConnectTimeout="$SSH_PROBE_TIMEOUT_SECONDS" "$CART" true 2>/dev/null \
        && ssh -o BatchMode=yes -o ConnectTimeout="$SSH_PROBE_TIMEOUT_SECONDS" "$COCKPIT" true 2>/dev/null; then
        echo "physical"
        return 0
    fi

    echo "unknown"
    return 0
}

# --------------------------------------------------------------------------
# Physical mode: SSH + systemd, against the real Amon cart/cockpit hardware.
# --------------------------------------------------------------------------
reset_physical() {
    : "${SUDO_PASSWORD:?SUDO_PASSWORD must be set for physical mode, e.g. SUDO_PASSWORD=<password> $0 amon}"

    # Units this run started that did not end up active, collected so the
    # summary at the end cannot be missed the way amon-cart's system_manager
    # failure was on 2026-08-14 -- systemctl start reported success
    # immediately (the job was dispatched, the process forked) while the unit
    # crash-looped and landed in failed a few restarts later, entirely after
    # the command had already returned.
    local FAILURES=()

    # Every call site passes a command already prefixed "sudo -S -p ''" -- -S
    # reads the password from stdin instead of prompting the tty, and -p ''
    # drops sudo's own "[sudo] password for ...:" prompt text, which would
    # otherwise print even though nothing is waiting to read it interactively.
    # Piping SUDO_PASSWORD in on this ssh call's stdin, once per command, is
    # what -S reads. BatchMode=yes now that nothing needs an interactive
    # prompt -- it also makes a hung command fail fast instead of hanging on
    # one, unlike the earlier -t version.
    run() {
        local host="$1"; shift
        echo "+ ${host}: $*"
        printf '%s\n' "$SUDO_PASSWORD" | ssh -o BatchMode=yes "$host" "$*"
    }

    # systemctl kill sends the signal and returns; it does not wait for the
    # unit to actually finish exiting. Starting the next thing before it has
    # is a race against systemd's own Restart=on-failure on these units,
    # which can relaunch a just-killed process before this script's own
    # "start" step ever runs. Polling for it to report inactive first closes
    # that race.
    wait_for_down() {
        local host="$1"; shift
        local units="$*"
        echo "  waiting for ${units} to stop on ${host}..."
        for _ in $(seq 1 "$WAIT_TIMEOUT_SECONDS"); do
            if ! ssh -o BatchMode=yes "$host" "systemctl is-active --quiet ${units}" 2>/dev/null; then
                return 0
            fi
            sleep 1
        done
        echo "  warning: ${units} on ${host} still reports active after ${WAIT_TIMEOUT_SECONDS}s -- continuing anyway" >&2
    }

    # systemctl start's own exit code only reflects whether the job was
    # dispatched, not whether the unit is still up moments later -- a unit
    # with Restart=on-failure can crash-loop and land in failed well after
    # that command returned. This polls for the unit to settle into active
    # or failed and reports which one plainly, rather than trusting the
    # start command alone.
    verify_active() {
        local host="$1"; shift
        local units="$1"
        local unit status
        for unit in $units; do
            status="unknown"
            for _ in $(seq 1 "$VERIFY_TIMEOUT_SECONDS"); do
                status=$(ssh -o BatchMode=yes "$host" "systemctl is-active ${unit}" 2>/dev/null || true)
                case "$status" in
                    active|failed) break ;;
                esac
                sleep 1
            done
            if [ "$status" = "active" ]; then
                echo "  OK: ${unit} is active on ${host}"
            else
                echo "  NOT ACTIVE: ${unit} on ${host} is '${status}' -- see: ssh ${host} systemctl status ${unit}" >&2
                FAILURES+=("${host}: ${unit} (${status})")
            fi
        done
    }

    # A unit that is failed -- especially start-limit-hit -- will not accept
    # a fresh start attempt at all until this runs. Both failure modes we hit
    # on 2026-08-17 land here: amon-cockpit's system_manager got
    # start-limit-hit from this script's own repeated kill/restart cycles
    # during testing, and amon-perception's hit a genuine startup timeout and
    # crash-looped to failed. Either way, this must run before every start or
    # that start just adds another failed attempt to the same limiter
    # instead of clearing it.
    reset_failed() {
        local host="$1"; shift
        run "$host" "sudo -S -p '' systemctl reset-failed $*" || true
    }

    # The GUI units BindsTo=polaris-openbox.service (they need the window
    # manager to render into) but do not Requires= it -- confirmed via
    # `systemctl show surgeon_gui.service -p Requires -p BindsTo` on
    # 2026-08-17, which lists polaris-openbox.service under BindsTo but not
    # under Requires. That means starting a GUI unit does not pull openbox up
    # as a dependency the way Requires= would; on a machine that is down to
    # zero, openbox included, starting the GUIs without this leaves them
    # bound to a window manager that never launches.
    ensure_openbox() {
        local host="$1"
        local status
        status=$(ssh -o BatchMode=yes "$host" "systemctl is-active polaris-openbox.service" 2>/dev/null || true)
        if [ "$status" = "active" ]; then
            echo "  polaris-openbox.service already active on ${host}"
            return 0
        fi
        echo "  polaris-openbox.service is '${status}' on ${host} -- starting it"
        reset_failed "$host" "polaris-openbox.service"
        run "$host" "sudo -S -p '' systemctl start polaris-openbox.service" || true
        verify_active "$host" "polaris-openbox.service"
    }

    echo "This will kill and restart system_manager and the GUIs on ${CART} and ${COCKPIT}. perception is not touched."
    confirm "Continue?"

    # systemctl kill exits non-zero on a unit that is not currently loaded --
    # already not running is the goal of a kill step, not a failure of it, so
    # that must not abort the rest of the reset under set -e.
    echo "== 1. Killing the GUIs =="
    run "$CART" "sudo -S -p '' systemctl kill ${CART_GUI_UNITS}" || true
    run "$COCKPIT" "sudo -S -p '' systemctl kill ${COCKPIT_GUI_UNITS}" || true

    echo "== 2. Killing system_manager on the cart and cockpit =="
    run "$CART" "sudo -S -p '' systemctl kill system_manager.service" || true
    run "$COCKPIT" "sudo -S -p '' systemctl kill system_manager.service" || true

    wait_for_down "$CART" "system_manager.service ${CART_GUI_UNITS}"
    wait_for_down "$COCKPIT" "system_manager.service ${COCKPIT_GUI_UNITS}"

    # A unit that fails to start at all (e.g. a missing unit file) makes this
    # command itself return non-zero, same as a unit that starts and then
    # crash-loops later does not -- verify_active below is what actually
    # reports either case, so this must not abort the reset under set -e
    # before it runs.
    echo "== 3. Starting system_manager on the cart and cockpit =="
    reset_failed "$CART" "system_manager.service"
    reset_failed "$COCKPIT" "system_manager.service"
    run "$CART" "sudo -S -p '' systemctl start system_manager.service" || true
    run "$COCKPIT" "sudo -S -p '' systemctl start system_manager.service" || true

    verify_active "$CART" "system_manager.service"
    verify_active "$COCKPIT" "system_manager.service"

    echo "== 4. Starting the GUIs =="
    ensure_openbox "$CART"
    ensure_openbox "$COCKPIT"

    reset_failed "$CART" "${CART_GUI_UNITS}"
    reset_failed "$COCKPIT" "${COCKPIT_GUI_UNITS}"
    run "$CART" "sudo -S -p '' systemctl start ${CART_GUI_UNITS}" || true
    run "$COCKPIT" "sudo -S -p '' systemctl start ${COCKPIT_GUI_UNITS}" || true

    verify_active "$CART" "$CART_GUI_UNITS"
    verify_active "$COCKPIT" "$COCKPIT_GUI_UNITS"

    cat <<'EOF'

Done.

If Squish needs to attach to these GUIs afterward: cart_gui.service's own
drop-in (/etc/systemd/system/cart_gui.service.d/override.conf) was found with
an empty Environment= on 2026-08-14, which means the unit is not currently
injecting LD_PRELOAD=libsquishqtpre.so / SQUISH_ATTACHABLE_PORT on its own.
If that is still the case, the GUIs this script just started are not
attachable until that is set (or whatever manual step normally does it is
run) -- confirm before assuming a Squish preflight will find them.
EOF

    if [ "${#FAILURES[@]}" -gt 0 ]; then
        echo
        echo "${#FAILURES[@]} unit(s) did not come up active:"
        printf '  %s\n' "${FAILURES[@]}"
        exit 1
    fi
}

# --------------------------------------------------------------------------
# Docker mode: docker-cart/docker-cockpit dev containers.
# --------------------------------------------------------------------------
reset_docker() {
    # Confirmed on docker-cart on 2026-08-24 via `ps afx` + `ps -o pid,ppid,pgid,cmd`
    # + reading run_cart.bash: there is no systemd/supervisor in these
    # containers. run_cart.bash directly launches system_manager
    # (--nodetach-children) and both GUIs as three sibling processes, then
    # blocks in wait_all. system_manager and every ROS node it spawns
    # (ros2_control_node, data_recorder, surgical_sequencer, ...) share ONE
    # process group -- confirmed by matching PGIDs -- so killing that group
    # in one shot tears down the whole subtree cleanly, no orphans. The GUIs
    # are launched via Squish's own `startaut`, which execs straight into the
    # target binary -- the appCart/appAssist PID in `ps afx` IS the real
    # process, nothing wrapping it left to chase separately.
    #
    # The cockpit half (run_cockpit.bash, the surgeon_gui binary name) is
    # MIRRORED from the cart pattern by naming convention, not independently
    # confirmed the way the cart side was -- verify before trusting it.
    local CART_LAUNCHER="/workspace/install/polaris_scripts/run_cart.bash"
    local COCKPIT_LAUNCHER="/workspace/install/polaris_scripts/run_cockpit.bash"
    local TECHPC_LAUNCHER="/workspace/install/polaris_scripts/run_techpc.bash"

    local CART_GUI_PATTERNS=("/cart_gui/bin/appCart" "/assistant_gui/bin/appAssist")
    local COCKPIT_GUI_PATTERNS=("/surgeon_gui/bin/appSurgeon")
    # techpc has no system_manager -- run_techpc.bash launches these two
    # directly, nothing else to track.
    local TECHPC_PATTERNS=("/eng_gui/bin/appEng" "rviz2")

    # Every known component binary/script pattern, observed directly via
    # `ps afx` on both containers. NOT just system_manager: an earlier
    # tree-walk-from-system_manager design (kill system_manager, then chase
    # its live descendants) had a fatal blind spot found live on 2026-08-24 --
    # any child that outlives its parent even briefly gets orphaned (PPID=1),
    # and an orphan is structurally invisible to any future re-walk rooted at
    # "whatever system_manager currently exists" -- it can never be found or
    # killed again, and accumulates across every subsequent reset. Killing by
    # pattern directly (pkill -f, same proven approach as the GUIs) finds a
    # match regardless of whether it's parented under a live tree or already
    # orphaned, so nothing can hide this way. Tradeoff: this list needs a new
    # entry if a genuinely new component type shows up in `ps afx` that isn't
    # covered by an existing pattern.
    local SYSTEM_MANAGER_PATTERN="system_manager/bin/system_manager"
    local CART_COMPONENT_PATTERNS=(
        "$SYSTEM_MANAGER_PATTERN"
        "teleop/bin/teleop"
        "surgical_sequencer/bin/surgical_sequencer"
        "surgical_feature_sim"
        "motion_planning/lib/motion_planning"
        "data_recorder/bin/data_recorder"
        "config_manager/lib/config_manager"
        "environment_marker_publisher"
        "ros2_control_node"
        "controller_manager/spawner"
        "moveit_ros_move_group/move_group"
        "robot_state_publisher"
        "ros2 launch control_layer_cart"
        "run_config_mgr"
    )

    # Confirmed via source (src/robotics-image-guidance/control_mux/src/main.cpp)
    # and live testing on 2026-08-24: these two never respond to SIGTERM --
    # control_mux just polls `while (rclcpp::ok())`, never observed to flip
    # after 45s of waiting either. Waiting any amount of time for them is
    # pure waste when running many cases in sequence, since the outcome
    # (SIGKILL) is identical whether you wait 5s or 45s -- so skip SIGTERM
    # and the wait loop entirely and go straight to SIGKILL for just these.
    local CART_FORCE_KILL_PATTERNS=(
        "control_mux/bin/control_mux"
        "surgical_planner/bin/rtmod_surgical_planner"
    )
    local COCKPIT_COMPONENT_PATTERNS=(
        "$SYSTEM_MANAGER_PATTERN"
        "data_recorder/bin/data_recorder"
        "config_manager/lib/config_manager"
        "ros2_control_node"
        "controller_manager/spawner"
        "robot_state_publisher"
        "ros2 launch control_layer_cockpit"
        "run_config_mgr"
    )

    local FAILURES=()

    # Kills every process matching a command-line pattern inside a
    # container, regardless of its position (or lack of one) in any process
    # tree. pkill signals every matching process in one call, so this is
    # also safe against an already-duplicated mess.
    kill_by_pattern() {
        local container="$1" pattern="$2" signal="${3:-TERM}"
        if ! docker exec "$container" pkill -0 -f "$pattern" 2>/dev/null; then
            echo "  ${container}: no process matching '${pattern}' -- already stopped"
            return 0
        fi
        echo "  ${container}: sending SIG${signal} to process(es) matching '${pattern}'"
        docker exec "$container" pkill "-${signal}" -f "$pattern" 2>/dev/null || true
    }

    # Mirrors reset_physical's wait_for_down, but unlike it, actually
    # escalates instead of just warning: SIGTERM is given WAIT_TIMEOUT_SECONDS
    # to work (ROS/MoveIt shutdown can legitimately take a while), but if
    # anything matching the pattern is still alive after that, this sends
    # SIGKILL and waits again -- guaranteeing a clean slate before relaunching
    # is what actually prevents a second instance getting stacked on top of
    # a first one that didn't die in time.
    wait_for_stopped() {
        local container="$1" pattern="$2"
        echo "  waiting for '${pattern}' to stop in ${container}..."
        for _ in $(seq 1 "$WAIT_TIMEOUT_SECONDS"); do
            if ! docker exec "$container" pkill -0 -f "$pattern" 2>/dev/null; then
                return 0
            fi
            sleep 1
        done

        echo "  '${pattern}' in ${container} still running after ${WAIT_TIMEOUT_SECONDS}s -- escalating to SIGKILL" >&2
        kill_by_pattern "$container" "$pattern" "KILL"

        for _ in $(seq 1 5); do
            if ! docker exec "$container" pkill -0 -f "$pattern" 2>/dev/null; then
                return 0
            fi
            sleep 1
        done
        echo "  warning: '${pattern}' in ${container} still running after SIGKILL -- giving up, it may end up orphaned" >&2
    }

    # Mirrors reset_physical's verify_active: polls for the process to
    # actually reappear after relaunch, rather than trusting that the
    # detached `docker exec -d` returning means anything about the process
    # itself having come up.
    verify_running() {
        local container="$1" label="$2" pattern="$3"
        for _ in $(seq 1 "$VERIFY_TIMEOUT_SECONDS"); do
            if docker exec "$container" pkill -0 -f "$pattern" 2>/dev/null; then
                echo "  OK: ${label} is running in ${container}"
                return 0
            fi
            sleep 1
        done
        echo "  NOT RUNNING: ${label} in ${container} (pattern '${pattern}')" >&2
        FAILURES+=("${container}: ${label}")
    }

    # Prompt only when the caller hasn't already decided (RESTART_TECHPC
    # unset) -- lets a script pre-set it to 1 or 0 and skip the prompt.
    if [ -z "${RESTART_TECHPC+x}" ]; then
        read -r -p "Restart techpc (eng_gui/rviz2) too? [y/N] " techpc_reply
        case "$techpc_reply" in
            y|Y) RESTART_TECHPC=1 ;;
            *) RESTART_TECHPC=0 ;;
        esac
    fi

    local techpc_msg=""
    [ "$RESTART_TECHPC" = "1" ] && techpc_msg=" and ${DOCKER_TECHPC_CONTAINER}"
    echo "This will kill and restart system_manager and the GUIs in ${DOCKER_CART_CONTAINER} and ${DOCKER_COCKPIT_CONTAINER}${techpc_msg}."
    confirm "Continue?"

    echo "== 1. Killing the GUIs =="
    for pattern in "${CART_GUI_PATTERNS[@]}"; do
        kill_by_pattern "$DOCKER_CART_CONTAINER" "$pattern"
    done
    for pattern in "${COCKPIT_GUI_PATTERNS[@]}"; do
        kill_by_pattern "$DOCKER_COCKPIT_CONTAINER" "$pattern"
    done
    if [ "$RESTART_TECHPC" = "1" ]; then
        for pattern in "${TECHPC_PATTERNS[@]}"; do
            kill_by_pattern "$DOCKER_TECHPC_CONTAINER" "$pattern"
        done
    fi

    echo "== 2. Killing system_manager and every known component on cart and cockpit =="
    for pattern in "${CART_COMPONENT_PATTERNS[@]}"; do
        kill_by_pattern "$DOCKER_CART_CONTAINER" "$pattern"
    done
    for pattern in "${COCKPIT_COMPONENT_PATTERNS[@]}"; do
        kill_by_pattern "$DOCKER_COCKPIT_CONTAINER" "$pattern"
    done
    # Known non-graceful: skip SIGTERM, go straight to SIGKILL, no wait.
    for pattern in "${CART_FORCE_KILL_PATTERNS[@]}"; do
        kill_by_pattern "$DOCKER_CART_CONTAINER" "$pattern" "KILL"
    done

    for pattern in "${CART_GUI_PATTERNS[@]}" "${CART_COMPONENT_PATTERNS[@]}"; do
        wait_for_stopped "$DOCKER_CART_CONTAINER" "$pattern"
    done
    for pattern in "${COCKPIT_GUI_PATTERNS[@]}" "${COCKPIT_COMPONENT_PATTERNS[@]}"; do
        wait_for_stopped "$DOCKER_COCKPIT_CONTAINER" "$pattern"
    done
    if [ "$RESTART_TECHPC" = "1" ]; then
        for pattern in "${TECHPC_PATTERNS[@]}"; do
            wait_for_stopped "$DOCKER_TECHPC_CONTAINER" "$pattern"
        done
    fi

    # -d (detach) is required, not optional: run_cart.bash/run_cockpit.bash
    # block in wait_all() for as long as the processes they launched stay
    # up, which is indefinitely -- a foreground `docker exec` here would
    # just hang this script forever.
    #
    # -u is required too: without it, `docker exec` defaults to root (the
    # image's default user), bypassing docker-entrypoint.sh's gosu-based
    # privilege drop entirely (that only applies to the container's PID 1).
    # A root-run stack leaves every log/pid/install file it touches
    # root-owned -- breaking the next rren-run process that needs to write
    # there -- and on cockpit specifically, ros2_control_node fails to come
    # up at all when launched this way.
    local uid="${SQUISH_CONTAINER_UID:-1000}"
    local gid="${SQUISH_CONTAINER_GID:-1000}"
    echo "== 3. Relaunching cart and cockpit (system_manager + GUIs together, via their launcher scripts) =="
    docker exec -d -u "${uid}:${gid}" "$DOCKER_CART_CONTAINER" bash "$CART_LAUNCHER"
    docker exec -d -u "${uid}:${gid}" "$DOCKER_COCKPIT_CONTAINER" bash "$COCKPIT_LAUNCHER"
    if [ "$RESTART_TECHPC" = "1" ]; then
        docker exec -d -u "${uid}:${gid}" "$DOCKER_TECHPC_CONTAINER" bash "$TECHPC_LAUNCHER"
    fi

    echo "== 4. Verifying =="
    verify_running "$DOCKER_CART_CONTAINER" "system_manager" "$SYSTEM_MANAGER_PATTERN"
    for pattern in "${CART_GUI_PATTERNS[@]}"; do
        verify_running "$DOCKER_CART_CONTAINER" "$pattern" "$pattern"
    done
    verify_running "$DOCKER_COCKPIT_CONTAINER" "system_manager" "$SYSTEM_MANAGER_PATTERN"
    for pattern in "${COCKPIT_GUI_PATTERNS[@]}"; do
        verify_running "$DOCKER_COCKPIT_CONTAINER" "$pattern" "$pattern"
    done
    if [ "$RESTART_TECHPC" = "1" ]; then
        for pattern in "${TECHPC_PATTERNS[@]}"; do
            verify_running "$DOCKER_TECHPC_CONTAINER" "$pattern" "$pattern"
        done
    fi

    # verify_running above only proves the process exists -- it says nothing
    # about whether the ROS graph inside it has actually finished matching.
    # Confirmed live: starting a case immediately after "Done" can beat
    # control_mux to having matched cart's and cockpit's controller_manager
    # services, so its controller-set switch for DRAPING silently times out
    # (control_mux itself waits only 3s per call, no internal readiness
    # wait of its own -- see controller_manager_client.cpp). Neither GUI
    # surfaces that failure (see CaseSetup.qml's own comment acknowledging
    # this exact race), so it just reads as "stuck on Moving to Draping" a
    # few seconds to tens of seconds after a reset, self-resolving once the
    # graph settles. Waiting for the actual services here, not a fixed
    # sleep, is what makes "Done" mean "safe to start a case."
    # Always queried from cart, regardless of which side the service
    # logically belongs to -- the DDS domain is shared, so cart sees
    # cockpit's services fine, but confirmed live that cockpit's own
    # ros2cli daemon can get stuck ("!rclpy.ok()") and give false
    # negatives for its own services. Cart's has been reliable all
    # session; querying from one consistent, known-good place avoids that.
    wait_for_service() {
        local label="$1" service="$2" timeout="${3:-30}"
        for _ in $(seq 1 "$timeout"); do
            if docker exec "$DOCKER_CART_CONTAINER" bash -c \
                'source /opt/ros/humble/setup.bash >/dev/null 2>&1; ros2 service list 2>/dev/null' \
                | grep -qx "$service"; then
                echo "  OK: ${label} (${service}) is ready"
                return 0
            fi
            sleep 1
        done
        echo "  NOT READY: ${label} (${service}) did not appear within ${timeout}s" >&2
        FAILURES+=("${label}: ROS graph not ready")
    }

    echo "== 5. Waiting for the ROS control graph to settle =="
    wait_for_service "cart controller_manager" "/controller_manager/list_controllers"
    wait_for_service "cockpit controller_manager" "/cockpit/controller_manager/list_controllers"
    wait_for_service "control_mux" "/control_mux/switch_controller_set"

    # Per polaris_docker_squish_runbook.html section 11 ("Correct runtime
    # order"): scripts/common.bash's shutdown() kills squishserver as a side
    # effect of restarting run_cart.bash/run_cockpit.bash (step 3 above), so
    # without this, every attach/preflight after a reset fails with "Peer
    # closed the connection during handshake" even though everything else
    # came back up fine -- confirmed the hard way tonight.
    restart_squishserver() {
        local container="$1"; shift
        local squish_root="/horizon/thirdparty/squish/9.2.2"
        local uid="${SQUISH_CONTAINER_UID:-1000}"
        local gid="${SQUISH_CONTAINER_GID:-1000}"
        local home_dir log_dir ready

        home_dir=$(docker exec "$container" getent passwd "$uid" | cut -d: -f6)
        log_dir="${home_dir}/.squish"

        echo "  ${container}: restarting squishserver"
        docker exec -u "${uid}:${gid}" "$container" mkdir -p "$log_dir"
        docker exec -u "${uid}:${gid}" "$container" \
            "${squish_root}/bin/squishserver" \
            --port 4322 --daemon \
            --logfile "${log_dir}/squishserver-4322.log"

        ready=0
        for _ in $(seq 1 10); do
            if docker exec -u "${uid}:${gid}" "$container" \
                "${squish_root}/bin/squishrunner" \
                --host localhost --port 4322 --info attachableApplications \
                > /dev/null 2>&1; then
                ready=1
                break
            fi
            sleep 1
        done

        if [ "$ready" -ne 1 ]; then
            echo "  NOT RUNNING: squishserver in ${container} did not come up within 10s" >&2
            FAILURES+=("${container}: squishserver")
            return 0
        fi

        # Registrations persist under the /home volume, so re-adding them
        # is usually redundant, but it's idempotent and cheap -- simpler
        # than detecting whether it's already there.
        while [ "$#" -ge 2 ]; do
            local alias="$1" target="$2"
            shift 2
            docker exec -u "${uid}:${gid}" "$container" \
                "${squish_root}/bin/squishrunner" \
                --host localhost --port 4322 \
                --config addAttachableAUT "$alias" "$target"
        done
    }

    echo "== 6. Restarting squishserver (killed as a side effect of step 3) =="
    restart_squishserver "$DOCKER_CART_CONTAINER" cart_gui localhost:9999 assistant_gui localhost:9997
    restart_squishserver "$DOCKER_COCKPIT_CONTAINER" surgeon_gui localhost:9998

    echo
    echo "Done."

    if [ "${#FAILURES[@]}" -gt 0 ]; then
        echo
        echo "${#FAILURES[@]} process(es) did not come back up:"
        printf '  %s\n' "${FAILURES[@]}"
        exit 1
    fi
}

MODE="${RESET_MODE:-}"

if [ -z "$MODE" ]; then
    echo "Detecting environment..."
    MODE=$(detect_mode)
fi

case "$MODE" in
    docker)
        echo "Detected environment: docker (${DOCKER_CART_CONTAINER}/${DOCKER_COCKPIT_CONTAINER})"
        reset_docker
        ;;
    physical)
        echo "Detected environment: physical (${CART}/${COCKPIT})"
        reset_physical
        ;;
    *)
        cat >&2 <<EOF
Could not detect environment: neither ${DOCKER_CART_CONTAINER}/${DOCKER_COCKPIT_CONTAINER}
are running, nor is ${CART}/${COCKPIT} reachable over SSH.

Start the docker containers, or check SSH/hostname setup for the physical
hardware, or override the guess with RESET_MODE=docker or RESET_MODE=physical.
EOF
        exit 1
        ;;
esac
