import time
import cv2
from ultralytics import YOLO

# --- GPT describe function (your existing one) ---
import base64
from pathlib import Path
from openai import OpenAI
import csv
from datetime import datetime, timezone

client = OpenAI()


def frame_to_data_url(frame_bgr) -> str:
    # Encode frame to JPG bytes
    ok, buf = cv2.imencode(".jpg", frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("Failed to encode frame to JPG.")
    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


def describe_frame(frame_bgr, prompt: str, model: str = "gpt-4.1-mini", detail: str = "low") -> str:
    data_url = frame_to_data_url(frame_bgr)
    resp = client.responses.create(
        model=model,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": data_url, "detail": detail},
            ],
        }],
    )
    return resp.output_text


# --- helpers ---
def person_present(yolo_result, min_conf=0.4):
    names = yolo_result.names
    person_id = next((k for k, v in names.items() if v == "person"), None)
    if person_id is None or yolo_result.boxes is None:
        return False, 0

    count = 0
    for b in yolo_result.boxes:
        if int(b.cls[0]) == person_id and float(b.conf[0]) >= min_conf:
            count += 1
    return count > 0, count


def put_multiline_text(img, text, x=10, y=30, line_h=22):
    for i, line in enumerate(text.splitlines()):
        cv2.putText(img, line[:120], (x, y + i * line_h),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)


def main():
    # Webcam
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam. Try index 1 or remove CAP_DSHOW.")

    # YOLO local model
    model = YOLO("yolov8n.pt")

    PROMPT = """You are analyzing a camera frame for child safety monitoring.

Describe the scene briefly in 3–6 short lines.

Focus on:

1) Who are present:
   - Identify baby, adult, animal, or other people if visible. How many? (e.g. "1 baby in center, 1 adult on left")
   - Approximate age category (infant/toddler/adult) only if reasonably clear.
   - Their position in the frame (left/right/center/background).
   - Tell what they are doing if clear. Anything unusual or concerning?
   
   
2) Nanny behavior (if nanny is visible):
   - If nanny is observable, note if they are paying attention to the baby or looking away.

3) Baby safety assessment (if a baby or young child is visible):
   - Is the baby’s face clearly visible?
   - Is anything covering or very close to the mouth or nose?
   - Is the baby pressed into a soft surface?
   - Baby posture (on back / side / stomach / sitting / being held / unknown).

4) Environmental hazards:
   - Blankets, pillows, cords, small objects, toys near face,
   - Clutter or objects that could pose choking or suffocation risk.

Be cautious.
If something is unclear, say "uncertain".
Do not guess details that are not visible.
"""

    # Throttle settings
    DESCRIBE_EVERY_SEC = 15  # don't spam GPT
    last_describe_t = 0.0
    last_description = "No description yet."
    describing_now = False

    print("Press 'q' to quit.")
    just_updated = False  # flag to indicate if we just got a new description
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Run YOLO on current frame (you can also do every N frames for speed)
        results = model.predict(source=frame, conf=0.35, verbose=False)
        r = results[0]

        # Draw YOLO boxes for debugging
        annotated = r.plot()

        # Gate GPT call: only if a person is present AND enough time passed
        present, num = person_present(r, min_conf=0.45)
        now = time.time()

        should_describe = present and (now - last_describe_t) >= DESCRIBE_EVERY_SEC

        if should_describe and not describing_now:
            describing_now = True

            last_describe_t = now  # set immediately to avoid double triggers

            try:
                # Use low detail for cheaper/faster; use "high" if you want better
                last_description = describe_frame(frame, PROMPT, model="gpt-4.1-mini", detail="low")
                append_log_row(
                    description=last_description,
                    source="laptop_webcam",
                    people_count=num,
                    person_present=present,
                    prompt=PROMPT,
                    gpt_model="gpt-4.1-mini",
                    detail="low",
                )
            except Exception as e:
                last_description = f"Describe error: {type(e).__name__}: {e}"
            finally:
                describing_now = False
                just_updated = True

        # Overlay info
        status = f"People: {num} | GPT every {DESCRIBE_EVERY_SEC}s | Press q to quit"
        cv2.putText(annotated, status, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Show GPT text on the frame

        description = last_description +  f"\n(Last update: {int(now - last_describe_t)}s ago)"
        put_multiline_text(annotated, "GPT:\n" + description, x=10, y=60)

        cv2.imshow("Webcam + YOLO + GPT Describe (Throttled)", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()




LOG_PATH = Path("logs/monitor_log.csv")

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def ensure_log_header(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "timestamp_utc",
                "source",
                "people_count",
                "yolo_person_present",
                "prompt",
                "gpt_model",
                "detail",
                "description",
            ])

def append_log_row(
    description: str,
    source: str = "webcam0",
    people_count: int = 0,
    person_present: bool = False,
    prompt: str = "",
    gpt_model: str = "",
    detail: str = "",
    log_path: Path = LOG_PATH,
):
    ensure_log_header(log_path)

    row = [
        utc_now_iso(),
        source,
        people_count,
        int(bool(person_present)),
        prompt.strip().replace("\r\n", "\n"),
        gpt_model,
        detail,
        description.strip().replace("\r\n", "\n"),
    ]

    with log_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(row)

if __name__ == "__main__":
    main()
