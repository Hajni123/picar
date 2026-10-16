from gpiozero import PWMOutputDevice

feher_bal_elore  = PWMOutputDevice(7, frequency=100)
zold_bal_hatra   = PWMOutputDevice(8, frequency=100)
barna_jobb_elore = PWMOutputDevice(25, frequency=100)
sarga_jobb_hatra = PWMOutputDevice(27, frequency=100)

SEB_GYORS   = 0.42   # Külső kerék ívkanyarban
SEB_LASSU   = 0.18   # Belső kerék ívkanyarban
SEB_EGYENES = 0.38   # Sima egyenes menet
SEB_FORGAS  = 0.32   # Helyben fordulás, ha csak a kanyar nyilat nyomod

def stop():
    """Minden motort azonnal leállít."""
    feher_bal_elore.value = 0
    zold_bal_hatra.value = 0
    barna_jobb_elore.value = 0
    sarga_jobb_hatra.value = 0

def drive(steer=0.0, throttle=0.0):
    """
    steer: -1.0 (balra), 0.0 (egyenes), +1.0 (jobbra)
    throttle: 1.0 (előre), -1.0 (hátra), 0.0 (megállás)
    """
    if throttle == 0.0 and steer == 0.0:
        stop()
        return

    # 1. ELŐREMENET + KANYARODÁS (Ívkanyar)
    if throttle > 0:
        zold_bal_hatra.value = 0
        sarga_jobb_hatra.value = 0
        if steer < 0:      # Előre + Balra
            feher_bal_elore.value = SEB_LASSU
            barna_jobb_elore.value = SEB_GYORS
        elif steer > 0:    # Előre + Jobbra
            feher_bal_elore.value = SEB_GYORS
            barna_jobb_elore.value = SEB_LASSU
        else:              # Csak sima Előre
            feher_bal_elore.value = SEB_EGYENES
            barna_jobb_elore.value = SEB_EGYENES

    # 2. HÁTRAMENET + KANYARODÁS
    elif throttle < 0:
        feher_bal_elore.value = 0
        barna_jobb_elore.value = 0
        if steer < 0:      # Hátra + Balra
            zold_bal_hatra.value = SEB_LASSU
            sarga_jobb_hatra.value = SEB_GYORS
        elif steer > 0:    # Hátra + Jobbra
            zold_bal_hatra.value = SEB_GYORS
            sarga_jobb_hatra.value = SEB_LASSU
        else:              # Csak sima Hátra
            zold_bal_hatra.value = SEB_EGYENES
            sarga_jobb_hatra.value = SEB_EGYENES

    # 3. CSAK KANYAR GOMB (Helyben forgás előremenet nélkül)
    elif throttle == 0.0:
        if steer < 0:      # Csak Balra nyíl
            feher_bal_elore.value = 0
            sarga_jobb_hatra.value = 0
            zold_bal_hatra.value = SEB_FORGAS
            barna_jobb_elore.value = SEB_FORGAS
        elif steer > 0:    # Csak Jobbra nyíl
            zold_bal_hatra.value = 0
            barna_jobb_elore.value = 0
            feher_bal_elore.value = SEB_FORGAS
            sarga_jobb_hatra.value = SEB_FORGAS

stop()
