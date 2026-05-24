# model/

Place your model files here after cloning. These are git-ignored (too large for GitHub).

## Files needed
- best.pt                  (PyTorch weights — fallback)
- best_ncnn_model.param    (NCNN architecture — fastest on RPi)
- best_ncnn_model.bin      (NCNN weights — fastest on RPi)

## Copy from your PC via SCP
```
scp best.pt best_ncnn_model.param best_ncnn_model.bin  pi@<rpi-ip>:~/rpi_yolo_scanner/model/
```

## Your class names
| ID | Class |
|----|-------|
| 0  | Roger Federer |
| 1  | Keanu Reeves |
| 2  | Henry Cavill |
| 3  | parcel box |
| 4  | QR codes |
| 5  | Smart Console |
| 6  | cats |
| 7  | dogs |
| 8  | bicycle |
| 9  | cars |
| 10 | motorbike |
| 11 | Apple_Logo |
| 12 | Tesla_Logo |
| 13 | Maybach_Logo |
