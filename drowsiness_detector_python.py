import time
import cv2
import dlib
import numpy as np
import serial
from serial.tools import list_ports
from imutils import face_utils

# ---------------- USER SETTINGS ----------------
CAMERA_INDEX = 0
BAUD_RATE = 9600

# Set this to your Mac's actual Arduino port, for example:
# SERIAL_PORT = "/dev/tty.usbmodem14101"
# On Windows, use a port such as "COM4".
# Leave as None to try automatic port detection.
SERIAL_PORT = None

LANDMARK_FILE = "shape_predictor_68_face_landmarks.dat"


# ---------------- ARDUINO CONNECTION ----------------
def connect_arduino():
    port = SERIAL_PORT

    if port is None:
        available_ports = list(list_ports.comports())
        if not available_ports:
            print("No serial port found. Camera detection will run without Arduino alerts.")
            return None

        print("Available serial ports:")
        for item in available_ports:
            print(f"  {item.device}: {item.description}")

        # Select the first available port. If this is not the Arduino,
        # set SERIAL_PORT manually near the top of this file.
        port = available_ports[0].device

    try:
        board = serial.Serial(port, BAUD_RATE, timeout=1)
        time.sleep(2)  # Allow the Arduino Uno to reset after serial connection.
        print(f"Connected to Arduino on {port}")
        return board
    except serial.SerialException as error:
        print(f"Could not connect to Arduino on {port}: {error}")
        print("Camera detection will continue without Arduino alerts.")
        return None


# ---------------- EYE MEASUREMENT ----------------
def distance(point_a, point_b):
    return np.linalg.norm(point_a - point_b)


def eye_state(a, b, c, d, e, f):
    """Return 2=open, 1=partly closed, 0=closed (original threshold approach)."""
    vertical = distance(b, d) + distance(c, e)
    horizontal = distance(a, f)

    if horizontal == 0:
        return 2

    ratio = vertical / (2.0 * horizontal)

    if ratio > 0.25:
        return 2
    elif ratio > 0.21:
        return 1
    return 0


# ---------------- INITIALIZATION ----------------
arduino = connect_arduino()

try:
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(LANDMARK_FILE)
except Exception as error:
    print(f"Could not load the facial landmark model: {error}")
    print(f"Make sure '{LANDMARK_FILE}' is in the same folder as this Python file.")
    if arduino:
        arduino.close()
    raise SystemExit(1)

camera = cv2.VideoCapture(CAMERA_INDEX)
if not camera.isOpened():
    print("Camera not detected. Check CAMERA_INDEX and camera connection.")
    if arduino:
        arduino.close()
    raise SystemExit(1)

sleep_count = 0
partial_count = 0
active_count = 0
current_status = "WAITING"
last_command = None

print("Drowsiness detection started. Press 'q' in the camera window to quit.")

try:
    while True:
        success, frame = camera.read()
        if not success:
            print("Could not read a frame from the camera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector(gray, 0)

        if len(faces) == 0:
            cv2.putText(frame, "Face not detected", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        for face in faces:
            shape = predictor(gray, face)
            landmarks = face_utils.shape_to_np(shape)

            left_eye = eye_state(
                landmarks[36], landmarks[37], landmarks[38],
                landmarks[41], landmarks[40], landmarks[39]
            )
            right_eye = eye_state(
                landmarks[42], landmarks[43], landmarks[44],
                landmarks[47], landmarks[46], landmarks[45]
            )

            # Both eyes closed/partly closed are treated as a warning.
            # The counters reduce reactions to a single camera frame.
            if left_eye == 0 and right_eye == 0:
                sleep_count += 1
                partial_count = 0
                active_count = 0
                if sleep_count > 6:
                    current_status = "SLEEPING"
                    command = b'a'

            elif left_eye == 1 or right_eye == 1 or left_eye == 0 or right_eye == 0:
                sleep_count = 0
                partial_count += 1
                active_count = 0
                if partial_count > 6:
                    current_status = "DROWSY"
                    command = b'a'

            else:
                sleep_count = 0
                partial_count = 0
                active_count += 1
                if active_count > 6:
                    current_status = "ACTIVE"
                    command = b'b'

            # Send only when the detected state changes.
            if current_status in ("SLEEPING", "DROWSY"):
                command = b'a'
            elif current_status == "ACTIVE":
                command = b'b'
            else:
                command = None

            if command is not None and command != last_command:
                if arduino is not None:
                    try:
                        arduino.write(command)
                    except serial.SerialException as error:
                        print(f"Serial communication error: {error}")
                last_command = command

            color = (0, 0, 255) if current_status in ("SLEEPING", "DROWSY") else (0, 255, 0)
            cv2.rectangle(frame, (face.left(), face.top()),
                          (face.right(), face.bottom()), color, 2)
            cv2.putText(frame, current_status, (face.left(), max(25, face.top() - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Driver Drowsiness Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    camera.release()
    cv2.destroyAllWindows()
    if arduino is not None and arduino.is_open:
        arduino.close()
    print("Program stopped.")
