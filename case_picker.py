import curses


def _draw(stdscr, test_steps, cursor, selected_ids):
    stdscr.erase()

    stdscr.addstr(
        0, 0,
        "Select test cases to run "
        "(up/down: move, space: toggle, enter: run, q: quit)",
    )

    for row, test_case in enumerate(test_steps):
        marker = "[x]" if test_case["id"] in selected_ids else "[ ]"
        line = f"{marker} {test_case['id']} - {test_case['name']}"
        attr = curses.A_REVERSE if row == cursor else curses.A_NORMAL

        try:
            stdscr.addstr(row + 2, 0, line, attr)
        except curses.error:
            pass

    stdscr.refresh()


def _run_picker(stdscr, test_steps):
    curses.curs_set(0)
    stdscr.keypad(True)

    cursor = 0
    selected_ids = set()

    while True:
        _draw(stdscr, test_steps, cursor, selected_ids)
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = (cursor - 1) % len(test_steps)
        elif key == curses.KEY_DOWN:
            cursor = (cursor + 1) % len(test_steps)
        elif key == ord(" "):
            case_id = test_steps[cursor]["id"]
            if case_id in selected_ids:
                selected_ids.discard(case_id)
            else:
                selected_ids.add(case_id)
        elif key == ord("q"):
            return None
        elif key in (curses.KEY_ENTER, 10, 13):
            return [
                test_case
                for test_case in test_steps
                if test_case["id"] in selected_ids
            ]


def pick_test_cases(test_steps):
    """Interactive terminal checklist for selecting test cases to run.

    Returns the list of selected test-case dicts, an empty list if the
    operator confirmed with nothing checked, or None if they quit with 'q'.
    """
    return curses.wrapper(_run_picker, test_steps)
