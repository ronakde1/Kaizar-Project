import cv2
import dlib
import numpy as np
from scipy.spatial import distance
from datetime import datetime

# ---------- FUNCTIONS ----------
def eye_aspect_ratio(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

def get_eye_ratio(eye, gray):
    # Extract eye region
    x_min = min([p[0] for p in eye])
    x_max = max([p[0] for p in eye])
    y_min = min([p[1] for p in eye])
    y_max = max([p[1] for p in eye])

    eye_img = gray[y_min:y_max, x_min:x_max]
    _, thresh = cv2.threshold(eye_img, 70, 255, cv2.THRESH_BINARY_INV)
    moments = cv2.moments(thresh)
    if moments['m00'] == 0:
        return 0.5  # Default to center
    cx = moments['m10'] / moments['m00']
    ratio = cx / (x_max - x_min)
    return ratio  # 0: looking left, 1: looking right, 0.5: center

# ---------- INIT ----------
EAR_THRESHOLD = 0.21
GAZE_LEFT_THRESHOLD = 0.35
GAZE_RIGHT_THRESHOLD = 0.65

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    faces = detector(gray)
    for face in faces:
        shape = predictor(gray, face)
        shape = [(p.x, p.y) for p in shape.parts()]

        # Eyes
        left_eye = [shape[i] for i in range(36, 42)]
        right_eye = [shape[i] for i in range(42, 48)]

        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        ear = (left_ear + right_ear) / 2.0

        left_ratio = get_eye_ratio(left_eye, gray)
        right_ratio = get_eye_ratio(right_eye, gray)
        gaze = (left_ratio + right_ratio) / 2.0

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check eyes closed
        if ear < EAR_THRESHOLD:
            print(f"{now} - EYES CLOSED")
            cv2.putText(frame, "EYES CLOSED", (30,50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        # Check eyes looking away
        elif gaze < GAZE_LEFT_THRESHOLD:
            print(f"{now} - LOOKING LEFT")
            cv2.putText(frame, "LOOKING LEFT", (30,50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        elif gaze > GAZE_RIGHT_THRESHOLD:
            print(f"{now} - LOOKING RIGHT")
            cv2.putText(frame, "LOOKING RIGHT", (30,50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        else:
            cv2.putText(frame, "LOOKING CENTER", (30,50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

        # Draw eyes
        for eye in [left_eye, right_eye]:
            pts = np.array(eye, np.int32)
            cv2.polylines(frame, [pts], True, (0,255,0), 1)

    cv2.imshow("Eye Monitor", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to exit
        break

cap.release()
cv2.destroyAllWindows()