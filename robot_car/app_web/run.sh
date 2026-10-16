#!/bin/bash

# Környezet
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/1000

# Hailo
cd /home/khajni/hailo-apps
source setup_env.sh

ENGINE="det"
MODE=1
ENHANCE=""

while true; do
    echo "PiCar indítása: Modell=$ENGINE | Mód=$MODE $ENHANCE"

    python3 /home/khajni/robot_car/app_web/picar_hailo_multimode.py \
        --engine $ENGINE --mode $MODE $ENHANCE

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Kilépés..."
        break
    fi

    # Képjavítás
    if [ $EXIT_CODE -ge 100 ]; then
        ENHANCE="--enhance"
        EXIT_CODE=$((EXIT_CODE - 100))
    else
        ENHANCE=""
    fi

    # Modell és mód
    TARGET_ENGINE_CODE=$((EXIT_CODE / 10 * 10))
    MODE=$((EXIT_CODE % 10))

    if [ $TARGET_ENGINE_CODE -eq 10 ]; then
        ENGINE="det"
    elif [ $TARGET_ENGINE_CODE -eq 20 ]; then
        ENGINE="seg"
    fi

    sleep 0.3
done
