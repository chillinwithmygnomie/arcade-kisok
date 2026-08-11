#!/usr/bin/env python3
# Simple fullscreen launcher using Tkinter. Click a tile to run the helper scripts.
import tkinter as tk
from tkinter import messagebox
import subprocess
import os
HOME = os.path.expanduser("~")

LAUNCHER_BUTTONS = [
    ("Clone Hero", "/home/kiosk/launcher/start_clonehero.sh"),
    ("YARG (Rock Band)", "/home/kiosk/launcher/start_yarg.sh"),
    ("Retro (EmulationStation)", "/home/kiosk/launcher/start_emulationstation.sh"),
    ("Settings", "/home/kiosk/launcher/open_settings.sh"),
    ("Shutdown", "/home/kiosk/launcher/shutdown.sh"),
]


def run_cmd(path):
    # Launch each helper in detached Xterm-less background
    try:
        subprocess.Popen(["/bin/bash", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        messagebox.showerror("Launch error", str(e))

root = tk.Tk()
root.title("Appliance Launcher")
root.attributes("-fullscreen", True)
root.configure(bg="black")

# Simple grid layout
rows = 1
cols = len(LAUNCHER_BUTTONS)
for i, (label, cmd) in enumerate(LAUNCHER_BUTTONS):
    btn = tk.Button(root, text=label, font=("Helvetica", 30), fg="white", bg="#222",
                    activebackground="#444", width=25, height=6,
                    command=lambda c=cmd: run_cmd(c))
    btn.grid(row=0, column=i, padx=20, pady=60)

# Quit keybinding for maintenance: Ctrl+Alt+Q to exit launcher to shell (for debugging)
def debug_exit(event=None):
    root.destroy()
root.bind_all("<Control-Alt-q>", debug_exit)

root.mainloop()
