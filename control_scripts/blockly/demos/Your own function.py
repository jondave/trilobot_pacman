set_lights("blue")
for _ in range(4):
    forward(seconds=1, power=60)
    turn_right(seconds=0.5, power=60)
wait(1)
for _ in range(4):
    forward(seconds=1, power=60)
    turn_right(seconds=0.5, power=60)
lights_off()
