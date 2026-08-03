import tkinter as tk
from tkinter import messagebox, filedialog

# --- palette (dark surface theme) ---
BG_PAGE = "#141414"
BG_CARD = "#1e1e1e"
BORDER = "#333333"
BORDER_STRONG = "#454545"
TEXT_PRIMARY = "#eaeaea"
TEXT_SECONDARY = "#a0a0a0"
TEXT_MUTED = "#707070"
SUCCESS = "#4fb583"
DANGER = "#e05a5a"

FONT_MONO = ("Consolas", 10)
FONT_BODY = ("Segoe UI", 12)
FONT_LABEL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 11, "bold")


def _card(root):
    """Outer page + centered card frame, mirrors the popup mockup."""
    root.configure(bg=BG_PAGE)
    card = tk.Frame(
        root,
        bg=BG_CARD,
        highlightbackground=BORDER_STRONG,
        highlightthickness=1,
        bd=0,
    )
    card.pack(expand=True, padx=24, pady=24, fill="both")
    return card


def _flat_button(parent, text, fg, command, width=14):
    return tk.Button(
        parent,
        text=text,
        font=FONT_BUTTON,
        width=width,
        bg=BG_CARD,
        fg=fg,
        activebackground=BORDER,
        activeforeground=fg,
        relief="flat",
        highlightbackground=fg,
        highlightthickness=1,
        bd=0,
        padx=6,
        pady=8,
        command=command,
    )


def show_manual_popup(test_case, step):
    result = {
        "status": None,
        "actual": "",
        "notes": "",
        "action": "continue",
        "screenshot": None,
    }
    attachment_path = {"path": None}

    root = tk.Tk()
    root.title(f"{test_case['id']} - {step['step_id']}")
    root.geometry("560x460")
    root.attributes("-topmost", True)
    root.configure(bg=BG_PAGE)

    card = _card(root)

    # test id, small mono label
    tk.Label(
        card,
        text=f"{test_case['id']} · {step['step_id']}",
        font=FONT_MONO,
        fg=TEXT_MUTED,
        bg=BG_CARD,
        anchor="w",
    ).pack(fill="x", padx=20, pady=(18, 4))

    # instruction, single paragraph, no sub-header treatment
    tk.Label(
        card,
        text=step["instruction"],
        wraplength=480,
        justify="left",
        font=FONT_BODY,
        fg=TEXT_PRIMARY,
        bg=BG_CARD,
        anchor="w",
    ).pack(fill="x", padx=20, pady=(0, 14))

    # divider
    tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=20)

    # expected result
    tk.Label(
        card,
        text="Expected result",
        font=FONT_LABEL,
        fg=TEXT_SECONDARY,
        bg=BG_CARD,
        anchor="w",
    ).pack(fill="x", padx=20, pady=(12, 2))

    tk.Label(
        card,
        text=step["expected"],
        wraplength=480,
        justify="left",
        font=FONT_LABEL,
        fg=TEXT_PRIMARY,
        bg=BG_CARD,
        anchor="w",
    ).pack(fill="x", padx=20, pady=(0, 14))

    # notes / comment box, used for both pass and fail
    tk.Label(
        card,
        text="Notes (optional)",
        font=FONT_LABEL,
        fg=TEXT_SECONDARY,
        bg=BG_CARD,
        anchor="w",
    ).pack(fill="x", padx=20, pady=(0, 4))

    notes = tk.Text(
        card,
        height=4,
        bg="#161616",
        fg=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        highlightbackground=BORDER,
        highlightcolor=BORDER_STRONG,
        highlightthickness=1,
        bd=0,
        font=FONT_LABEL,
        wrap="word",
    )
    notes.pack(fill="x", padx=20, pady=(0, 8))

    # attach file row
    attach_row = tk.Frame(card, bg=BG_CARD)
    attach_row.pack(fill="x", padx=20, pady=(0, 16))

    attach_label = tk.Label(
        attach_row, text="", font=FONT_LABEL, fg=TEXT_MUTED, bg=BG_CARD, anchor="w"
    )
    attach_label.pack(side="left")

    def attach_file():
        path = filedialog.askopenfilename(title="Attach file")
        if path:
            attachment_path["path"] = path
            attach_label.config(text=path.split("/")[-1])

    tk.Button(
        attach_row,
        text="📎 Attach file",
        font=FONT_LABEL,
        bg=BG_CARD,
        fg=TEXT_SECONDARY,
        activebackground=BORDER,
        activeforeground=TEXT_PRIMARY,
        relief="flat",
        highlightbackground=BORDER,
        highlightthickness=1,
        bd=0,
        padx=8,
        pady=4,
        command=attach_file,
    ).pack(side="right")

    # pass / fail actions
    def pass_step():
        comment = notes.get("1.0", "end").strip()
        result["status"] = "PASS"
        result["actual"] = "Operator marked step as passed"
        result["notes"] = comment
        result["action"] = "continue"
        result["screenshot"] = attachment_path["path"]
        root.destroy()

    def fail_step():
        comment = notes.get("1.0", "end").strip()
        if not comment:
            messagebox.showwarning(
                "Comment required", "Please enter a failure comment before continuing."
            )
            return
        _show_fail_action_popup(root, result, comment, attachment_path["path"])

    button_row = tk.Frame(card, bg=BG_CARD)
    button_row.pack(fill="x", padx=20, pady=(0, 20))
    button_row.columnconfigure(0, weight=1)
    button_row.columnconfigure(1, weight=1)

    _flat_button(button_row, "Pass", SUCCESS, pass_step).grid(
        row=0, column=0, sticky="ew", padx=(0, 6)
    )
    _flat_button(button_row, "Fail", DANGER, fail_step).grid(
        row=0, column=1, sticky="ew", padx=(6, 0)
    )

    root.mainloop()
    return result


def _show_fail_action_popup(parent_root, result, comment, attachment):
    """Ask whether to continue or abort after recording a failure."""

    fail_window = tk.Toplevel(parent_root)
    fail_window.title("Failure recorded")
    fail_window.geometry("420x200")
    fail_window.configure(bg=BG_PAGE)

    fail_window.transient(parent_root)
    fail_window.attributes("-topmost", True)
    fail_window.lift()
    fail_window.focus_force()
    fail_window.grab_set()

    card = _card(fail_window)

    tk.Label(
        card,
        text="Failure recorded. Continue testing or abort?",
        font=FONT_BODY,
        fg=TEXT_PRIMARY,
        bg=BG_CARD,
        wraplength=340,
        justify="left",
    ).pack(padx=20, pady=(20, 20))

    def continue_after_fail():
        result["status"] = "FAILED"
        result["actual"] = "Operator marked step as FAILED"
        result["notes"] = comment
        result["action"] = "continue"
        result["screenshot"] = attachment

        fail_window.grab_release()
        fail_window.destroy()
        parent_root.destroy()

    def abort_after_fail():
        result["status"] = "FAILED"
        result["actual"] = "Operator marked step as FAILED"
        result["notes"] = comment
        result["action"] = "abort"
        result["screenshot"] = attachment

        fail_window.grab_release()
        fail_window.destroy()
        parent_root.destroy()

    button_row = tk.Frame(
        card,
        bg=BG_CARD,
    )
    button_row.pack(
        fill="x",
        padx=20,
        pady=(0, 20),
    )

    button_row.columnconfigure(0, weight=1)
    button_row.columnconfigure(1, weight=1)

    _flat_button(
        button_row,
        "Continue",
        TEXT_PRIMARY,
        continue_after_fail,
        width=12,
    ).grid(
        row=0,
        column=0,
        sticky="ew",
        padx=(0, 6),
    )

    _flat_button(
        button_row,
        "Abort test",
        DANGER,
        abort_after_fail,
        width=12,
    ).grid(
        row=0,
        column=1,
        sticky="ew",
        padx=(6, 0),
    )

    def continue_after_fail():
        result["status"] = "FAILED"
        result["actual"] = comment
        result["action"] = "continue"
        result["screenshot"] = attachment

        fail_window.grab_release()
        fail_window.destroy()
        parent_root.destroy()

    def abort_after_fail():
        result["status"] = "FAILED"
        result["actual"] = comment
        result["action"] = "abort"
        result["screenshot"] = attachment

        fail_window.grab_release()
        fail_window.destroy()
        parent_root.destroy()


    button_row = tk.Frame(card, bg=BG_CARD)
    button_row.pack(fill="x", padx=20, pady=(0, 20))
    button_row.columnconfigure(0, weight=1)
    button_row.columnconfigure(1, weight=1)

    _flat_button(
        button_row, "Continue", TEXT_PRIMARY, continue_after_fail, width=12
    ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
    _flat_button(button_row, "Abort test", DANGER, abort_after_fail, width=12).grid(
        row=0, column=1, sticky="ew", padx=(6, 0)
    )