import cv2
import dlib
import numpy as np
from scipy.spatial import distance
from datetime import datetime
import csv
import os
import time
import subprocess
import shutil
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox

# ---------- FUNCTIONS ----------
def get_study_duration_seconds():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    while True:
        minutes = simpledialog.askfloat(
            title="Study Timer",
            prompt="Enter planned study duration (minutes):",
            minvalue=0.01,
            parent=root
        )

        if minutes is None:
            root.destroy()
            raise SystemExit("Study duration entry cancelled.")

        if minutes > 0:
            root.destroy()
            return minutes * 60.0

        messagebox.showerror("Invalid Input", "Please enter a value greater than 0.", parent=root)


def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

def get_eye_ratio(eye, gray):
    x_min = min([p[0] for p in eye])
    x_max = max([p[0] for p in eye])
    y_min = min([p[1] for p in eye])
    y_max = max([p[1] for p in eye])

    eye_img = gray[y_min:y_max, x_min:x_max]
    if eye_img.size == 0:
        return 0.5

    _, thresh = cv2.threshold(eye_img, 70, 255, cv2.THRESH_BINARY_INV)
    moments = cv2.moments(thresh)
    if moments['m00'] == 0:
        return 0.5

    cx = moments['m10'] / moments['m00']
    width = max((x_max - x_min), 1)
    ratio = cx / width
    return ratio

# ---------- INIT ----------
EAR_THRESHOLD = 0.21
GAZE_LEFT_THRESHOLD = 0.35
GAZE_RIGHT_THRESHOLD = 0.65

LOG_FILE = "screen_attention_log.csv"

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

cap = cv2.VideoCapture(0)

study_duration_sec = get_study_duration_seconds()
study_start_unix = time.time()
completion_flash_start = None
completion_flash_duration_sec = 3.0

# Running, time-weighted attention metrics for live overlay.
last_unix_time = None
prev_looking_at_screen = 0
total_monitored_time = 0.0
total_looking_time = 0.0
display_percent = 0.0
last_display_update = 0.0

# Start a fresh CSV each run so columns stay consistent per session.
with open(LOG_FILE, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp",
        "unix_time",
        "state",
        "gaze_label",
        "looking_at_screen"
    ])

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    state = "NOT_LOOKING_AT_SCREEN"
    looking_at_screen = 0
    gaze_label = "NO FACE DETECTED"

    faces = detector(gray)

    if len(faces) > 0:
        # Use the first detected face
        face = faces[0]
        shape = predictor(gray, face)
        shape = [(p.x, p.y) for p in shape.parts()]

        left_eye = [shape[i] for i in range(36, 42)]
        right_eye = [shape[i] for i in range(42, 48)]

        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0

        left_ratio = get_eye_ratio(left_eye, gray)
        right_ratio = get_eye_ratio(right_eye, gray)
        gaze = (left_ratio + right_ratio) / 2.0

        if ear < EAR_THRESHOLD:
            gaze_label = "EYES CLOSED"
            looking_at_screen = 0
            state = "NOT_LOOKING_AT_SCREEN"

        elif gaze < GAZE_LEFT_THRESHOLD:
            gaze_label = "LOOKING LEFT"
            looking_at_screen = 0
            state = "NOT_LOOKING_AT_SCREEN"

        elif gaze > GAZE_RIGHT_THRESHOLD:
            gaze_label = "LOOKING RIGHT"
            looking_at_screen = 0
            state = "NOT_LOOKING_AT_SCREEN"

        else:
            gaze_label = "LOOKING CENTER"
            looking_at_screen = 1
            state = "LOOKING_AT_SCREEN"

        color = (0, 255, 0) if looking_at_screen else (0, 0, 255)
        cv2.putText(frame, gaze_label, (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, state, (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        for eye in [left_eye, right_eye]:
            pts = np.array(eye, np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 1)

    else:
        cv2.putText(frame, gaze_label, (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        cv2.putText(frame, state, (30, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    # Update running time-weighted percentage before logging/display.
    now = datetime.now()
    unix_time = time.time()
    elapsed_study_sec = unix_time - study_start_unix
    study_complete = elapsed_study_sec >= study_duration_sec

    if last_unix_time is not None:
        dt = unix_time - last_unix_time
        if dt > 0:
            total_monitored_time += dt
            if prev_looking_at_screen:
                total_looking_time += dt

    if total_monitored_time > 0:
        live_percent = 100.0 * (total_looking_time / total_monitored_time)
    else:
        live_percent = 0.0

    # Refresh displayed percent once per second to keep overlay stable.
    if (unix_time - last_display_update) >= 1.0:
        display_percent = live_percent
        last_display_update = unix_time

    live_text = f"Focus so far: {display_percent:.1f}%"
    (text_w, text_h), baseline = cv2.getTextSize(
        live_text,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        2
    )
    text_x = max(10, frame.shape[1] - text_w - 20)
    text_y = 30
    cv2.rectangle(
        frame,
        (text_x - 8, text_y - text_h - 8),
        (text_x + text_w + 8, text_y + baseline + 8),
        (0, 0, 0),
        -1
    )
    cv2.putText(
        frame,
        live_text,
        (text_x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    # Small progress bar under the percentage text.
    bar_width = text_w
    bar_height = 10
    bar_x1 = text_x
    bar_y1 = text_y + baseline + 8
    bar_x2 = bar_x1 + bar_width
    bar_y2 = bar_y1 + bar_height

    cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (180, 180, 180), 1)
    fill_width = int(bar_width * max(0.0, min(display_percent, 100.0)) / 100.0)
    if fill_width > 0:
        cv2.rectangle(
            frame,
            (bar_x1 + 1, bar_y1 + 1),
            (bar_x1 + fill_width - 1, bar_y2 - 1),
            (0, 220, 0),
            -1
        )

    remaining_sec = max(0.0, study_duration_sec - elapsed_study_sec)
    remaining_min = int(remaining_sec // 60)
    remaining_rem_sec = int(remaining_sec % 60)
    timer_text = f"Study timer left: {remaining_min:02d}:{remaining_rem_sec:02d}"
    cv2.putText(
        frame,
        timer_text,
        (30, frame.shape[0] - 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    if study_complete and completion_flash_start is None:
        completion_flash_start = unix_time

    if completion_flash_start is not None and int(unix_time * 2) % 2 == 0:
        red_overlay = np.zeros_like(frame)
        red_overlay[:, :] = (0, 0, 255)
        frame = cv2.addWeighted(red_overlay, 0.35, frame, 0.65, 0)
        cv2.putText(
            frame,
            "STUDY SESSION COMPLETE",
            (30, frame.shape[0] - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2
        )

    prev_looking_at_screen = looking_at_screen
    last_unix_time = unix_time

    # Log one row per frame

    with open(LOG_FILE, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            now.strftime("%Y-%m-%d %H:%M:%S.%f"),
            unix_time,
            state,
            gaze_label,
            looking_at_screen
        ])

    cv2.imshow("Eye Monitor", frame)

    if completion_flash_start is not None and (unix_time - completion_flash_start) >= completion_flash_duration_sec:
        break

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()

# Launch MATLAB analysis automatically after logging ends.
project_dir = os.path.dirname(os.path.abspath(__file__))
analysis_script = "screen_attention_analysis"
matlab_exe = shutil.which("matlab")

if matlab_exe:
    try:
        subprocess.Popen(
            [matlab_exe, "-batch", analysis_script],
            cwd=project_dir
        )
        print("MATLAB launched to run screen_attention_analysis.m")
    except Exception as e:
        print(f"Could not launch MATLAB automatically: {e}")
else:
    print(
        "MATLAB executable not found in PATH. "
        "Add MATLAB to PATH or run screen_attention_analysis.m manually."
    )