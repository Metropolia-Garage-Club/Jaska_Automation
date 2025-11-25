from .Config import config
from .ModbusDriver import modbus

# This script is responsible for the motor control logic. The functions handle the driving logic on the controller level, keeping track of direction (DIR register)
class MotorDriver:
    def __init__(self):
        self.FORWARD = 0
        self.REVERSE = 1
        
        # Track current direction for each side
        self.current_left_dir = self.FORWARD
        self.current_right_dir = self.FORWARD 
        # These are to keep track of the state of the direction of the motor controllers without having to read from the register its true state
        # There may be an edge case where the value is not correctly written which will mean these variables will be out of sync with the motor controllers
        # TODO: Implement a resync function in case they fall out of sync

        self.get_direction = lambda value: self.REVERSE if value < 0 else self.FORWARD

        self.stop_state = False

        self.speed_toggle_state = False

    def _set_left_direction(self, desired_dir):
        """Tracks the left side direction state variables and sets them on the corresponding motor controllers. Don't call from outside the class."""
        if self.current_left_dir != desired_dir:
            for address in config.left_motor_addresses:
                modbus.set_direction(address, desired_dir)
            self.current_left_dir = desired_dir
    
    def _set_right_direction(self, desired_dir):
        """Tracks the right side direction state variables and sets them on the corresponding motor controllers. Don't call from outside the class."""
        if self.current_right_dir != desired_dir:
            for address in config.right_motor_addresses:
                modbus.set_direction(address, desired_dir)
            self.current_right_dir = desired_dir
    
    def drive_all(self, value):
        """Drive all motors with a broadcast command"""
        modbus.set_speed(address=0, speed=abs(value))

    def drive_left(self,value):
        """Drive left motors with automatic direction handling"""
        if -20 < value < 20: # Re-account for DEADZONE for speed purposes even though stick drift is already accounted for
            # Just set speed to 0, don't change direction
            for address in config.left_motor_addresses:
                modbus.set_speed(address, 0)
            return
        
        self._set_left_direction(self.get_direction(value))

        for address in config.left_motor_addresses:
            modbus.set_speed(address, abs(value)) # Make sure to always pass the absolute value to the motor controllers

    def drive_right(self, value): 
        """Drive right motors with automatic direction handling"""
        if -20 < value < 20:
            for address in config.right_motor_addresses:
                modbus.set_speed(address, 0)
            return
        
        self._set_right_direction(self.get_direction(value))

        for address in config.right_motor_addresses:
            modbus.set_speed(address, abs(value))

    #TODO Implement timer to prevent re-enabling before 2-3 seconds have passed so that the capacitors have time to dissipate energy
    def toggle_motor_stop(self):
            modbus.set_disable(0, self.stop_state)
            modbus.set_speed(0, 0)
            self.stop_state = not self.stop_state

    def toggle_slow_forward(self):
        modbus.set_direction(0, 0)
        if not self.speed_toggle_state:
            modbus.set_speed(0, config.fixed_speed)
            self.speed_toggle_state = not self.speed_toggle_state
        else:
            modbus.set_speed(0, 0)
            self.speed_toggle_state = not self.speed_toggle_state

    def toggle_slow_backward(self):
        modbus.set_direction(0, 1)
        if not self.speed_toggle_state:
            modbus.set_speed(0, config.fixed_speed)
            self.speed_toggle_state = not self.speed_toggle_state
        else:
            modbus.set_speed(0, 0)
            self.speed_toggle_state = not self.speed_toggle_state

    #TODO Implement reading from registers in a way it doesnt block everything. Do not use the ChatGPT functions as they are, because they WILL congest the modbus line.
    def read_direction(self, value):
        pass
    def read_motor_state(self, value):
        pass
    def read_all_motor_states(self, value):
        pass


driver = MotorDriver()