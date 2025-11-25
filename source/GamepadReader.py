import asyncio
import pygame
import time

# This script is responsible for reading data from the controller (Event Handler, no polling)

# PyGame doesnt support advanced functionality like configuring the color of a PS4 controller, but the advantage is that its a library thats kept up to date by a large community.


DEAD_ZONE = 0.05  # Joystick axises are -1 to 1 by default. This is just meant to prevent stick drift when the stick is not used, default 0.05 (= 5 % of full range)

pygame.init()

# Wait for controller to be connected at startup
print("Waiting for a controller to connect...")
while pygame.joystick.get_count() == 0:
    pygame.joystick.quit()   # Deinitialize
    pygame.joystick.init()   # Reinitialize to detect new devices
    time.sleep(0.5)

# Now that get_count() > 0, we can safely create the controller
controller = pygame.joystick.Joystick(0)
controller.init()
print(f"Controller connected: {controller.get_name()}")




# Legacy code when I was still comparing raw integers, simply add the number corresponding to the ID (Config > InputMapping) to make it an accepted input
def filter_events(gamepad_command):
    """This function is called after reading the gamepad events. Unused commands are discarded before they are placed in Async queue.
    The purpose of the filter is to stop the queue from being filled with data thats not used at all.
    Safe to delete or change for your purposes.
    See the description of read_gamepad() for the ID mappings"""
    match gamepad_command[0]:
        case 0:
            match gamepad_command[1]:
                case 1 | 3: # List of axis inputs that are accepted
                    return True
                case _:
                    return False
        case 1:
                match gamepad_command[1]:
                    case 0 | 1 | 2 | 3 | 4 | 9 | 10 | 11 | 12: # List of button inputs that are accepted
                        return True
                    case _:
                        return False
        case _:
            return False



# Flag to pause read_gamepad during disconnect/reconnect
controller_active = True

async def reinit_controller():
    """
    Reinitialize the controller after reconnection.
    """
    global controller, controller_active
    
    controller_active = False  # Signal read_gamepad to pause
    await asyncio.sleep(0.05)  # Let read_gamepad finish current iteration
    
    try:
        pygame.joystick.quit()
        pygame.joystick.init()
        
        await asyncio.sleep(0.2)  # Give time for OS to enumerate device again
        
        if pygame.joystick.get_count() > 0:
            controller = pygame.joystick.Joystick(0)
            controller.init()
            controller_active = True  # Resume reading
            return True
    except Exception as e:
        print(f"Reinit exception: {e}")
    
    return False

async def read_gamepad(queue):
    """Read PS4 controller and puts data in asyncio queue.
    This is a generic function I built for the Jaska project.
    That means you can use it as-is. I do the parsing in other project code,
    so this function has no logic in itself.

    This function outputs data as a tuple with three elements:

    (Axis (0) or Button (1) or "Hat"(2), ID of event (0-15, separate for axis/button), value of event)

    Joystick values are scaled by 1000 and the sign flipped to reverse the y-axis. Easier to handle other axises being flipped. (Function by default returns value between -1 and 1).
    Deadzone value is small and is meant to prevent stick drift while the stick is in a neutral position.

    By default, only a state change of the button/axis triggers data to be read.
    If you need to poll the state of a button/joystick at any moment in time somewhere else, you can import the controller variable from this script
    And then for example, poll the status of an axis stick with controller.get_axis(id)

    The size of the command packet is 64 bytes.
    The data is polled from PyGame at 100 Hz.
    
    IDs for AXIS:
        0: "Left stick X",
        1: "Left stick Y", 
        2: "Right stick X",
        3: "Right stick Y",
        4: "L2 trigger",
        5: "R2 trigger"
    
    IDs for BUTTON:
        0: "X",
        1: "Circle", 
        2: "Square",
        3: "Triangle",
        4: "Share",
        5: "PS4",
        6: "Options",
        7: "L3", 
        8: "R3",
        9: "L1",
        10: "R1",
        11: "D-Pad Up",
        12: "D-Pad Down",
        13: "D-Pad Left",
        14: "D-Pad Right",
        15: "Touchpad"

    VALUE for BUTTON:
        0: "Released"
        1: "Pressed"

    """
    try:
        while True:
            try:
                events = pygame.event.get()
                for event in events:
                    controller_data = None
                    
                    if event.type == pygame.JOYAXISMOTION:
                        if abs(event.value) > DEAD_ZONE:
                            controller_data = (0, event.axis, int(event.value * -1000))  # Scale axis value and flip the sign, y-axis is positive downwards by default
                        else: # If we are not above the deadzone, just sent a 0
                            controller_data = (0, event.axis, 0)
                    elif event.type == pygame.JOYBUTTONDOWN:
                        controller_data = (1, event.button, 1)
                    elif event.type == pygame.JOYBUTTONUP:
                        controller_data = (1, event.button, 0)
                    elif event.type == pygame.JOYHATMOTION:
                        #controller_data = (2, event.hat, event.value) #windows, not used though, legacy
                        controller_data = (1, 0, event.value) #linux

                    if controller_data:
                        # if filter_events(controller_data):
                        await queue.put(controller_data)
            except (pygame.error, SystemError) as e:
                # Controller disconnected during read - just wait
                print(f"Read error (expected during disconnect): {e}")
                await asyncio.sleep(0.1)
                continue
                    
            await asyncio.sleep(0.01)  # 100Hz
            
    except KeyboardInterrupt:
        print("EXITING NOW")
        controller.quit()


if __name__ == "__main__":
    pass