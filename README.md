## How to drive:

Ensure that your computer has bluetooth ***classic*** (bredr) capability. The code has been written for PS4 controller. Connect your controller to the computer.

#### Emergency stop (Motor disable)

To disable the motors immediately, press the circle (O) button. **DO NOT** toggle the motors back on before ~3 seconds have passed, to let the energy dissipate from them. Otherwise, the energy will cause the motors move again with a large impulse.



#### Toggle driving (Fixed speed - mode)

The D-pad up & down buttons can be used to move at a fixed speed (default = 1/5th of max speed) forwards or backwards. This can be used to have more accurate control which can help to move safely in tight spaces. The speed value can be configured in Source > Config. 

#### Manual driving (Stick steering)

R1 is set as a "Dead man's switch". To drive, you need to hold it down. By default, the MODBUS program writes a 0 to the speed register if R1 is let go of and then stops sending anymore commands in until the button is held down again.

You can use the left and right sticks to accelerate/decelerate the left and right wheel pairs, respectively. The speed value is mapped to fit the 0 - 1000 value for the motor controllers. The program handles direction change logic, which has to be written into a separate DIR register on the motor boards (0 - 1 value).


### About turning

This code was written with tank steering in mind. To turn while standing in place, pull one stick towards and push the other away to spin the left and right side in opposite directions. To turn while moving, steer so that the side you want to turn towards is moving slower than the other side.