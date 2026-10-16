# A két hajtómotor vezérlése előre, hátra, ívkanyarban és helyben forgáshoz.

from gpiozero import PWMOutputDevice


# Motorok
left_forward = PWMOutputDevice(7, frequency=100)
left_backward = PWMOutputDevice(8, frequency=100)
right_forward = PWMOutputDevice(25, frequency=100)
right_backward = PWMOutputDevice(27, frequency=100)


# Sebességek
FAST_SPEED = 0.42
SLOW_SPEED = 0.18
STRAIGHT_SPEED = 0.38
ROTATION_SPEED = 0.32


# Leállítás
def stop():
    left_forward.value = 0
    left_backward.value = 0
    right_forward.value = 0
    right_backward.value = 0


# Motorvezérlés
def drive(steer=0.0, throttle=0.0):
    if throttle == 0.0 and steer == 0.0:
        stop()
        return

    # Előremenet
    if throttle > 0:
        left_backward.value = 0
        right_backward.value = 0

        if steer < 0:
            left_forward.value = SLOW_SPEED
            right_forward.value = FAST_SPEED
        elif steer > 0:
            left_forward.value = FAST_SPEED
            right_forward.value = SLOW_SPEED
        else:
            left_forward.value = STRAIGHT_SPEED
            right_forward.value = STRAIGHT_SPEED

    # Hátramenet
    elif throttle < 0:
        left_forward.value = 0
        right_forward.value = 0

        if steer < 0:
            left_backward.value = SLOW_SPEED
            right_backward.value = FAST_SPEED
        elif steer > 0:
            left_backward.value = FAST_SPEED
            right_backward.value = SLOW_SPEED
        else:
            left_backward.value = STRAIGHT_SPEED
            right_backward.value = STRAIGHT_SPEED

    # Forgás
    elif throttle == 0.0:
        if steer < 0:
            left_forward.value = 0
            right_backward.value = 0
            left_backward.value = ROTATION_SPEED
            right_forward.value = ROTATION_SPEED
        elif steer > 0:
            left_backward.value = 0
            right_forward.value = 0
            left_forward.value = ROTATION_SPEED
            right_backward.value = ROTATION_SPEED


stop()
