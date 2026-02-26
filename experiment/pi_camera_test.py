from picamera2 import Picamera2
import cv2
import time

def main():
    print("Starting Picamera2...")

    picam2 = Picamera2()

    config = picam2.create_video_configuration(
        main={"size": (1280, 720), "format": "RGB888"}
    )

    picam2.configure(config)
    picam2.start()

    # Let auto exposure settleq
    time.sleep(1)

    print("Camera started. Press 'q' to quit.")

    try:
        while True:
            frame_rgb = picam2.capture_array()  # RGB frame
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            frame_bgr = frame_rgb

            cv2.imshow("NoIR Camera Test", frame_bgr)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        print("Stopping camera...")
        picam2.stop()
        picam2.close()
        cv2.destroyAllWindows()
        print("Camera closed cleanly.")

if __name__ == "__main__":
    main()