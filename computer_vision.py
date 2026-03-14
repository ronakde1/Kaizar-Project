import cv2
import dlib
import numpy as np
from scipy.spatial import distance
from datetime import datetime
import csv
import os
import time
import subprocess
import serial
import shutil

# ---------- FUNCTIONS ----------
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

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
    return cx / width

# ---------- CONFIG ----------
EAR_THRESHOLD = 0.21
GAZE_LEFT_THRESHOLD = 0.35
GAZE_RIGHT_THRESHOLD = 0.65


LOG_FILE = "screen_attention_log.csv"

# ---------- ADDITIONAL VARIABLES ----------
not_focusing_start = None  # time when user stopped focusing
signal_sent = False        # whether Arduino signal has been sent for current unfocused period


# --- Arduino serial setup ---
arduino_port = "/dev/tty.usbserial-210"  # Mac/Linux
baud_rate = 9600
timeout = 0.01  # non-blocking read
ser = serial.Serial(arduino_port, baud_rate, timeout=timeout)
time.sleep(2)  # allow Arduino to initialize
arduino_data = []

# ---------- INIT ----------
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
cap = cv2.VideoCapture(0)

last_unix_time = None
prev_looking_at_screen = 0
total_monitored_time = 0.0
total_looking_time = 0.0
display_percent = 0.0
last_display_update = 0.0

# Start fresh CSV with headers
with open(LOG_FILE, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp", "unix_time", "state", "gaze_label", "looking_at_screen",
        "temperature", "distance", "loud"
    ])

# ---------- MAIN LOOP ----------
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

        # --- Arduino non-blocking read ---
        temperature = distance_val = loud = None
        while ser.in_waiting:
            line = ser.readline().decode('utf-8').strip()
            if line:
                try:
                    dist_str, temp_str, loud_str = line.split(',')
                    temperature = float(temp_str)
                    distance_val = float(dist_str)
                    loud = int(loud_str)
                    arduino_data.append((temperature, distance_val, loud))
                except ValueError:
                    pass  # skip malformed lines

        # --- Update running attention metrics ---
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

        # --- Overlay progress bar ---
        live_text = f"Focus so far: {display_percent:.1f}%"
        (text_w, text_h), baseline = cv2.getTextSize(live_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        text_x = max(10, frame.shape[1] - text_w - 20)
        text_y = 30
        cv2.rectangle(frame, (text_x-8, text_y-text_h-8), (text_x+text_w+8, text_y+baseline+8), (0,0,0), -1)
        cv2.putText(frame, live_text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        bar_width = text_w
        bar_height = 10
        bar_x1, bar_y1 = text_x, text_y + baseline + 8
        bar_x2, bar_y2 = bar_x1 + bar_width, bar_y1 + bar_height
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (180,180,180), 1)
        fill_width = int(bar_width * max(0.0, min(display_percent, 100.0)) / 100.0)
        if fill_width > 0:
            cv2.rectangle(frame, (bar_x1+1, bar_y1+1), (bar_x1+fill_width-1, bar_y2-1), (0,220,0), -1)

        prev_looking_at_screen = looking_at_screen
        last_unix_time = unix_time

        # --- Focus signal logic ---
        current_time = time.time()

        if looking_at_screen:
            not_focusing_start = None
            if signal_sent:
                try:
                    ser.write(b'0\n')  # send 0 if user refocused
                except Exception as e:
                    print(f"Serial write failed: {e}")
                signal_sent = False
        else:
            if not_focusing_start is None:
                not_focusing_start = current_time
            elif current_time - not_focusing_start >= 5.0 and not signal_sent:
                try:
                    ser.write(b'1\n')  # send 1 after 5 seconds of not focusing
                except Exception as e:
                    print(f"Serial write failed: {e}")
                signal_sent = True

        # --- Log everything ---
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

# --- MATLAB POST-PROCESSING ---
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
    print(f"MATLAB executable not found at {matlab_exe}. Check the path or install MATLAB.")