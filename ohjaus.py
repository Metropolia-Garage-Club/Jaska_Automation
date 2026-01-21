from nicegui import ui
from source.ModbusDriver import modbus
import threading
import time

# ====== ASETUKSET ======
MAX_SPEED = 500 # max speed 1000
DEADZONE = 0.1
RAMP_STEP = 0.08      # 0.02 = pehmeä, 0.1 = nopea
MODBUS_INTERVAL = 0.1  # sekuntia (10 Hz)

# ====== TILA ======
state = {
    'x': 0.0,
    'y': 0.0,
    'm1': 0.0,
    'm2': 0.0,
    'M1': 0,
    'M2': 0,
    'S1': 0,
    'S2': 0,
}

lock = threading.Lock()

# ====== APUFUNKTIOT ======
def deadzone(v):
    return 0.0 if abs(v) < DEADZONE else v

def ramp(current, target):
    if abs(target - current) <= RAMP_STEP:
        return target
    return current + RAMP_STEP if target > current else current - RAMP_STEP

# ====== DIFFERENTIAALIOHJAUS (UI-LOOPPI) ======
def control_loop():
    with lock:
        x = deadzone(state['x'])
        y = deadzone(state['y'])

        left_target  = max(-1, min(1, y - x))
        right_target = max(-1, min(1, y + x))

        state['m1'] = ramp(state['m1'], left_target)
        state['m2'] = ramp(state['m2'], right_target)

        state['S1'] = 1 if state['m1'] < 0 else 0
        state['S2'] = 1 if state['m2'] < 0 else 0

        state['M1'] = int(abs(state['m1']) * MAX_SPEED)
        state['M2'] = int(abs(state['m2']) * MAX_SPEED)

        output.set_text(
            f"M1={state['M1']:4d} S1={state['S1']} | "
            f"M2={state['M2']:4d} S2={state['S2']}"
        )

# ====== MODBUS SÄIE (BLOKKAAVA I/O) ======
def modbus_worker():
    last_M1 = last_M2 = last_S1 = last_S2 = None

    while True:
        with lock:
            M1, S1 = state['M1'], state['S1']
            M2, S2 = state['M2'], state['S2']

        # Lähetä vain jos muuttui (vähemmän kuormaa)
        if (M2, S2) != (last_M2, last_S2):
            modbus.set_direction(4, S2)
            modbus.set_direction(6, S2)
            modbus.set_speed(4, M2)
            modbus.set_speed(6, M2)

            last_M2, last_S2 = M2, S2

        # Jos otat vasemman käyttöön:
        if (M1, S1) != (last_M1, last_S1):
            modbus.set_direction(1, S1)
            modbus.set_direction(3, S1)
            modbus.set_speed(1, M1)
            modbus.set_speed(3, M1)
            last_M1, last_S1 = M1, S1

        time.sleep(MODBUS_INTERVAL)

# ====== JOYSTICK EVENTIT ======
def joystick_move(e):
    with lock:
        state['x'] = e.x
        state['y'] = e.y

def joystick_end(_):
    with lock:
        state['x'] = 0.0
        state['y'] = 0.0

# ====== UI ======
ui.label("🎮 Differentiaaliohjaus")

ui.joystick(
    size=80,
    color='blue',
    on_move=joystick_move,
    on_end=joystick_end,
).classes('bg-slate-300')

output = ui.label(
    "M1=0 S1=0 | M2=0 S2=0"
).style("font-family: monospace;")

ui.timer(0.05, control_loop)  # 20 Hz UI-looppi

# ====== KÄYNNISTYS ======
threading.Thread(target=modbus_worker, daemon=True).start()

ui.run(
    host="0.0.0.0",
    port=8080,
    title="Joystick ohjaus"
)
