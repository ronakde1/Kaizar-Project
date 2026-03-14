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
<<<<<<< HEAD
=======
import tkinter as tk
from tkinter import simpledialog, messagebox
>>>>>>> e8009f51eba019c6fab7a8615ff5dfbdf6a73fc3

try:
    import serial
except Exception:
    serial = None


def get_study_duration_seconds():
    while True:
        raw = input("Enter planned study duration in minutes: ").strip()
        try:
            minutes = float(raw)
            if minutes > 0:
                return minutes * 60.0
            print("Please enter a value greater than 0.")
        except ValueError:
            print("Please enter a valid number (example: 25 or 45.5).")

def eye_aspect_ratio(eye):
    a = distance.euclidean(eye[1], eye[5])
    b = distance.euclidean(eye[2], eye[4])
    c = distance.euclidean(eye[0], eye[3])
    return (a + b) / (2.0 * c)


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
    if moments["m00"] == 0:
        return 0.5

    cx = moments["m10"] / moments["m00"]
    width = max((x_max - x_min), 1)
    return cx / width


EAR_THRESHOLD = 0.21
GAZE_LEFT_THRESHOLD = 0.35
GAZE_RIGHT_THRESHOLD = 0.65
LOG_FILE = "screen_attention_log.csv"

<<<<<<< HEAD
# Optional Arduino setup. Leave ARDUINO_PORT empty to disable.
ARDUINO_PORT = ""
ARDUINO_BAUD = 9600
ARDUINO_TIMEOUT = 0.01
=======
# --- Arduino serial setup ---
arduino_port = "/dev/tty.usbserial-210"  # Mac/Linux
baud_rate = 9600
timeout = 0.01  # non-blocking read
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)
time.sleep(2)
arduino_data = []
>>>>>>> e8009f51eba019c6fab7a8615ff5dfbdf6a73fc3


<<<<<<< HEAD
def open_arduino_serial(port):
    if not port or serial is None:
        return None
    try:
        ser_obj = serial.Serial(port, ARDUINO_BAUD, timeout=ARDUINO_TIMEOUT)
        time.sleep(2)
        print(f"Arduino connected on {port}")
        return ser_obj
    except Exception as exc:
        print(f"Arduino not connected ({exc}). Continuing without Arduino data.")
        return None


def main():
    study_duration_sec = get_study_duration_seconds()
    study_start_unix = time.time()
    completion_flash_start = None
    completion_flash_duration_sec = 3.0
=======
study_duration_sec = get_study_duration_seconds()
study_start_unix = time.time()
completion_flash_start = None

# Running metrics
last_unix_time = None
prev_looking_at_screen = 0
total_monitored_time = 0.0
total_looking_time = 0.0
display_percent = 0.0
last_display_update = 0.0

# CSV header
with open(LOG_FILE, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp", "unix_time", "state", "gaze_label", "looking_at_screen",
        "temperature", "distance", "loud"
    ])
>>>>>>> e8009f51eba019c6fab7a8615ff5dfbdf6a73fc3

    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
    cap = cv2.VideoCapture(0)
    ser_obj = open_arduino_serial(ARDUINO_PORT)

    last_unix_time = None
    prev_looking_at_screen = 0
    total_monitored_time = 0.0
    total_looking_time = 0.0
    display_percent = 0.0
    last_display_update = 0.0

<<<<<<< HEAD
    with open(LOG_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "unix_time",
            "state",
            "gaze_label",
            "looking_at_screen",
            "temperature",
            "distance",
            "loud",
        ])

    try:
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
                face = faces[0]
                shape = predictor(gray, face)
                shape = [(p.x, p.y) for p in shape.parts()]

                left_eye = [shape[i] for i in range(36, 42)]
                right_eye = [shape[i] for i in range(42, 48)]

                ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2.0
                gaze = (get_eye_ratio(left_eye, gray) + get_eye_ratio(right_eye, gray)) / 2.0

                if ear < EAR_THRESHOLD:
                    gaze_label = "EYES CLOSED"
                elif gaze < GAZE_LEFT_THRESHOLD:
                    gaze_label = "LOOKING LEFT"
                elif gaze > GAZE_RIGHT_THRESHOLD:
                    gaze_label = "LOOKING RIGHT"
                else:
                    gaze_label = "LOOKING CENTER"
                    looking_at_screen = 1
                    state = "LOOKING_AT_SCREEN"

                color = (0, 255, 0) if looking_at_screen else (0, 0, 255)
                cv2.putText(frame, gaze_label, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(frame, state, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

                for eye in [left_eye, right_eye]:
                    pts = np.array(eye, np.int32)
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 1)
            else:
                cv2.putText(frame, gaze_label, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                cv2.putText(frame, state, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

            temperature = None
            distance_val = None
            loud = None
            if ser_obj is not None:
                while ser_obj.in_waiting:
                    line = ser_obj.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        dist_str, temp_str, loud_str = line.split(",")
                        distance_val = float(dist_str)
                        temperature = float(temp_str)
                        loud = int(loud_str)
                    except ValueError:
                        pass

            now = datetime.now()
            unix_time = time.time()

            if last_unix_time is not None:
                dt = unix_time - last_unix_time
                if dt > 0:
                    total_monitored_time += dt
                    if prev_looking_at_screen:
                        total_looking_time += dt

            live_percent = 100.0 * total_looking_time / total_monitored_time if total_monitored_time > 0 else 0.0
            if (unix_time - last_display_update) >= 1.0:
                display_percent = live_percent
                last_display_update = unix_time

            live_text = f"Focus so far: {display_percent:.1f}%"
            (text_w, text_h), baseline = cv2.getTextSize(live_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            text_x = max(10, frame.shape[1] - text_w - 20)
            text_y = 30
            cv2.rectangle(frame, (text_x - 8, text_y - text_h - 8), (text_x + text_w + 8, text_y + baseline + 8), (0, 0, 0), -1)
            cv2.putText(frame, live_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            bar_width = text_w
            bar_height = 10
            bar_x1 = text_x
            bar_y1 = text_y + baseline + 8
            bar_x2 = bar_x1 + bar_width
            bar_y2 = bar_y1 + bar_height
            cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (180, 180, 180), 1)
            fill_width = int(bar_width * max(0.0, min(display_percent, 100.0)) / 100.0)
            if fill_width > 0:
                cv2.rectangle(frame, (bar_x1 + 1, bar_y1 + 1), (bar_x1 + fill_width - 1, bar_y2 - 1), (0, 220, 0), -1)

            elapsed_study_sec = unix_time - study_start_unix
            study_complete = elapsed_study_sec >= study_duration_sec
            remaining_sec = max(0.0, study_duration_sec - elapsed_study_sec)
            remaining_min = int(remaining_sec // 60)
            remaining_rem_sec = int(remaining_sec % 60)
            timer_text = f"Study timer left: {remaining_min:02d}:{remaining_rem_sec:02d}"
            cv2.putText(frame, timer_text, (30, frame.shape[0] - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

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
                    2,
                )

            prev_looking_at_screen = looking_at_screen
            last_unix_time = unix_time

            with open(LOG_FILE, mode="a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                    unix_time,
                    state,
                    gaze_label,
                    looking_at_screen,
                    temperature,
                    distance_val,
                    loud,
                ])

            cv2.imshow("Eye Monitor", frame)

            if completion_flash_start is not None and (unix_time - completion_flash_start) >= completion_flash_duration_sec:
                break

            if cv2.waitKey(1) & 0xFF == 27:
                break
    finally:
        cap.release()
        if ser_obj is not None:
            ser_obj.close()
        cv2.destroyAllWindows()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    analysis_script = "screen_attention_analysis"
    matlab_exe = shutil.which("matlab")

    if matlab_exe:
        try:
            subprocess.Popen([matlab_exe, "-batch", analysis_script], cwd=project_dir)
            print("MATLAB launched to run screen_attention_analysis.m")
        except Exception as exc:
            print(f"Could not launch MATLAB automatically: {exc}")
    else:
        print("MATLAB executable not found in PATH. Add MATLAB to PATH or run screen_attention_analysis.m manually.")


if __name__ == "__main__":
    main()
=======
        state = "NOT_LOOKING_AT_SCREEN"
        looking_at_screen = 0
        gaze_label = "NO FACE DETECTED"

        faces = detector(gray)
        if faces:
            face = faces[0]
            shape = predictor(gray, face)
            shape = [(p.x, p.y) for p in shape.parts()]

            left_eye = [shape[i] for i in range(36, 42)]
            right_eye = [shape[i] for i in range(42, 48)]

            ear = (eye_aspect_ratio(left_eye) + eye_aspect_ratio(right_eye)) / 2
            gaze = (get_eye_ratio(left_eye, gray) + get_eye_ratio(right_eye, gray)) / 2

            if ear < EAR_THRESHOLD:
                gaze_label = "EYES CLOSED"
            elif gaze < GAZE_LEFT_THRESHOLD:
                gaze_label = "LOOKING LEFT"
            elif gaze > GAZE_RIGHT_THRESHOLD:
                gaze_label = "LOOKING RIGHT"
            else:
                gaze_label = "LOOKING CENTER"
                looking_at_screen = 1
                state = "LOOKING_AT_SCREEN"

            color = (0, 255, 0) if looking_at_screen else (0, 0, 255)
            cv2.putText(frame, gaze_label, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            cv2.putText(frame, state, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            for eye in [left_eye, right_eye]:
                pts = np.array(eye, np.int32)
                cv2.polylines(frame, [pts], True, (0, 255, 0), 1)
        else:
            cv2.putText(frame, gaze_label, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            cv2.putText(frame, state, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        # --- Arduino non-blocking read ---
        temperature = distance_val = loud = None
        while ser.in_waiting:
            line = ser.readline().decode('utf-8').strip()
            if line:
                try:
                    dist_str, temp_str, loud_str = line.split(',')
                    distance_val = float(dist_str)
                    temperature = float(temp_str)
                    loud = int(loud_str)
                    arduino_data.append((temperature, distance_val, loud))
                except ValueError:
                    continue

        # --- Metrics update ---
        now = datetime.now()
        unix_time = time.time()
        if last_unix_time is not None:
            dt = unix_time - last_unix_time
            if dt > 0:
                total_monitored_time += dt
                if prev_looking_at_screen:
                    total_looking_time += dt

        live_percent = 100.0 * total_looking_time / total_monitored_time if total_monitored_time > 0 else 0.0
        if unix_time - last_display_update >= 1.0:
            display_percent = live_percent
            last_display_update = unix_time

        elapsed_study_sec = unix_time - study_start_unix
        study_complete = elapsed_study_sec >= study_duration_sec

        # --- Overlay ---
        live_text = f"Focus so far: {display_percent:.1f}%"
        (text_w, text_h), baseline = cv2.getTextSize(live_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        text_x = max(10, frame.shape[1] - text_w - 20)
        text_y = 30
        cv2.rectangle(frame, (text_x-8, text_y-text_h-8), (text_x+text_w+8, text_y+baseline+8), (0,0,0), -1)
        cv2.putText(frame, live_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        # Progress bar
        bar_width = text_w
        bar_height = 10
        bar_x1, bar_y1 = text_x, text_y + baseline + 8
        bar_x2, bar_y2 = bar_x1 + bar_width, bar_y1 + bar_height
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (180,180,180), 1)
        fill_width = int(bar_width * max(0.0, min(display_percent, 100.0)) / 100.0)
        if fill_width > 0:
            cv2.rectangle(frame, (bar_x1+1, bar_y1+1), (bar_x1+fill_width-1, bar_y2-1), (0,220,0), -1)

        # Completion flash
        if study_complete:
            if completion_flash_start is None:
                completion_flash_start = unix_time
            if int(unix_time * 2) % 2 == 0:
                red_overlay = np.zeros_like(frame)
                red_overlay[:, :] = (0, 0, 255)
                frame = cv2.addWeighted(red_overlay, 0.35, frame, 0.65, 0)
                cv2.putText(frame, "STUDY SESSION COMPLETE", (30, frame.shape[0]-60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,255,255), 2)

        prev_looking_at_screen = looking_at_screen
        last_unix_time = unix_time

        # --- Log ---
        with open(LOG_FILE, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                unix_time,
                state,
                gaze_label,
                looking_at_screen,
                temperature,
                distance_val,
                loud
            ])

        cv2.imshow("Eye Monitor", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

finally:
    cap.release()
    ser.close()
    cv2.destroyAllWindows()

    # --- MATLAB post-processing ---
    project_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(project_dir, LOG_FILE)
    analysis_script = "screen_attention_analysis"
    matlab_exe = "/Applications/MATLAB_R2025b.app/bin/matlab"

    if os.path.exists(matlab_exe):
        try:
            matlab_command = f"try, {analysis_script}('{csv_path}'); catch e, disp(e.message); end;"
            subprocess.Popen([matlab_exe, "-desktop", "-r", matlab_command], cwd=project_dir)
            print(f"MATLAB launched to run {analysis_script}.m with CSV: {csv_path}")
        except Exception as e:
            print(f"Could not launch MATLAB automatically: {e}")
    else:
        print("MATLAB executable not found. Add MATLAB to PATH or run screen_attention_analysis.m manually.")
>>>>>>> e8009f51eba019c6fab7a8615ff5dfbdf6a73fc3
