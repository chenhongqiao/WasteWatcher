import cv2
import imutils
from picamera2 import Picamera2, Preview
import time
import os
import multiprocessing as mp
import json


def detect_motion(img, prev, threshold=200, min_area=800):
    delta = cv2.absdiff(prev, img)

    delta = cv2.threshold(delta, threshold, 255, cv2.THRESH_BINARY)[1]
    delta = cv2.dilate(delta, None, iterations=2)

    contours = cv2.findContours(
        delta.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = imutils.grab_contours(contours)

    movement = False
    for contour in contours:
        if cv2.contourArea(contour) >= min_area:
            movement = True
            break

    return movement, img


from time import perf_counter


def camera_loop(save_queue, llm_queue):
    picam2 = Picamera2()

    camera_config = picam2.create_video_configuration(
        main={"size": (1440, 1080), "format": "XRGB8888"}
    )
    picam2.configure(camera_config)
    picam2.set_controls(
        {
            "ExposureTime": 500,
            "ExposureValue": 8.0,
            "Brightness": 0,
            "AnalogueGain": 5,
            "FrameRate": 240,
        }
    )
    picam2.start()

    try:
        logs = os.listdir("log")
        logs = [int(s.split(".")[0]) for s in logs]
        log_id = max(logs) + 1
    except:
        log_id = 0

    try:
        data = os.listdir("data")
        data = [int(s.split(".")[0]) for s in data]
        data_id = max(data) + 1
    except:
        data_id = 0

    prev = None

    buffer = []
    lst_time = 0
    start_time = time.time()

    while True:
        a1_beg = perf_counter()
        img = picam2.capture_array("main")
        a1_end = perf_counter()

        # a2_beg = perf_counter()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        # a2_end = perf_counter()

        if prev is None:
            prev = gray

        # a3_beg = perf_counter()
        movement, prev = detect_motion(gray, prev)
        # a3_end = perf_counter()

        if movement == True and time.time() - start_time > 1:
            # a4_beg = perf_counter()
            print(f"Detected {log_id}.")
            # cv2.imwrite(f"log/{log_id}.jpg", img)
            buffer.append(log_id)
            save_queue.put((log_id, img))
            log_id += 1
            lst_time = time.time()
            # a4_end = perf_counter()
            print(f"Capture: {a1_end-a1_beg}")
            # print(f"Detect: {a3_end-a3_beg}")
            # print(f"Image Processing: {a2_end-a2_beg}")
            # print(f"Save: {a4_end-a4_beg}")
        elif len(buffer) > 0 and time.time() - lst_time > 0.2:
            print(f"Movement completed. {len(buffer)} Frames.")
            with open(f"data/{data_id}.json", "w") as f:
                f.write(json.dumps(buffer))
            # final_frame = buffer[len(buffer)//2]
            # cv2.imwrite(f"data/{data_id}.jpg", final_frame)
            # queue.put(data_id)
            llm_queue.put(buffer)
            data_id += 1
            buffer.clear()
