# Search for green using a block-friendly OpenCV measurement.
import cv2

attempts = 0
found = False
while attempts < 8 and not found:
    image = take_picture()
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (40, 70, 70), (80, 255, 255))
    pixels = cv2.countNonZero(mask)
    show_in_live_camera(mask)
    print("Look", attempts)
    print("Green pixels:", pixels)
    if pixels > 500:
        flash_lights("green", times=3)
        found = True
    else:
        turn_right(seconds=0.4, power=50)
    attempts += 1
stop()
