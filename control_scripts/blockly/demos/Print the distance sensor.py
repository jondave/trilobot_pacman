# Read the distance sensor and print each reading.
for i in count(1, 10):
    cm = distance()
    print("Reading", i)
    print("Distance cm:", cm)
    if cm < 20:
        print("Too close")
        set_lights("red")
    else:
        set_lights("green")
    wait(0.5)
lights_off()
print("Finished")
