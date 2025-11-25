import platform
import serial.tools.list_ports
import glob


# This is the configuration file
# It has various things in a single class, including indexes like slave addresses of motors you want to use and paths
# Every other script pulls necessary configurations from here

# If you need to make changes such as the addresses of the motors or the device path for serial communication, do it here

class Configurations:
    def __init__(self):

        self.system: str = platform.system()

        self.USB_Serial_Device: str = self.get_device_path() # If the function doesn't work, you can specify the correct device address as a string eg. "COM3" for Windows or "dev/ttyUSB0" for Linux

        # Change these if you need to, you can use a single element tuple as an iterable like this: tuple = (element, )
        self.right_motor_addresses: tuple = (4,6)
        self.left_motor_addresses: tuple = (1,3)

        self.motor_addresses = self.right_motor_addresses + self.left_motor_addresses

        # Change this to set the fixed speed driving functionality
        self.fixed_speed: int = 200

        # Change this to set the amount of change from the controller joystick that needs to happen from the previous read value for it to be processed
        # The program reads and writes data far faster than human can move the controller joystick, causing lots of unnecessary writes in the dataline
        # Treshold = 20 -> 2 % of total range
        self.speed_change_treshold: int = 20

    # Warning, this hasn't been checked to work universally or without bugs
    # If theres a problem, just manually input the device path where you get the error
    def get_device_path(self):
        """
        Get USB serial device path automatically.
        
        Returns:
            str: Device path (COM3, /dev/ttyUSB0, etc.) or None if not founds
        """
        if self.system == "Windows":
            # Look for "USB Serial Port" devices
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if "USB Serial Port" in str(port.description):
                    return port.device  # Returns "COM3", "COM4", etc.
            return None
        
        elif self.system == "Linux":
            # Look for ttyUSB devices (most common for USB serial)
            usb_devices = glob.glob('/dev/ttyUSB*')
            if usb_devices:
                return usb_devices[0]  # Return first one found (usually ttyUSB0)
            
            # Fallback to ttyACM devices (some Arduino boards)
            acm_devices = glob.glob('/dev/ttyACM*')
            if acm_devices:
                return acm_devices[0]
            
            return None
        
        elif self.system == "Darwin":  # macOS
            # Look for USB serial devices
            usb_devices = glob.glob('/dev/tty.usbserial*')
            if usb_devices:
                return usb_devices[0]
            
            # Fallback to USB modem devices
            modem_devices = glob.glob('/dev/tty.usbmodem*')
            if modem_devices:
                return modem_devices[0]
            
            return None
        
        return None

class InputMapping(): 
# The class dictionary can be used to invoke the corresponding value using the key (Name of the button) without having to remember which number represents what. 
# These are fixed in place by PyGame.
# These specific mappings are for PS4 controller. If you want to use another controller, check https://www.pygame.org/docs/ref/joystick.html
    def __init__(self):

        self.CONTROLLER_TYPE = {
            "Axis": 0,
            "Button": 1,
            "Hat": 2 # Not used
        }

        self.BUTTON_STATE = {
            "Unpressed": 0,
            "Pressed": 1
        }

        if config.system == "Linux":
            self.BUTTON_ID = {
            "Cross": 1,
            "Circle": 2,
            "Square": 0,
            "Triangle": 3,
            "Share": 8,
            "PS4": 12,
            "Options": 9,
            "L3": 10,
            "R3": 11,
            "L1": 4,
            "R1": 5,
            "D-Pad Up": 0 ,
            "D-Pad Down": 0,
            "D-Pad Left": 0,
            "D-Pad Right": 0,
            "Touchpad": 13
        }

        self.AXIS_ID = {
            "Left Stick X": 0,
            "Left Stick Y": 1,
            "Right Stick X": 2,
            "Right Stick Y": 5,
            "L2 Trigger": 3,
            "R2 Trigger": 4
        }
        if config.system == "Windows":
            self.BUTTON_ID = {
                "Cross": 0,
                "Circle": 1,
                "Square": 2,
                "Triangle": 3,
                "Share": 4,
                "PS4": 5,
                "Options": 6,
                "L3": 7,
                "R3": 8,
                "L1": 9,
                "R1": 10,
                "D-Pad Up": 11,
                "D-Pad Down": 12,
                "D-Pad Left": 13,
                "D-Pad Right": 14,
                "Touchpad": 15
            }

            self.AXIS_ID = {
                "Left Stick X": 0,
                "Left Stick Y": 1,
                "Right Stick X": 2,
                "Right Stick Y": 3,
                "L2 Trigger": 4,
                "R2 Trigger": 5
            }



# The class objects are automatically built and shared among the various scripts

config = Configurations()
mapping = InputMapping()
# You can use it like this 
# x_button = mapping.BUTTON_ID["Cross"]  # Returns 0
# button_type = mapping.CONTROLLER_TYPES["Button"]  # Returns 1
# left_stick_x = mapping.AXIS_ID["Left stick X"]  # Returns 0