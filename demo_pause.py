import tkinter as tk
from tkinter import ttk


def pause_for_demo(
    test_case_name,
    step_id,
    step_name,
    status,
):
    root = tk.Tk()
    root.title("Demo Paused")
    root.geometry("500x280")
    root.resizable(False, False)

    action = {"value": "CONTINUE"}

    ttk.Label(
        root,
        text="Demo Paused",
        font=("Arial", 18, "bold"),
    ).pack(pady=(20, 10))

    ttk.Label(
        root,
        text=f"Test Case: {test_case_name}",
        wraplength=450,
    ).pack(pady=4)

    ttk.Label(
        root,
        text=f"Step: {step_id}",
    ).pack(pady=4)

    ttk.Label(
        root,
        text=step_name,
        wraplength=450,
    ).pack(pady=4)

    ttk.Label(
        root,
        text=f"Result: {status}",
        font=("Arial", 11, "bold"),
    ).pack(pady=4)

    ttk.Label(
        root,
        text="Review the displays through VNC, then continue.",
        wraplength=450,
    ).pack(pady=(12, 16))

    def continue_demo():
        action["value"] = "CONTINUE"
        root.destroy()

    def abort_demo():
        action["value"] = "ABORT"
        root.destroy()

    button_frame = ttk.Frame(root)
    button_frame.pack()

    ttk.Button(
        button_frame,
        text="Continue",
        command=continue_demo,
    ).pack(side="left", padx=8)

    ttk.Button(
        button_frame,
        text="Abort Demo",
        command=abort_demo,
    ).pack(side="left", padx=8)

    root.protocol("WM_DELETE_WINDOW", abort_demo)

    # Python pauses here until the popup is closed.
    root.mainloop()

    return action["value"]