"""
Bicycle Watcher - Security Guard
=================================
Tracks a user-selected object (e.g. a parked bicycle) via webcam.
Alerts visually, saves a snapshot, and logs to terminal if the object
moves significantly or disappears from view.

Controls:
  - On launch: drag a box around your bicycle, then press SPACE or ENTER to confirm
  - Click "Reselect" or press 'r' at any time to re-select the region
  - Click "Quit" or press 'q' to quit
"""

import cv2
import os
import time
from datetime import datetime


class TemplateTracker:
    """
    Fallback tracker using template matching.
    Used automatically when opencv-contrib-python is not installed.
    """
    CONFIDENCE_THRESHOLD = 0.45

    def __init__(self):
        self.template = None
        self.template_gray = None

    def init(self, frame, bbox):
        x, y, w, h = [int(v) for v in bbox]
        self.template = frame[y:y + h, x:x + w].copy()
        self.template_gray = cv2.cvtColor(self.template, cv2.COLOR_BGR2GRAY)

    def update(self, frame):
        if self.template_gray is None:
            return False, None
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(frame_gray, self.template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < self.CONFIDENCE_THRESHOLD:
            return False, None
        h, w = self.template_gray.shape[:2]
        return True, (max_loc[0], max_loc[1], w, h)


def create_tracker():
    """Create a CSRT tracker if contrib is available, else fall back to template matching."""
    for factory in (
        lambda: cv2.TrackerCSRT_create(),
        lambda: cv2.legacy.TrackerCSRT_create(),
    ):
        try:
            tracker = factory()
            print("Using CSRT tracker.")
            return tracker
        except AttributeError:
            pass
    print("opencv-contrib-python not found — using built-in template tracker.")
    print("For better tracking run:  python3 -m pip install opencv-contrib-python")
    return TemplateTracker()


# ── Configuration ─────────────────────────────────────────────────────────────

WEBCAM_INDEX = 0           # Change if your webcam isn't device 0
ALERT_COOLDOWN_SEC = 5     # Minimum seconds between consecutive alerts
MOVE_THRESHOLD_PX = 40     # How many pixels the centre can drift before alert
SNAPSHOT_DIR = "snapshots" # Folder where alert images are saved

# ── UI / button styling ────────────────────────────────────────────────────────

BTN_H          = 38
BTN_PAD_X      = 16
BTN_MARGIN     = 8
BTN_BG         = (30,  30,  30)
BTN_HOVER_BG   = (75,  75,  75)
BTN_BORDER     = (120, 120, 120)
BTN_TEXT_COLOR = (230, 230, 230)
UI_FONT        = cv2.FONT_HERSHEY_SIMPLEX
UI_SCALE       = 0.6
UI_THICK       = 1

# ─────────────────────────────────────────────────────────────────────────────


def centre(bbox):
    x, y, w, h = bbox
    return (x + w // 2, y + h // 2)


def distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def draw_text_with_bg(frame, text, pos,
                      font_scale=0.75, color=(255, 255, 255),
                      bg=(0, 0, 0), thickness=2, padding=5):
    """Draw text with a solid black background so it's always readable."""
    (tw, th), baseline = cv2.getTextSize(text, UI_FONT, font_scale, thickness)
    x, y = pos
    cv2.rectangle(frame,
                  (x - padding,      y - th - padding),
                  (x + tw + padding, y + baseline + padding),
                  bg, -1)
    cv2.putText(frame, text, (x, y), UI_FONT, font_scale,
                color, thickness, cv2.LINE_AA)


def draw_buttons(frame, mouse_x, mouse_y):
    """
    Draw clickable buttons at the bottom-right of the frame.
    Returns a dict mapping button name -> (x, y, w, h).
    """
    h, w = frame.shape[:2]
    specs = [
        ("reselect", "Reselect  [R]"),
        ("quit",     "Quit  [Q]"),
    ]

    # Calculate rects right-to-left so order is left=Reselect, right=Quit
    rects = {}
    x_cursor = w - BTN_MARGIN
    for name, label in reversed(specs):
        (tw, _), _ = cv2.getTextSize(label, UI_FONT, UI_SCALE, UI_THICK)
        bw = tw + BTN_PAD_X * 2
        bx = x_cursor - bw
        by = h - BTN_H - BTN_MARGIN
        x_cursor = bx - BTN_MARGIN
        rects[name] = (bx, by, bw, BTN_H)

    for name, label in specs:
        bx, by, bw, bh = rects[name]
        hovered = bx <= mouse_x <= bx + bw and by <= mouse_y <= by + bh
        bg = BTN_HOVER_BG if hovered else BTN_BG
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), bg, -1)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), BTN_BORDER, 1)
        (tw, th), _ = cv2.getTextSize(label, UI_FONT, UI_SCALE, UI_THICK)
        tx = bx + (bw - tw) // 2
        ty = by + (bh + th) // 2
        cv2.putText(frame, label, (tx, ty), UI_FONT, UI_SCALE,
                    BTN_TEXT_COLOR, UI_THICK, cv2.LINE_AA)

    return rects


def draw_alert_overlay(frame, message):
    """Draw a red border and alert message with a solid black background."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 6)
    draw_text_with_bg(frame, f"ALERT: {message}", (10, h - 55),
                      font_scale=0.9, color=(0, 0, 255), bg=(0, 0, 0),
                      thickness=2, padding=6)


def save_snapshot(frame, reason):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(SNAPSHOT_DIR, f"alert_{ts}.jpg")
    cv2.imwrite(filename, frame)
    print(f"[{ts}] Snapshot saved: {filename}")
    return filename


def log_alert(reason):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] *** ALERT *** {reason}")


def select_roi(cap):
    """Let the user draw a bounding box. Returns (x, y, w, h) or None."""
    print("\nDraw a box around your bicycle, then press SPACE or ENTER to confirm.")
    print("Press 'c' to cancel.\n")

    ret, frame = cap.read()
    if not ret:
        print("ERROR: Could not read from webcam.")
        return None

    bbox = cv2.selectROI("Select bicycle -- press SPACE/ENTER to confirm", frame,
                         fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("Select bicycle -- press SPACE/ENTER to confirm")

    if bbox == (0, 0, 0, 0):
        print("No region selected.")
        return None

    return bbox


def main():
    print("=== Bicycle Watcher ===")
    print(f"Snapshots will be saved to: ./{SNAPSHOT_DIR}/")
    print("Press 'r' / click Reselect to re-select the region, 'q' / Quit to quit.\n")

    cap = cv2.VideoCapture(WEBCAM_INDEX)
    if not cap.isOpened():
        print(f"ERROR: Cannot open webcam (index {WEBCAM_INDEX}).")
        return

    # ── Initial ROI selection ─────────────────────────────────────────────────
    bbox = select_roi(cap)
    if bbox is None:
        cap.release()
        return

    original_centre = centre(bbox)
    print(f"Tracking started. Original centre: {original_centre}")

    tracker = create_tracker()
    ret, frame = cap.read()
    tracker.init(frame, bbox)

    last_alert_time = 0

    # ── Window + mouse callback ───────────────────────────────────────────────
    WIN = "Bicycle Watcher"
    cv2.namedWindow(WIN)

    mouse_state = {"x": 0, "y": 0, "clicked": False}

    def on_mouse(event, x, y, flags, param):
        mouse_state["x"] = x
        mouse_state["y"] = y
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_state["clicked"] = True

    cv2.setMouseCallback(WIN, on_mouse)

    # ── Main loop ─────────────────────────────────────────────────────────────
    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: Lost webcam feed.")
            break

        success, bbox = tracker.update(frame)
        now = time.time()
        alert_active = False
        alert_reason = ""

        if not success:
            alert_active = True
            alert_reason = "Bicycle not detected!"
        else:
            current_centre = centre([int(v) for v in bbox])
            drift = distance(original_centre, current_centre)

            if drift > MOVE_THRESHOLD_PX:
                alert_active = True
                alert_reason = f"Bicycle moved! ({int(drift)}px drift)"
            else:
                x, y, w, h = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(frame, current_centre, 4, (0, 255, 0), -1)
                draw_text_with_bg(frame, "Watching...", (10, 30),
                                  font_scale=0.8, color=(0, 220, 0),
                                  bg=(0, 0, 0), thickness=2)

        if alert_active:
            draw_alert_overlay(frame, alert_reason)
            if now - last_alert_time >= ALERT_COOLDOWN_SEC:
                log_alert(alert_reason)
                save_snapshot(frame, alert_reason)
                last_alert_time = now

        # Draw buttons and get their rects for click-testing
        button_rects = draw_buttons(frame, mouse_state["x"], mouse_state["y"])

        cv2.imshow(WIN, frame)

        # Resolve a mouse click into an action name
        clicked_action = None
        if mouse_state["clicked"]:
            mouse_state["clicked"] = False
            mx, my = mouse_state["x"], mouse_state["y"]
            for name, (bx, by, bw, bh) in button_rects.items():
                if bx <= mx <= bx + bw and by <= my <= by + bh:
                    clicked_action = name

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or clicked_action == "quit":
            print("Quitting.")
            break
        elif key == ord('r') or clicked_action == "reselect":
            bbox = select_roi(cap)
            if bbox is not None:
                original_centre = centre(bbox)
                tracker = create_tracker()
                ret, frame = cap.read()
                tracker.init(frame, bbox)
                print(f"Re-tracking from new position: {original_centre}")
                cv2.setMouseCallback(WIN, on_mouse)  # re-attach after ROI window closes

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
