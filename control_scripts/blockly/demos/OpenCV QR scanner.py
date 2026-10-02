# Scan the robot label and keep the processed camera view live.
import cv2

while True:
    image = take_picture()
    blurred = cv2.GaussianBlur(image, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    hsv_view = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    show_in_live_camera(hsv_view)
    robot_name = scan_robot_qr()
    if robot_name:
        print("Robot:", robot_name)
    wait(0.1)
