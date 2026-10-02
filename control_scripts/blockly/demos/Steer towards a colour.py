# Use a simple green-pixel check to choose a direction.
import cv2

attempts = 0
while attempts < 10:
    image = take_picture()
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (40, 70, 70), (80, 255, 255))
    pixels = cv2.countNonZero(mask)
    print("Green pixels:", pixels)
    show_in_live_camera(mask)
    if pixels > 800:
        forward(seconds=0.5, power=50)
    else:
        turn_right(seconds=0.3, power=50)
    attempts += 1
stop()
