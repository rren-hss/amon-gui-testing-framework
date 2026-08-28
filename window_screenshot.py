"""Screenshots an arbitrary on-screen window by title, without Squish.

For windows Squish has no AUT/object-map access to (e.g. Tech PC's rviz2,
which no suite registers as an attachable AUT) -- object.grabScreenshot()
inside a Squish test.py isn't an option, since that call needs a Squish
object handle. This captures at the X11 level instead: wmctrl locates the
window by title and reports its screen geometry, mss grabs those pixels
directly. Works whenever the target window shares an X display reachable
from wherever this runs -- true today because the Docker environment's
GUI containers share the host's X display (DISPLAY is bind-mounted in,
per CLAUDE.md), so this runs host-side with no remote hop. On physical
hardware, Tech PC is a separate machine, so this approach needs a real
remote call (SSH) instead -- not yet implemented.
"""

import subprocess
import time

import mss
from mss.tools import to_png

# How long to wait after raising a window before its content is trustworthy
# to screenshot -- mirrors SCREENSHOT_RENDER_DELAY_SECONDS in the Squish
# suites' test.py, same reasoning: the raise is asynchronous, so grabbing
# immediately can catch a partially-redrawn frame.
RAISE_SETTLE_SECONDS = 0.5


def _list_windows():
    """Returns [{"id", "x", "y", "width", "height", "title"}, ...] via wmctrl."""

    completed = subprocess.run(
        ["wmctrl", "-l", "-G"],
        capture_output=True,
        text=True,
        check=True,
    )

    windows = []

    for line in completed.stdout.splitlines():
        # wmctrl -l -G columns: id desktop x y width height client title...
        # (title itself may contain spaces, hence the maxsplit).
        parts = line.split(None, 7)

        if len(parts) < 8:
            continue

        window_id, _desktop, x, y, width, height, _client, title = parts

        windows.append({
            "id": window_id,
            "x": int(x),
            "y": int(y),
            "width": int(width),
            "height": int(height),
            "title": title,
        })

    return windows


def find_window(title_contains):
    """First window (wmctrl order) whose title contains title_contains,
    case-insensitive. Returns None if nothing matches."""

    needle = title_contains.lower()

    for window in _list_windows():
        if needle in window["title"].lower():
            return window

    return None


def capture_window(title_contains, output_path):
    """Screenshots the first window whose title contains title_contains,
    saving a PNG to output_path. Returns the matched window dict.

    Raises ValueError if no window matches.
    """

    window = find_window(title_contains)

    if window is None:
        raise ValueError(
            f"No window found with title containing {title_contains!r}"
        )

    # mss grabs raw pixels at a screen region, not "this window's content" --
    # whatever's visually on top at that geometry wins. Confirmed live on
    # 2026-08-28: without this, an overlapping Assistant/Surgeon GUI window
    # got captured instead of RViz underneath it. wmctrl -a sends an EWMH
    # _NET_ACTIVE_WINDOW request, which the host's Mutter honors (unlike
    # Qt's own raise()/requestActivate(), silently ignored by focus-stealing
    # prevention here -- see bring_to_front() in the Squish suites' test.py,
    # same fix for the same class of problem).
    try:
        subprocess.run(
            ["wmctrl", "-a", window["title"]],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        pass

    time.sleep(RAISE_SETTLE_SECONDS)

    with mss.mss() as screen_grabber:
        # wmctrl's reported geometry can extend past the virtual screen's
        # actual bounds -- observed live on 2026-08-28: an RViz window
        # reported 1403px tall starting at y=74 on a 1440px-tall screen,
        # i.e. 37px past the bottom edge. Grabbing past the edge raises an
        # X11 BadDrawable error, so clip to the combined virtual screen
        # (monitors[0], which spans every physical monitor).
        virtual_screen = screen_grabber.monitors[0]

        region = {
            "left": window["x"],
            "top": window["y"],
            "width": min(
                window["width"],
                virtual_screen["width"] - window["x"],
            ),
            "height": min(
                window["height"],
                virtual_screen["height"] - window["y"],
            ),
        }

        image = screen_grabber.grab(region)
        to_png(image.rgb, image.size, output=str(output_path))

    return window
