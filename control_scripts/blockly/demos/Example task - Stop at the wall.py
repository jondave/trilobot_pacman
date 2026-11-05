# EXAMPLE TASK: drive towards a wall and stop 20 cm before it.
# 1. Point the robot at a wall or large box.
# 2. Run this program. The robot should creep forward with green lights,
#    then stop with red lights when it is closer than 20 cm.
# 3. Challenge: change 20 to 40, then make the lights flash when it stops.
set_lights("green")
while distance() > 20:
    forward(seconds=0.3, power=50)
stop()
set_lights("red")
print("Stopped")
wait(2)
lights_off()
