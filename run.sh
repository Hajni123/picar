#!/bin/bash
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/1000

cd /home/khajni/hailo-apps
source setup_env.sh

ENGINE="det"
MODE=1
ENHANCE=""

while true; do
    echo "=================================================="
    echo "  PiCar Indítás: Modell=$ENGINE | Mód=$MODE $ENHANCE"
    echo "=================================================="
    python3 /home/khajni/robot_car/picar_hailo_multimode.py --engine $ENGINE --mode $MODE $ENHANCE
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Kilépés..."
        break
    fi

    if [ $EXIT_CODE -ge 100 ]; then
        ENHANCE="--enhance"
        EXIT_CODE=$((EXIT_CODE - 100))
    else
        ENHANCE=""
    fi

    TARGET_ENGINE_CODE=$((EXIT_CODE / 10 * 10))
    MODE=$((EXIT_CODE % 10))

    if [ $TARGET_ENGINE_CODE -eq 10 ]; then
        ENGINE="det"
    elif [ $TARGET_ENGINE_CODE -eq 20 ]; then
        ENGINE="seg"
    fi

    sleep 0.3
done
