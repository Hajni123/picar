with open("/home/khajni/robot_car/picar_hailo_multimode.py", "r") as f:
    code = f.read()

# Cseréljük ki az ékezetes státuszokat tiszta ASCII szövegekre
replacements = {
    "AKADÁLY ELOTT! TOLATAS...": "AKADALY ELOTT! TOLATAS...",
    "AKADALY! HÁTRÁLÁS...": "AKADALY! HATRALAS...",
    "ÜTKÖZÉS / AKADÁLY: TOLATÁS...": "UTKOZES / AKADALY: TOLATAS...",
    "KORREKCIÓS FORDULÁS": "KORREKCIOS FORDULAS",
    "ELHALADás ÉS ÚJRATERVEZÉS": "ELHALADAS ES UJRATERVEZES",
    "UT TISZTA - ELORE": "UT TISZTA - ELORE",
    "TOLATAS AZ AKADALYTOL": "TOLATAS AZ AKADALYTOL",
    "ELHALADAS": "ELHALADAS",
    "HALADÁS ELŐRE": "HALADAS ELORE",
    "ÜTKÖZÉS / ELAKADÁS -> Korrekciós tolatás...": "UTKOZES / ELAKADAS -> Korrekcios tolatas...",
    "AKADÁLY ÉSZLELVE -> Tolatás...": "AKADALY ESZLELVE -> Tolatas...",
    "ÚT TISZTA - HALADÁS ELŐRE": "UT TISZTA - HALADAS ELORE",
    "HÁTRÁLÁS...": "HATRALAS...",
    "KITÉRŐ FORDULÁS": "KITERO FORDULAS",
    "ÚJRATERVEZÉS ÉS ELHALADÁS": "UJRATERVEZES ES ELHALADAS",
    "TOLATAS!": "TOLATAS!",
    "MEGALLVA (EMBER ALL)": "MEGALLVA (EMBER ALL)",
    "KOVETES (MOZOGSZ)": "KOVETES (MOZOGSZ)",
    "TARTAS": "TARTAS",
    "KERESES...": "KERESES..."
}

for k, v in replacements.items():
    code = code.replace(k, v)

# Általános biztonsági cserék az ékezetes betűkre
code = code.replace("AKADÁLY", "AKADALY").replace("HÁTRÁLÁS", "HATRALAS").replace("FORDULÁS", "FORDULAS")
code = code.replace("ÚJRATERVEZÉS", "UJRATERVEZES").replace("HALADÁS", "HALADAS").replace("ELŐRE", "ELORE")
code = code.replace("TISZTA", "TISZTA").replace("ÜTKÖZÉS", "UTKOZES").replace("ELAKADÁS", "ELAKADAS")

with open("/home/khajni/robot_car/picar_hailo_multimode.py", "w") as f:
    f.write(code)

print("Kész!")
