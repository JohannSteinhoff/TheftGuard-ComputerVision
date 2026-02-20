# Bicycle Watcher

A real-time object-monitoring tool built with Python and OpenCV. Point a webcam at a parked bicycle (or any stationary object), draw a box around it, and the program will alert you the moment it moves or disappears from view.

---

## How It Works

### 1. Region of Interest (ROI) Selection
On launch the live webcam feed is paused and a selection window opens. You drag a rectangle around the object you want to watch. That bounding box is passed to the tracker to establish a baseline position.

### 2. Object Tracking
Every frame from the webcam is fed into the tracker, which attempts to locate the object and return an updated bounding box. Two tracker implementations are supported, chosen automatically at runtime:

| Tracker | When used | Notes |
|---|---|---|
| **CSRT** (Channel and Spatial Reliability Tracking) | `opencv-contrib-python` is installed | More robust; handles lighting changes, partial occlusion, and slight perspective shifts |
| **Template Matching** (built-in fallback) | Contrib package not installed | Converts both the stored template and the current frame to greyscale, then uses `cv2.TM_CCOEFF_NORMED` to find the closest match; a confidence threshold of 0.45 rejects low-quality matches |

### 3. Alert Logic
Each frame, the tracker's returned bounding box centre is compared against the original centre recorded at selection time using Euclidean distance. Two conditions trigger an alert:

- **Moved** — the centre has drifted more than `MOVE_THRESHOLD_PX` pixels (default: 40)
- **Not detected** — the tracker reports failure (confidence too low, or object left the frame)

Alerts are rate-limited by `ALERT_COOLDOWN_SEC` (default: 5 seconds) to avoid log spam.

### 4. Alert Actions
When an alert fires the program simultaneously:
- Draws a **red border** around the entire frame
- Overlays an **ALERT message** with a solid black background so it is always readable
- Prints a **timestamped line** to the terminal
- Saves a **JPEG snapshot** to the `snapshots/` folder with the timestamp in the filename

### 5. UI
The live window is rendered using OpenCV's `imshow` loop at ~30 fps. Clickable buttons are drawn directly onto the frame each tick. A `setMouseCallback` listener tracks cursor position for hover highlighting and detects left-clicks, mapping them to the same actions as keyboard shortcuts.

---

## Requirements

- **Python 3.8+**
- A connected webcam

### Python packages

Install the recommended package for full tracker support:

```
pip install opencv-contrib-python
```

> If you only have `opencv-python` (the base package), the CSRT tracker will not be available and the program will automatically fall back to template matching. Template matching is less robust but requires no extra dependencies.

To check what you have installed:

```
python3 -m pip list | findstr opencv   # Windows
python3 -m pip list | grep opencv      # macOS / Linux
```

---

## Installation

```bash
# 1. Clone or download the project folder
cd path/to/watcher

# 2. Install the dependency
python3 -m pip install opencv-contrib-python
```

No virtual environment is required, but one is recommended for keeping your system Python clean:

```bash
python3 -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS / Linux
python3 -m pip install opencv-contrib-python
```

---

## Running

```bash
python3 watcher.py
```

### Step-by-step

1. A selection window opens showing a still from your webcam.
2. Click and drag a rectangle around the object you want to monitor, then press **Space** or **Enter** to confirm (press `C` to cancel and retry).
3. The live monitoring window opens. A green box tracks the object and "Watching..." is displayed while everything is normal.
4. If the object moves or disappears, a red border and alert message appear and a snapshot is saved to `snapshots/`.

---

## Controls

| Action | Keyboard | Mouse |
|---|---|---|
| Confirm ROI selection | Space / Enter | — |
| Cancel ROI selection | C | — |
| Re-select the tracked region | R | Click **Reselect [R]** button |
| Quit | Q | Click **Quit [Q]** button |

---

## Configuration

All tuneable values are constants at the top of `watcher.py`:

| Constant | Default | Description |
|---|---|---|
| `WEBCAM_INDEX` | `0` | Which camera to use — increment if you have multiple webcams |
| `MOVE_THRESHOLD_PX` | `40` | Pixel distance the object must drift before an alert fires |
| `ALERT_COOLDOWN_SEC` | `5` | Minimum seconds between repeated alerts for the same event |
| `SNAPSHOT_DIR` | `"snapshots"` | Folder where alert images are saved (created automatically) |

---

## Output

Alert snapshots are saved as:

```
snapshots/alert_YYYY-MM-DD_HH-MM-SS.jpg
```

Terminal output follows the same timestamp format:

```
[2024-06-01 14:32:07] *** ALERT *** Bicycle moved! (63px drift)
[2024-06-01 14:32:07] Snapshot saved: snapshots/alert_2024-06-01_14-32-07.jpg
```

---

## Project Structure

```
watcher/
├── watcher.py      # Main application
├── README.md       # This file
└── snapshots/      # Created automatically when the first alert fires
```

---

## Tech Stack

- **Python 3** — standard library (`os`, `time`, `datetime`)
- **OpenCV** (`cv2`) — webcam capture, object tracking, drawing, window management
