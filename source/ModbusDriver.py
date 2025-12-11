import minimalmodbus
import time
from .Config import config

# This script is responsible for creating the MinimalModbus instruments and handling the data transfer between the computer and the motor controllers
# WARNING: Heavily AI made, needs some refactoring

class ModbusFunctions:
    """
    Class to control multiple EM-366 motor controllers via Modbus RTU
    """
    # Holding Register addresses (40001-based addressing, subtract 1 for 0-based)
    REG_BUS_ENABLE = 0      # 40001 - 0 = Local, 1 = Bus enable
    REG_SPEED = 1           # 40002 - Speed (0-1000)
    REG_DISABLE = 2         # 40003 - Disable (0-1)
    REG_DIR = 3             # 40004 - Direction (0-1)
    
    # Input Register addresses (30001-based addressing, subtract 1 for 0-based)
    REG_CURRENT = 1         # 30002 - Motor Current (1 A/digit)
    REG_BRAKE_CURRENT = 2   # 30003 - Braking current (1 A/digit)
    REG_VOLTAGE = 3         # 30004 - Supply voltage (0.1 V/digit)
    REG_FREQ = 4            # 30005 - Motor pulse frequency (0-255 Hz)
    REG_IO_STOP13 = 5          # 30006 - I/O State
    REG_IO_DIR = 6           # 30007 - I/O State direction
    REG_IO_SPEED = 7        # 30008 - I/O State speed
    REG_IO_ILM = 8          # 30009 - I/O State
    REG_IO_DISABLE = 9      # 30010 - IO State
    REG_PWM = 10            # 30011 - Motor driving PWM (0-255, 255=100%)
    REG_SPEED2ENABLED = 11  # 30012 - Speed 2 enabled
    REG_FAULT = 12          # 30013 - Fault indicated
    REG_FAIL_CURRENT = 13   # 30014 - Fail from current
    REG_FAIL_TEMP = 14      # 30015 - Fail from temperature
    REG_FAIL_SUPPLY = 15    # 30016 - Fail from supply
    REG_FAIL_OVERVOLTAGE = 16 # 30017 - Fail from overvoltage
    REG_FAIL_SAFETY = 17    # 30018 - Fail from safety line
    REG_FAIL_SAFETY_WIRE = 18 # 30019 - Fail from safetywire monitor


    def __init__(self, port: str=config.USB_Serial_Device, baudrate: int=19200, parity: str='E', 
                 stopbits: int=1, timeout: float=0.05, addresses: tuple=config.motor_addresses):
        """
        Initialize the modbus instrument
        
        Args:
            port: Serial port (e.g., '/dev/ttyUSB0' (LINUX) or 'COM3' (WINDOWS))
            baudrate: Communication speed (9600 or 19200, default=19200)
            parity: 'N'=none, 'E'=even, 'O'=odd (default='E')
            stopbits: 1 or 2 (default=1)
            timeout: Communication timeout in seconds
            motor_addresses: List of motor addresses to manage (e.g., [1, 2, 3, 4, 5, 6])
        """
        self.port = port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.motors = {}
        
        # If motor addresses provided, initialize them

        #Create a broadcast instrument (Hacky AF)
        self.add_motor(0)
        
        if addresses:
            for address in addresses:
                self.add_motor(address)
    
    def add_motor(self, address):
        """
        Add a motor controller to the manager
        
        Args:
            address: Modbus slave address (1-247)
        """
        
        try:
            instrument = minimalmodbus.Instrument(self.port, address)
            
            if instrument.serial is None:
                raise ValueError(f"Serial port {self.port} not found")
            
            # Configure serial parameters
            instrument.serial.baudrate = self.baudrate
            instrument.serial.bytesize = 8
            
            # Set parity
            match self.parity:
                case 'N'|'n':
                    instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
                case 'E'|'e':
                    instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
                case 'O'|'o':
                    instrument.serial.parity = minimalmodbus.serial.PARITY_ODD
                case _:
                    raise ValueError(f"Invalid parity bit setting!")
            
            instrument.serial.stopbits = self.stopbits
            instrument.serial.timeout = self.timeout
            
            # Store the instrument
            self.motors[address] = instrument
            
            print(f"Motor at address {address} added successfully")
            
        except Exception as e:
            print(f"Error adding motor at address {address}: {e}")
    
    def remove_motor(self, address: int=None):
        """Remove a motor from the controller"""
        if address in self.motors:
            del self.motors[address]
            print(f"Motor at address {address} removed")
        else:
            print(f"Motor at address {address} not found")
    
    def get_motor(self, address: int=None):
        """Get the instrument for a specific motor"""
        if address not in self.motors:
            raise ValueError(f"Motor at address {address} not found. Available addresses: {list(self.motors.keys())}")
        return self.motors[address]
    
    def validate_modbus_address(func):
        """Decorator to validate modbus address is not broadcast (0)"""
        def wrapper(*args, **kwargs):
            # Handle both positional and keyword arguments for 'address'
            address = None
            if args:
                # Assume first argument is address (adjust index if needed)
                address = args[0]
            elif 'address' in kwargs:
                address = kwargs['address']
            
            if address == 0:
                raise AssertionError("Do not read MODBUS lines using broadcast")
            
            return func(*args, **kwargs)
        return wrapper


    # Write functions
    ###############################
    def set_speed(self, address: int=0, speed: int=0):
        """Set motor speed for a specific motor, use address 0 for all motors"""
        if not 0 <= speed <= 1000:
            raise ValueError("Speed must be between 0 and 1000")
        
        try:
            motor = self.get_motor(address)
            motor.write_register(self.REG_SPEED, int(speed), functioncode=6)
            print(f"Motor {address}: Speed set to {speed}")
        except Exception as e:
            print(f"Error setting speed for motor {address}: {e}")
    
    def set_direction(self, address: int=0, direction: int=0):
        """Set motor direction for a specific motor, use address 0 for all motors"""
        if direction not in [0, 1]:
            raise ValueError("Direction must be 0 or 1")
        
        try:
            motor = self.get_motor(address)
            motor.write_register(self.REG_DIR, direction, functioncode=6)
            print(f"Motor {address}: Direction set to {direction}")
        except Exception as e:
            print(f"Error setting direction for motor {address}: {e}")
    
    def set_disable(self, address: int=0, disable: int=0):
        """Enable or disable a specific motor, use address 0 for all motors"""
        if disable not in [0, 1]:
            raise ValueError("Disable must be 0 or 1")
        try: 
            motor = self.get_motor(address)
            motor.write_register(self.REG_DISABLE, disable, functioncode=6)
            status = "disabled" if disable else "enabled"
            print(f"Motor {address}: {status}")
        except Exception as e:
            print(f"Error setting disable for motor {address}: {e}")
    
    # Read functions
    ###############################
    # Validation is there to prevent you from accidentally trying to read using broadcast
    @validate_modbus_address
    def read_direction(self, address):
        """Read the direction from the register of the motor controller"""
        try:
            motor = self.get_motor(address)
            value = motor.read_register(self.REG_IO_DIR, functioncode=4) # EI toimi antaa vaan arvoa 0 oli suunta mikä tahansa
            return value  # 0 Forward 1 backward
        except Exception as e:
            print(f"Error reading direction from motor {address}: {e}")
            return None


    @validate_modbus_address
    def read_current(self, address):
        """Read motor current from a specific motor"""
        try:
            motor = self.get_motor(address)
            value = motor.read_register(self.REG_CURRENT, functioncode=4)
            # Modubus does not give real measured value. 
            # tried to make some kind of scaling acording to real measured values. 
            a = 0.0016794224417253174
            b = 1.632749473028088
            I = a * (value ** b)
            if I < 0:
                I = 0.0
            return round(I, 2)
            #return value  # Already in Amperes (1 A/digit) added "/10" By TNuppi 25.11.25
        except Exception as e:
            print(f"Error reading current from motor {address}: {e}")
            return None
        
    @validate_modbus_address
    def read_brake_current(self, address):
        """Read regenerative braking current from a specific motor"""
        try:
            motor = self.get_motor(address)
            value = motor.read_register(self.REG_BRAKE_CURRENT, functioncode=4)
            #return value  # Already in Amperes (1 A/digit)
            return value/10 # changed by TNuppi 11.12.2025
        except Exception as e:
            print(f"Error reading brake current from motor {address}: {e}")
            return None
        
    @validate_modbus_address
    def read_voltage(self, address):
        """Read supply voltage from a specific motor"""
        try:
            motor = self.get_motor(address)
            value = motor.read_register(self.REG_VOLTAGE, functioncode=4)
            #return 0.1/value  # orginal Convert to Volts (0.1 V/digit)
            return value/10 # Added and tested that it shows real value by TNuppi 25.11.25
        except Exception as e:
            print(f"Error reading voltage from motor {address}: {e}")
            return None
        
    @validate_modbus_address
    def read_frequency(self, address):
        """Read Hall sensor pulse frequency from a specific motor"""
        try:
            motor = self.get_motor(address)
            value = motor.read_register(self.REG_FREQ, functioncode=4)
            return value  # Already in Hz
        except Exception as e:
            print(f"Error reading frequency from motor {address}: {e}")
            return None
        
    @validate_modbus_address
    def read_pwm(self, address):
        """Read motor driving PWM from a specific motor"""
        try:
            motor = self.get_motor(address)
            value = motor.read_register(self.REG_PWM, functioncode=4)
            return value  # 0-255 (255 = 100%)
        except Exception as e:
            print(f"Error reading PWM from motor {address}: {e}")
            return None
        
    @validate_modbus_address
    def read_status(self, address):
        """Read all status values from a specific motor"""
    
        status = {
            'address': address,
            'current_A': self.read_current(address),
            'brake_current_A': self.read_brake_current(address),
            'voltage_V': self.read_voltage(address),
            'frequency_Hz': self.read_frequency(address),
            'pwm': self.read_pwm(address),
            'dir':self.read_direction(address)
        }
        return status
    
    def emergency_stop(self):
        """Emergency stop - disable motor(s) and set speed to 0"""
        self.set_disable(0, 1)
        self.set_speed(0, 0)
        print("Emergency stop executed for all motors")

modbus = ModbusFunctions()

# def main():
#     """Example usage of the MotorControllerManager class"""
    
#     # Initialize motor controller manager with 6 motors
#     manager = ModbusFunctions(
#         baudrate=19200,
#         parity='E',
#         stopbits=1,
#         motor_addresses=[1, 2, 3, 4, 5, 6]  # Your 6 motor addresses
#     )
    
#     try:
#         # Example 1: Control individual motors
#         print("\n--- Individual Motor Control ---")
#         manager.set_disable(1, 0)  # Enable motor 1
#         manager.set_direction(1, 0)  # Set motor 1 direction
#         manager.set_speed(1, 500)  # Set motor 1 speed
        
#         time.sleep(2)
        
#         # Read status from motor 1
#         status = manager.read_status(1)
#         print(f"\nMotor 1 Status:")
#         print(f"Current: {status['current_A']} A")
#         print(f"Voltage: {status['voltage_V']} V")
#         print(f"PWM: {status['pwm_percentage']:.1f}%")
        
#         # Example 2: Control multiple motors differently
#         print("\n--- Multiple Motor Control ---")
#         manager.enable_all_motors()  # Enable all motors
        
#         # Set different speeds for each motor
#         for i, address in enumerate([1, 2, 3, 4, 5, 6]):
#             speed = (i + 1) * 150  # 150, 300, 450, 600, 750, 900
#             manager.set_speed(address, speed)
        
#         time.sleep(2)
        
#         # Read all motors status
#         all_status = manager.read_all_motors_status()
#         print("\nAll Motors Status:")
#         for address, status in all_status.items():
#             print(f"Motor {address}: {status['frequency_Hz']} Hz, "
#                   f"{status['current_A']} A, {status['pwm_percentage']:.1f}% PWM")
        
#         # Example 3: Synchronized control
#         print("\n--- Synchronized Control ---")
#         manager.set_all_directions(0)  # All motors forward
#         manager.set_all_speeds(500)     # All motors same speed
        
#         time.sleep(3)
        
#         # Example 4: Sequential motor control
#         print("\n--- Sequential Motor Control ---")
#         for address in [1, 2, 3, 4, 5, 6]:
#             manager.set_speed(address, 1000)
#             print(f"Motor {address} at full speed")
#             time.sleep(1)
#             manager.set_speed(address, 0)
        
#         # Stop all motors
#         manager.stop_all_motors()
#         print("\nAll motors stopped")
        
#     except KeyboardInterrupt:
#         print("\nInterrupted by user")
#         manager.emergency_stop()  # Stop all motors
    
#     except Exception as e:
#         print(f"\nError occurred: {e}")
#         manager.emergency_stop()  # Stop all motors
    
#     finally:
#         # Optionally return all motors to local control
#         # for address in manager.motors:
#         #     manager.disable_bus_control(address)
#         pass


# # Alternative usage pattern for more dynamic control
# def dynamic_example():
#     """Example of dynamic motor management"""
    
#     # Start with empty manager
#     manager = ModbusFunctions(port='/dev/ttyUSB0')
    
#     # Add motors as needed
#     manager.add_motor(1)
#     manager.add_motor(2)
    
#     # Control them
#     manager.set_speed(1, 500)
#     manager.set_speed(2, 700)
    
#     # Add more motors later
#     manager.add_motor(3)
#     manager.set_speed(3, 300)
    
#     # Read specific motor
#     current = manager.read_current(2)
#     print(f"Motor 2 current: {current} A")
    
#     # Remove a motor if needed
#     manager.remove_motor(1)


# if __name__ == '__main__':
#     main()
#     # dynamic_example()  # Uncomment to run the dynamic example