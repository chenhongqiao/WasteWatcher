from picamera2 import Picamera2, Preview

picam2 = Picamera2()

camera_config = picam2.create_video_configuration(main={"size": (1440, 1080), "format": "XRGB8888"})
picam2.configure(camera_config)
picam2.set_controls({"ExposureTime": 500, "ExposureValue": 8.0, "Brightness": 0, "AnalogueGain": 5, 'FrameRate': 240})
picam2.start()

picam2.capture_file("test.jpg")