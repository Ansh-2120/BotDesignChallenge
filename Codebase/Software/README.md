# Bot Design Challenge

> Real-time multi-object detection system running on Raspberry Pi 5 with dual Pi Camera Rev 1.3 modules, YOLOv8 inference, live browser dashboard, QR code & number plate decoding, and CSV logging.

**Dashboard:** [http://192.168.0.231:5000](http://192.168.0.231:5000)  
---

## Features

- Dual camera MJPEG streaming via Flask
- Custom YOLOv8 model with 18 detection classes
- NCNN model support for faster CPU inference on RPi
- Live QR code decoding using OpenCV
- Number plate OCR using Tesseract
- Browser dashboard with Category / Content output format
- Manual stopwatch (START / PAUSE / RESET) synced to CSV logs
- Background CSV writer — non-blocking detection loop
- Auto-retry for disconnected cameras
- Cap mode for testing on PC with webcam or video file

---

## Hardware

| Component | Spec |
|-----------|------|
| SBC | Raspberry Pi 5 |
| Cameras | 2x Pi Camera Module Rev 1.3 (OV5647, 5MP) |
| Connections | CAM0 and CAM1 FFC ports |
| Storage | MicroSD 16GB+ |
| OS | Raspberry Pi OS (64-bit) |

---

## Project Structure

```
BotDesignChallenge/
├── app/
│   ├── app.py                    # Flask server + YOLO inference
│   └── templates/
│       └── index.html            # Dashboard UI
├── model/
│   ├── best.pt                   # YOLOv8 PyTorch weights
│   ├── best_ncnn_model.param     # NCNN model (faster on RPi CPU)
│   └── best_ncnn_model.bin
├── data/
│   └── detections.csv            # Auto-generated detection log
├── config/
│   └── yolo_scanner.service      # systemd autostart service
├── scripts/
│   └── setup.sh                  # One-time setup script
└── requirements.txt
```

---

## Setup


### 1. Run Setup Script (once)

```bash
bash scripts/setup.sh
```

This installs:
- `python3-picamera2` — RPi camera library
- `tesseract-ocr` — number plate OCR engine
- `libopencv-dev` — OpenCV system libraries
- Python venv with `--system-site-packages`
- All packages from `requirements.txt`

### 2. Run the App

```bash
source venv/bin/activate
python app/app.py
```

Open dashboard on any device on the same network:

```
http://192.168.0.231:5000
```

Press `Ctrl+C` to stop — cameras and CSV writer will be released cleanly.

---

## Dashboard

The browser dashboard provides:

- Live annotated MJPEG streams from both cameras
- Detection output in **Category / Content** format
- Combined summary when multiple objects detected simultaneously
- Manual stopwatch — START, PAUSE, RESUME, RESET
- Detection log with run-time stamps
- CSV download and clear buttons
- Live stats: object counts, total logged, run time, clock

### Output Format

```
Category:  Face recognition, Vehicle
Content:   Keanu Reeves, Car
```

---

## Detection Classes

| Class ID | Category | Content |
|----------|----------|---------|
| 0 | Face recognition | Roger Federer |
| 1 | Face recognition | Keanu Reeves |
| 2 | Face recognition | Henry Cavill |
| 3 | Parcel | Parcel |
| 4 | QR code | *(decoded at runtime)* |
| 5 | Smart switch | Smart Console |
| 6 | Furniture | Chair |
| 7 | Furniture | Dining Table |
| 8 | Pets | Cat |
| 9 | Pets | Dog |
| 10 | Vehicle | Bicycle |
| 11 | Vehicle | Car |
| 12 | Vehicle | Motorbike |
| 13 | Brand logo | Apple |
| 14 | Brand logo | Tesla |
| 15 | Brand logo | Maybach |
| 16 | Brand logo | Keus |
| 17 | Vehicle number plate | *(OCR at runtime)* |

---

## CSV Log Format

All detections logged to `data/detections.csv`:

```
timestamp, run_time, camera, category, class_id, class_name, content, confidence
2026-03-11 22:54:47, 01:23, Camera 1, Vehicle, 11, Car, Car, 0.8812
```

`run_time` = elapsed time from the dashboard stopwatch at the moment of detection.

---

## Configuration

Key settings in `app/app.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CONF_THRESH` | `0.5` | Minimum detection confidence |
| `FRAME_WIDTH / HEIGHT` | `320 x 240` | Capture resolution |
| `FRAME_SKIP` | `5` | Run YOLO every N frames |
| `LOG_COOLDOWN_SECONDS` | `5` | Min seconds between CSV logs per class per camera |

---

## Cap Mode (PC Testing)

Test on a PC with a webcam or video file — no RPi needed:

```bash
python app/app.py --cap                    # webcam index 0
python app/app.py --cap --source 1         # webcam index 1
python app/app.py --cap --source video.mp4
python app/app.py --cap --source image.jpg
python app/app.py --cap --conf 0.35
```

Controls: `Q` / `ESC` = quit · `S` = save frame · `SPACE` = pause/resume

---

## Autostart on Boot

During `setup.sh` you are asked to install the systemd service. If enabled:

```bash
sudo systemctl status yolo_scanner     # check status
sudo systemctl restart yolo_scanner    # restart
sudo systemctl disable yolo_scanner    # disable autostart
```

---

## Troubleshooting

**Port 5000 already in use**
```bash
sudo fuser -k 5000/tcp
```

**Camera not detected**
```bash
rpicam-hello --list-cameras
```
Re-seat the FFC ribbon cable on the Pi Camera Rev 1.3 if not listed.

**picamera2 not found inside venv**
```bash
# Venv must be created with system site packages
python3 -m venv venv --system-site-packages
```

**Tesseract not found**
```bash
sudo apt install -y tesseract-ocr
```

**After git pull, restart**
```bash
sudo fuser -k 5000/tcp
source venv/bin/activate
python app/app.py
```

---

## Requirements

```
ultralytics>=8.0.0
flask>=3.0.0
opencv-python-headless>=4.9.0
numpy>=1.24.0
pytesseract>=0.3.10
```

> `picamera2` is installed via `apt`, not pip.

---

*Bot Design Challenge · Raspberry Pi 5 · Pi Camera Rev 1.3 · YOLOv8*
