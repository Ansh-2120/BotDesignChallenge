# -*- coding: utf-8 -*-
import cv2
import csv
import os
import time
import threading
import queue
import numpy as np
from datetime import datetime
from flask import Flask, Response, render_template, jsonify, send_file, request
from ultralytics import YOLO
from picamera2 import Picamera2

app = Flask(__name__, template_folder="templates", static_folder="static")

# Run time string synced from dashboard stopwatch
current_run_time = "00:00"

# --- Paths -------------------------------------------------------------------
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "..", "model")
CSV_PATH  = os.path.join(BASE_DIR, "..", "data", "detections.csv")

# --- Model loading -----------------------------------------------------------
PT_MODEL   = os.path.join(MODEL_DIR, "best.pt")
NCNN_PARAM = os.path.join(MODEL_DIR, "best_ncnn_model.param")
NCNN_BIN   = os.path.join(MODEL_DIR, "best_ncnn_model.bin")

if os.path.exists(NCNN_PARAM) and os.path.exists(NCNN_BIN):
    MODEL_PATH   = NCNN_PARAM
    MODEL_FORMAT = "ncnn"
    print("[OK] Loading NCNN model")
elif os.path.exists(PT_MODEL):
    MODEL_PATH   = PT_MODEL
    MODEL_FORMAT = "pt"
    print("[OK] Loading best.pt model")
else:
    raise FileNotFoundError(f"No model found in {MODEL_DIR}")

# --- Class map (category, content) -------------------------------------------
CLASS_MAP = {
    0:  ("Face recognition",     "Roger Federer"),
    1:  ("Face recognition",     "Keanu Reeves"),
    2:  ("Face recognition",     "Henry Cavill"),
    3:  ("Parcel",               "Parcel"),
    4:  ("QR code",              None),           # decoded live
    5:  ("Smart switch",         "Smart Console"),
    6:  ("Furniture",            "Chair"),
    7:  ("Furniture",            "Dining Table"),
    8:  ("Pets",                 "Cat"),
    9:  ("Pets",                 "Dog"),
    10: ("Vehicle",              "Bicycle"),
    11: ("Vehicle",              "Car"),
    12: ("Vehicle",              "Motorbike"),
    13: ("Brand logo",           "Apple"),
    14: ("Brand logo",           "Tesla"),
    15: ("Brand logo",           "Maybach"),
    16: ("Brand logo",           "Keus"),
    17: ("Vehicle number plate", None),           # OCR decoded live
}

QR_CLASS_ID    = 4
PLATE_CLASS_ID = 17

def get_class_name(cls_id):
    entry = CLASS_MAP.get(int(cls_id))
    if entry:
        return entry[1] if entry[1] else entry[0]
    return f"class_{cls_id}"

# --- Config ------------------------------------------------------------------
CONF_THRESH  = 0.5
# PERF: Reduced resolution � YOLO runs much faster on 320x240 vs 640x480
# You can bump back to 640x480 if accuracy matters more than speed
FRAME_WIDTH  = 320
FRAME_HEIGHT = 240

# PERF: Increased frame skip � only run YOLO every 5 frames instead of 3
# Detections still feel responsive but CPU usage drops significantly
FRAME_SKIP   = 5

LOG_COOLDOWN_SECONDS = 5
_last_logged_time = {0: {}, 1: {}}

# --- Load model --------------------------------------------------------------
print(f"[..] Loading model from: {MODEL_PATH}")
model = YOLO(MODEL_PATH, task="detect")
# PERF: Warm up the model once so first real frame isn't slow
model(np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8), verbose=False)
print(f"[OK] Model loaded and warmed up: {MODEL_FORMAT}")

# PERF: Single lock for the model � YOLO is not thread-safe.
# Both camera threads share one model but take turns via this lock.
# This avoids crashes and is faster than loading two model instances.
model_lock = threading.Lock()

# --- QR / Plate decode helpers -----------------------------------------------
_qr_detector = cv2.QRCodeDetector()

try:
    import pytesseract
    _TESSERACT_OK = True
except ImportError:
    _TESSERACT_OK = False

PLATE_OCR_CONFIG = (
    "--oem 3 --psm 6 "
    "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)
PLATE_MIN_CHARS = 4
PLATE_MAX_CHARS = 12

def _decode_qr(crop_bgr):
    data, _, _ = _qr_detector.detectAndDecode(crop_bgr)
    if data:
        return data.strip()
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    data, _, _ = _qr_detector.detectAndDecode(gray)
    return data.strip() if data else None

def _preprocess_for_ocr(crop_bgr):
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(thr) < 127:
        thr = cv2.bitwise_not(thr)
    return thr

def _decode_plate(crop_bgr):
    if not _TESSERACT_OK:
        return None
    thr = _preprocess_for_ocr(crop_bgr)
    raw = pytesseract.image_to_string(thr, config=PLATE_OCR_CONFIG).strip()
    clean = "".join(c for c in raw if c.isalnum())
    return clean if PLATE_MIN_CHARS <= len(clean) <= PLATE_MAX_CHARS else None

# --- CSV setup ---------------------------------------------------------------
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="") as f:
        csv.writer(f).writerow(["timestamp", "run_time", "camera", "category", "class_id", "class_name", "content", "confidence"])

csv_lock = threading.Lock()

# PERF: CSV writes happen in a background thread via a queue
# so they never block the camera/YOLO loop
csv_queue = queue.Queue()

def csv_writer_worker():
    while True:
        row = csv_queue.get()
        if row is None:
            break
        with csv_lock:
            with open(CSV_PATH, "a", newline="") as f:
                csv.writer(f).writerow(row)

csv_thread = threading.Thread(target=csv_writer_worker, daemon=True)
csv_thread.start()

def log_to_csv(cam_idx, camera_name, class_id, class_name, confidence, decoded=None, run_time="00:00"):
    now = time.time()
    last_time = _last_logged_time[cam_idx].get(class_id, 0)
    if now - last_time < LOG_COOLDOWN_SECONDS:
        return
    _last_logged_time[cam_idx][class_id] = now
    entry    = CLASS_MAP.get(class_id)
    category = entry[0] if entry else "Unknown"
    content  = (entry[1] if entry and entry[1] else None) or decoded or class_name
    csv_queue.put([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        run_time, camera_name, category, class_id, class_name, content, f"{confidence:.4f}"
    ])

# --- Camera config -----------------------------------------------------------
CAMERAS = [
    {"index": 0, "name": "Camera 1"},
    {"index": 1, "name": "Camera 2"},
]

camera_state = {
    0: {
        "picam":          None,
        "lock":           threading.Lock(),
        "detections":     [],
        "frame_count":    0,
        "last_annotated": None,
        # PERF: Each camera gets a frame buffer queue (maxsize=1 = always latest frame)
        # The MJPEG streamer reads from here instead of blocking on capture
        "frame_queue":    queue.Queue(maxsize=1),
    },
    1: {
        "picam":          None,
        "lock":           threading.Lock(),
        "detections":     [],
        "frame_count":    0,
        "last_annotated": None,
        "frame_queue":    queue.Queue(maxsize=1),
    },
}

def init_camera(cam_idx):
    try:
        picam = Picamera2(CAMERAS[cam_idx]["index"])
        config = picam.create_video_configuration(
            main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"},
            # PERF: buffer_count=2 reduces memory pressure vs default 4
            buffer_count=2,
        )
        picam.configure(config)
        picam.start()
        time.sleep(0.5)
        print(f"[OK] Camera {cam_idx} started")
        return picam
    except Exception as e:
        print(f"[!!] Camera {cam_idx} not available: {e}")
        return None

def release_all_cameras():
    for cam_idx in camera_state:
        picam = camera_state[cam_idx]["picam"]
        if picam:
            try:
                picam.stop()
                picam.close()
            except Exception:
                pass
            camera_state[cam_idx]["picam"] = None
    print("[OK] All cameras released")

# --- PERF: Capture + YOLO runs in a dedicated background thread per camera ---
# The MJPEG generator just reads the latest processed frame from the queue.
# This decouples slow YOLO inference from the HTTP streaming rate.
def capture_and_infer(cam_idx):
    cam_name = CAMERAS[cam_idx]["name"]
    state    = camera_state[cam_idx]
    color    = (0, 255, 100) if cam_idx == 0 else (0, 180, 255)
    retry_interval = 5.0
    last_retry = 0

    while True:
        picam = camera_state[cam_idx]["picam"]
        if picam is None:
            now = time.time()
            if now - last_retry > retry_interval:
                camera_state[cam_idx]["picam"] = init_camera(cam_idx)
                last_retry = now
            # Push placeholder frame so stream stays alive
            blank = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype="uint8")
            blank[:] = (20, 20, 30)
            cv2.putText(blank, f"{cam_name} - not connected",
                        (20, FRAME_HEIGHT // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 255), 1)
            ret, buf = cv2.imencode(".jpg", blank)
            if ret:
                try:
                    state["frame_queue"].put_nowait(buf.tobytes())
                except queue.Full:
                    pass
            time.sleep(0.5)
            continue

        try:
            # PERF: capture_array() without a lock � Picamera2 is thread-safe
            # for captures; the lock was causing unnecessary stalls before
            frame_rgb = picam.capture_array()
        except Exception as e:
            print(f"[!!] Camera {cam_idx} capture error: {e}")
            camera_state[cam_idx]["picam"] = None
            time.sleep(1.0)
            continue

        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        state["frame_count"] += 1

        if state["frame_count"] % FRAME_SKIP == 0:
            try:
                # PERF: model_lock ensures only one camera runs YOLO at a time
                # avoiding race conditions and reducing peak memory usage
                with model_lock:
                    results = model(frame, conf=CONF_THRESH, verbose=False,
                                    # PERF: half=True uses FP16 � ~2x faster on supported hardware
                                    # Comment this out if you see accuracy issues
                                    # half=True,
                                    # PERF: imgsz matches our capture size exactly � no internal resize
                                    imgsz=max(FRAME_WIDTH, FRAME_HEIGHT))
                detections = []
                for result in results:
                    for box in result.boxes:
                        cls_id   = int(box.cls[0])
                        cls_name = get_class_name(cls_id)
                        conf     = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = f"{cls_name} {conf:.2f}"
                        bg_y  = max(y1 - 20, 0)
                        cv2.rectangle(frame, (x1, bg_y), (x1 + len(label) * 8, y1), color, -1)
                        cv2.putText(frame, label, (x1 + 3, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

                        # QR / plate decode
                        decoded = None
                        crop = frame[max(0,y1):min(frame.shape[0],y2),
                                     max(0,x1):min(frame.shape[1],x2)]
                        if crop.size > 0:
                            if cls_id == QR_CLASS_ID:
                                decoded = _decode_qr(crop)
                            elif cls_id == PLATE_CLASS_ID:
                                decoded = _decode_plate(crop)

                        detections.append({
                            "class_id":   cls_id,
                            "class_name": cls_name,
                            "confidence": round(conf, 4),
                            "camera":     cam_name,
                            "decoded":    decoded,
                        })
                        log_to_csv(cam_idx, cam_name, cls_id, cls_name, conf,
                                   decoded=decoded, run_time=current_run_time)

                state["detections"]     = detections
                state["last_annotated"] = frame.copy()

            except Exception as e:
                print(f"[!!] YOLO error on camera {cam_idx}: {e}")

        else:
            if state["last_annotated"] is not None:
                frame = state["last_annotated"].copy()

        cv2.putText(frame, cam_name, (8, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        # PERF: Lower JPEG quality = smaller payload = faster streaming
        ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        if ret:
            # PERF: put_nowait + discard old frame if full � never blocks the capture loop
            try:
                state["frame_queue"].put_nowait(buf.tobytes())
            except queue.Full:
                try:
                    state["frame_queue"].get_nowait()
                except queue.Empty:
                    pass
                state["frame_queue"].put_nowait(buf.tobytes())

# --- Start background capture threads ----------------------------------------
for idx in range(len(CAMERAS)):
    camera_state[idx]["picam"] = init_camera(idx)
    t = threading.Thread(target=capture_and_infer, args=(idx,), daemon=True)
    t.start()
    print(f"[OK] Capture thread started for camera {idx}")

# --- MJPEG streamer � just reads from queue, no blocking work here -----------
def generate_frames(cam_idx):
    state = camera_state[cam_idx]
    while True:
        try:
            frame_bytes = state["frame_queue"].get(timeout=2.0)
        except queue.Empty:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
               + frame_bytes + b"\r\n")

# --- Routes ------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed/0")
def video_feed_0():
    return Response(generate_frames(0),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/video_feed/1")
def video_feed_1():
    return Response(generate_frames(1),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/detections/0")
def detections_0():
    return jsonify(camera_state[0]["detections"])

@app.route("/detections/1")
def detections_1():
    return jsonify(camera_state[1]["detections"])

@app.route("/download_csv")
def download_csv():
    return send_file(os.path.abspath(CSV_PATH), mimetype="text/csv",
                     as_attachment=True,
                     download_name=f"detections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

@app.route("/clear_csv", methods=["POST"])
def clear_csv():
    with csv_lock:
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "run_time", "camera", "category", "class_id", "class_name", "content", "confidence"])
    for cam_idx in _last_logged_time:
        _last_logged_time[cam_idx].clear()
    return jsonify({"status": "cleared"})

@app.route("/set_run_time", methods=["POST"])
def set_run_time():
    global current_run_time
    data = request.get_json(silent=True) or {}
    current_run_time = data.get("run_time", "00:00")
    return jsonify({"status": "ok"})

@app.route("/status")
def status():
    return jsonify({
        "model": MODEL_FORMAT,
        "cameras": [
            {
                "cam_idx": i,
                "name": CAMERAS[i]["name"],
                "active": camera_state[i]["picam"] is not None,
                "frames_processed": camera_state[i]["frame_count"],
            }
            for i in range(len(CAMERAS))
        ]
    })

# --- Entry point -------------------------------------------------------------
if __name__ == "__main__":
    import signal

    def _shutdown(sig, frame):
        print("\n[>>] Shutting down...")
        csv_queue.put(None)
        release_all_cameras()
        os._exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print(f"[>>] YOLO Scanner | model={MODEL_FORMAT} | 2 cameras")
    print(f"[>>] Dashboard: http://jeffery.local:5000")
    print(f"[>>] Status:    http://jeffery.local:5000/status")
    print(f"[>>] Press Ctrl+C to stop")
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True, use_reloader=False)
    finally:
        csv_queue.put(None)
        release_all_cameras()