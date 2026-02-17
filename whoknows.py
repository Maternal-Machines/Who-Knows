#!/usr/bin/env python3

import os
import tkinter as tk
from PIL import Image, ImageTk
import RPi.GPIO as GPIO
import fnmatch

# === CONFIGURATION ===
IMAGE_FOLDER = "/home/mm/whoknows/facts" # images change depending on device (rectangular / circular / losange)
DISPLAY_WIDTH = 1024 # change depending on display used
DISPLAY_HEIGHT = 600 # change depending on display used
POLL_INTERVAL = 200  # milliseconds
RANDOM_CHANGE_INTERVAL = 10 * 1000  # 10 seconds

SWITCH_PIN = 17        # image mode button
SHUTDOWN_PIN = 27      # shutdown button

FIXED_IMAGE_BASENAME = "who knows_1"

# === GPIO SETUP ===
GPIO.setmode(GPIO.BCM)
GPIO.setup(SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(SHUTDOWN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# === IMAGE LIST ===
image_files = sorted([
    os.path.join(IMAGE_FOLDER, f)
    for f in os.listdir(IMAGE_FOLDER)
    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
])

if not image_files:
    raise RuntimeError("No images found in the directory.")

# === FIND FIXED IMAGE ===
fixed_image_path = None
for f in image_files:
    if fnmatch.fnmatch(
        os.path.basename(f).lower(),
        f"{FIXED_IMAGE_BASENAME.lower()}.*"
    ):
        fixed_image_path = f
        break

if not fixed_image_path:
    raise RuntimeError(
        f"No image matching '{FIXED_IMAGE_BASENAME}.*' found in folder."
    )

# Remove fixed image from slideshow
image_files = [f for f in image_files if f != fixed_image_path]

# === TKINTER SETUP ===
root = tk.Tk()
root.attributes('-fullscreen', True)
root.overrideredirect(True)
root.configure(background='black')

# Hide mouse cursor
root.config(cursor="none")

label = tk.Label(root, bg='black')
label.pack(expand=True)

# === CLEAN EXIT ===
def quit_app(event=None):
    GPIO.cleanup()
    root.destroy()

root.bind('<Escape>', quit_app)

# === STATE ===
current_mode = None   # "fixed" or "sequence"
sequence_index = 0
scheduled_job = None
shutdown_started = False

# === IMAGE DISPLAY ===
def show_image(image_path):
    try:
        img = Image.open(image_path)
        img.thumbnail((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.ANTIALIAS)

        background = Image.new(
            'RGB',
            (DISPLAY_WIDTH, DISPLAY_HEIGHT),
            (0, 0, 0)
        )

        offset_x = (DISPLAY_WIDTH - img.width) // 2
        offset_y = (DISPLAY_HEIGHT - img.height) // 2
        background.paste(img, (offset_x, offset_y))

        tk_img = ImageTk.PhotoImage(background)
        label.config(image=tk_img)
        label.image = tk_img

    except Exception as e:
        print(f"Error displaying image {image_path}: {e}")

# === IMAGE TIMING ===
def schedule_next_image():
    global scheduled_job
    scheduled_job = root.after(
        RANDOM_CHANGE_INTERVAL,
        show_next_image
    )

def cancel_scheduled_image():
    global scheduled_job
    if scheduled_job:
        root.after_cancel(scheduled_job)
        scheduled_job = None

def show_next_image():
    global sequence_index

    if current_mode == "sequence":
        show_image(image_files[sequence_index])
        sequence_index = (sequence_index + 1) % len(image_files)
        schedule_next_image()

# === MAIN POLLING LOOP ===
def poll_switch():
    global current_mode, shutdown_started

    # --- Shutdown button ---
    if GPIO.input(SHUTDOWN_PIN) == GPIO.LOW and not shutdown_started:
        shutdown_started = True
        print("Shutdown button pressed")
        GPIO.cleanup()
        os.system("sudo shutdown -h now")
        return

    # --- Image mode switch ---
    if GPIO.input(SWITCH_PIN) == GPIO.LOW:
        if current_mode != "fixed":
            cancel_scheduled_image()
            show_image(fixed_image_path)
            current_mode = "fixed"
    else:
        if current_mode != "sequence":
            current_mode = "sequence"
            show_next_image()

    root.after(POLL_INTERVAL, poll_switch)

# === INITIAL STATE ===
if GPIO.input(SWITCH_PIN) == GPIO.LOW:
    show_image(fixed_image_path)
    current_mode = "fixed"
else:
    current_mode = "sequence"
    show_next_image()

root.after(POLL_INTERVAL, poll_switch)

root.mainloop()
