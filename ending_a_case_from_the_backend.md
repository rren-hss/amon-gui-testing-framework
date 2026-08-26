# Ending a surgical case when the GUI can't

## The problem

Once a surgical case reaches the draping position, nothing in the shipped GUIs
can end it. Logout doesn't clear it, Case Setup stays locked, and the cart shows
no end-case control (Edit Case appears one step later at docking; appEng's "End
Case" isn't deployed on any rig). So a case left by one run breaks the next.

## The workaround

Talk to the surgical sequencer directly on the ROS 2 command bus:

1. Read `/surgical_state` (`current_case.status`). If already UNDEFINED (0),
   do nothing -- makes it idempotent.
2. Subscribe to `/command_responses` **before** publishing -- it's
   RELIABLE/VOLATILE, so a late subscription misses the reply. Sleep ~3s for
   discovery, then send.
3. Publish `END_SURGICAL_CASE` on `/command_requests`
   (`polaris_interfaces/msg/CommandRequest`): `command_id: 60`, `source_id: 5`
   (e_gui), `target_id: 13` (surgical_sequencer), random `invocation_uuid`.
4. Match the reply by invocation id, read its `status_code`.
5. Read the status back -- accepted and actually-ended are different claims.

The sequencer accepts it when a case is ongoing and no arm has motion engaged; it
refuses (BAD_COMMAND) both with no case and with a client controlling an arm,
which is why step 1 reads status first.

**Two gotchas:** ending the case does *not* reset `current_surgical_step_id`, so
if surgery had started the cart GUI stays stranded on its active-case screen and
needs a reboot (perception, cockpit, cart last). And `ros2 topic echo` needs
`--no-daemon` with QoS spelled out or a dead ros2cli daemon captures nothing;
`ros2 topic pub` rejects `--no-daemon` and doesn't need it.

Full reference: `scripts/end_surgical_case.sh`.

## Stopgap

This is the suite's one deliberate go-round-the-GUI. A green run doesn't prove a
person could recover by hand. GitHub #166 / PS3-3346 asks for an end-case control
at draping; when it lands this is replaced by a GUI click.

## Drop-in

### Bash

```bash
# Ends the active surgical case via the command bus. Run on the cart.
# Returns 0 if a case was ended or none was active, 1 otherwise.
end_surgical_case() {
    local resp=/dev/shm/end_case_resp.yaml
    local inv=$(( (RANDOM << 15 | RANDOM) + 1 ))

    source /opt/ros/humble/setup.bash
    source /horizon/polaris/setup.bash

    local before
    before=$(timeout 15 ros2 topic echo /surgical_state --once --no-daemon \
        --qos-reliability best_effort --qos-durability volatile \
        --field current_case.status 2>/dev/null | head -1 | tr -dc '0-9')
    [ "$before" = 0 ] && { echo "no case active"; return 0; }

    : >"$resp"
    stdbuf -oL ros2 topic echo /command_responses --no-daemon \
        --qos-reliability reliable --qos-durability volatile >"$resp" 2>/dev/null &
    local listener=$!
    sleep 3

    ros2 topic pub -1 --qos-reliability reliable /command_requests \
        polaris_interfaces/msg/CommandRequest \
        "{command_id: 60, invocation_uuid: $inv, source_id: 5, target_id: 13, arguments: []}" \
        >/dev/null 2>&1

    local waited=0 code=""
    while [ "$waited" -lt 15 ]; do
        code=$(awk -v u="$inv" '
            /^---$/ { delete b; next }
            /invocation_uuid:/ { b["u"]=$2 }
            /status_code:/ { b["c"]=$2 }
            b["u"]==u && "c" in b { print b["c"]; exit }' "$resp")
        [ -n "$code" ] && break
        sleep 1; waited=$(( waited + 1 ))
    done
    kill "$listener" 2>/dev/null; wait "$listener" 2>/dev/null

    local after
    after=$(timeout 15 ros2 topic echo /surgical_state --once --no-daemon \
        --qos-reliability best_effort --qos-durability volatile \
        --field current_case.status 2>/dev/null | head -1 | tr -dc '0-9')
    [ "$after" = 0 ] && { echo "ended (code $code)"; return 0; }
    echo "still active (status $after, code $code)"; return 1
}
```

### Python (rclpy)

```python
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from polaris_interfaces.msg import CommandRequest, CommandResponse, SurgicalState
import random, time

END_SURGICAL_CASE, E_GUI, SURGICAL_SEQUENCER = 60, 5, 13

def end_surgical_case(timeout=15.0):
    """End the active surgical case via the command bus. Run on the cart.
    Returns True if a case was ended or none was active."""
    rclpy.init()
    node = Node("end_surgical_case")
    reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                          durability=DurabilityPolicy.VOLATILE)
    best_effort = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                             durability=DurabilityPolicy.VOLATILE)

    state = {"status": None}
    node.create_subscription(SurgicalState, "/surgical_state",
                             lambda m: state.update(status=m.current_case.status), best_effort)

    responses = {}
    node.create_subscription(CommandResponse, "/command_responses",
                             lambda m: responses.setdefault(m.invocation_uuid, m.status_code), reliable)

    def status(deadline=5.0):
        end = time.time() + deadline
        while state["status"] is None and time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.2)
        return state["status"]

    try:
        if status() == 0:
            return True  # no case active

        # Subscription is up (created above); let discovery settle before publishing.
        pub = node.create_publisher(CommandRequest, "/command_requests", reliable)
        time.sleep(3)
        inv = random.getrandbits(30) + 1
        pub.publish(CommandRequest(command_id=END_SURGICAL_CASE, invocation_uuid=inv,
                                   source_id=E_GUI, target_id=SURGICAL_SEQUENCER, arguments=[]))

        end = time.time() + timeout
        while inv not in responses and time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.2)

        state["status"] = None
        return status() == 0
    finally:
        node.destroy_node()
        rclpy.shutdown()
```
