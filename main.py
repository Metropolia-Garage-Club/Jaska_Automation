import asyncio
import sys
import time 
import pygame

from source.GamepadReader import read_gamepad, reinit_controller, controller, controller_active
from source.Config import mapping, config
from source.ControlLogic import driver

# This is the main script
# The controlling logic lives here (process_commands)
# You can create your own functionalities for the driving controls here



# TODO 
# Add write multiple registers functionality to MotorDrive and make use of it in motor control logic to reduce amount of writes?
# Check to make sure this makes sense for DIR + SPEED combo, it might not with current implementation
# Timer for emergency stop (> 5 seconds before it can be toggled off, to let the magnetic field dissipate and the capacitors to discharge)
# Refactor and clean MODBUS code (Very chatGPT barebones)
# Reduce amount of prints and rewrite key events into logging instead.


# Bonus
# Add ROS2 functionality and make a cleaner API point


async def _debug_queue_(queue):
    """Debug function for reading the control commands from gamepad."""
    while True:
        data = await queue.get()
        
        # Only print non-zero axis values and all button events
        control_type = data[0]
        value = data[2]
        
        # Skip axis events with value of 0
        if control_type == 0 and value == 0:  # Axis with zero value
            queue.task_done()
            continue
        
        print(f"Command: {data}")
        print("Control id:", data[1])
        queue.task_done()

        if data == (mapping.CONTROLLER_TYPE["Button"], mapping.BUTTON_ID["Cross"], mapping.BUTTON_STATE["Pressed"]):
            if controller_active:
                try:
                    print("Joystick state: ", controller.get_button(10))  # R1
                    print("Battery: ", controller.get_power_level())
                except pygame.error:
                    print("Controller not accessible")
                    
        if queue.empty():
            print("No more data in queue")

async def check_pad_connection_state():
    """
    Monitor controller connection and handle reconnection.
    """
    was_connected = True
    
    while True:
        await asyncio.sleep(0.2)
        
        is_connected = pygame.joystick.get_count() > 0
        
        # Disconnect event
        if was_connected and not is_connected:
            print("WARNING: Controller disconnected - Emergency stop triggered")
            driver.toggle_motor_stop()
            driver.drive_all(0)
        
        # Reconnect event
        elif not was_connected and is_connected:
            print("Controller reconnected - Reinitializing...")
            if await reinit_controller():
                print("Controller reinitialized successfully")
            else:
                print("Failed to reinitialize controller")
            
        was_connected = is_connected

#############################################################
# MAIN DRIVING CODE
#############################################################

async def process_commands(queue):
    last_sent_values = {}  # Track last sent values
    change_threshold = config.speed_change_treshold  # Minimum change to send update
   
    while True:

        # TODO: I dont know if the draining the queue like this to discard extra commands is efficient, heavily AI made hacky patchwork

        # Drain queue and keep latest values
        pending_commands = {}
        
        # Get at least one item
        control_type, id, value = await queue.get()
        pending_commands[(control_type, id)] = value
       
        # # Drain any additional items
        while not queue.empty():
            try:
                control_type, id, value = queue.get_nowait()
                pending_commands[(control_type, id)] = value
            except asyncio.QueueEmpty:
                break

        # Skip processing if controller is being reinitialized
        if not controller_active:
            await asyncio.sleep(0.01)
            continue
       
        # Process only commands that have changed significantly
        for (control_type, id), value in pending_commands.items():
            key = (control_type, id)
            last_value = last_sent_values.get((key))

            try:
                # For axis values, only send if change is significant
                if control_type == mapping.CONTROLLER_TYPE["Axis"]:
                    if last_value is None or abs(value - last_value) >= change_threshold:
                        if controller.get_button(mapping.BUTTON_ID["R1"]):
                            if id == mapping.AXIS_ID["Left Stick Y"]:
                                driver.drive_left(value)
                            if id == mapping.AXIS_ID["Right Stick Y"]:
                                driver.drive_right(value)
                            last_sent_values[key] = value
                
                # Buttons always get processed (they're discrete events)
                if control_type == mapping.CONTROLLER_TYPE["Button"]:
                    if id == mapping.BUTTON_ID["Circle"]:
                        if value == mapping.BUTTON_STATE["Pressed"]:
                            driver.toggle_motor_stop()
                    if id == mapping.BUTTON_ID["D-Pad Up"]:
                        #if value == mapping.BUTTON_STATE["Pressed"]:
                        if value == (0, 1): #Linux compatible
                            driver.toggle_slow_forward()
                    if id == mapping.BUTTON_ID["D-Pad Down"]:
                        #if value == mapping.BUTTON_STATE["Pressed"]:
                        if value == (0, -1): #Linux compatible
                            driver.toggle_slow_backward()
                    if id == mapping.BUTTON_ID["R1"]:
                        if value == mapping.BUTTON_STATE["Unpressed"]:
                            driver.drive_all(0)
                    last_sent_values[key] = value
                
                elif not controller.get_button(mapping.BUTTON_ID["R1"]) and last_value != 0:
                    driver.drive_all(0)
                    last_sent_values[key] = 0
            except pygame.error:
                pass

        
        await asyncio.sleep(0.01)  # 100Hz update rate


async def main():

    # Create asyncio queue
    command_queue = asyncio.Queue(maxsize=5)
    
    # Start both tasks concurrently
    await asyncio.gather(
        read_gamepad(command_queue),
        process_commands(command_queue),
        #_debug_queue_(command_queue),
        check_pad_connection_state()
    )

if __name__ == "__main__":
    asyncio.run(main())




