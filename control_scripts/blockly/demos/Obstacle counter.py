# Count obstacles while driving forwards.
bumps = 0
set_lights("green")
for step in count(1, 10):
    if distance() < 20:
        bumps += 1
        print("Obstacle number", bumps)
        flash_lights("red", times=2)
        backward(seconds=1, power=50)
        turn_left(seconds=0.6, power=60)
    else:
        forward(seconds=0.5, power=50)
stop()
lights_off()
print("Total obstacles:", bumps)
