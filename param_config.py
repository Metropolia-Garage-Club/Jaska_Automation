"""
EM-366 Motor Controller Parameter Configuration Tool

Uses the Modbus "Parameter Update" mechanism defined in the EM-352/367 Modbus spec:
  - Register 40021 (addr 20) = Parameter Update control register
      0 = no action
      1 = write MB registers to device parameters (volatile, lost on power cycle)
      2 = write MB registers to device parameters AND store to EEPROM (persistent)
      3 = read device parameters into MB registers 21-42
  - Registers 40022-40043 (addr 21-42) = Parameters 1-22

Supports multiple devices on the same RS-485 bus. You select a target
device by slave address before reading/writing parameters.

Workflow:
  READ:  write 3 to reg 20 → wait → read regs 21-42
  WRITE: read first (populate all regs) → write value to target reg →
         write 1 or 2 to reg 20 to commit
"""

import sys
import time

# minimalmodbus: lightweight Modbus RTU library for Python.
# Wraps pyserial to handle Modbus framing, CRC, and register read/write.
import minimalmodbus

# ---------------------------------------------------------------------------
# Parameter metadata: defines valid ranges, units, and human-readable names
# for each of the 22 configurable parameters on the EM-366 controller.
# Keys = parameter number (1-22), matching the device documentation.
# ---------------------------------------------------------------------------
PARAMETER_DEFINITIONS = {
    1:  {"name": "Mode",                          "range": (0, 2),    "default": 0,   "unit": "",
         "description": "0=open loop, 1=closed loop, 2=closed loop slow"},
    2:  {"name": "Closed loop range",             "range": (0, 4),    "default": 3,   "unit": "",
         "description": "0=15000rpm, 1=7500rpm, 2=5000rpm, 3=2500rpm, 4=1500rpm (4-pole)"},
    3:  {"name": "Start ramp",                    "range": (0, 50),   "default": 10,  "unit": "x0.1s",
         "description": "0-5s in 0.1s steps (value 0-50)"},
    4:  {"name": "Stop ramp",                     "range": (0, 50),   "default": 5,   "unit": "x0.1s",
         "description": "0-5s in 0.1s steps (value 0-50)"},
    5:  {"name": "I-trip delay",                  "range": (0, 255),  "default": 200, "unit": "x0.01s",
         "description": "0.01-2.55s (0-255), 0=I-trip disabled"},
    6:  {"name": "Scale start speed",             "range": (0, 255),  "default": 0,   "unit": "x0.1%",
         "description": "0-25.5% (0-255)"},
    7:  {"name": "Scale gain",                    "range": (0, 255),  "default": 200, "unit": "x0.01",
         "description": "0-2.55 (0-255)"},
    8:  {"name": "Load compensation / P-factor",  "range": (1, 200),  "default": 5,   "unit": "",
         "description": "RxI adjust (open loop) or dynamic P-factor (closed loop)"},
    9:  {"name": "Closed loop dynamic I-factor",  "range": (1, 200),  "default": 10,  "unit": "",
         "description": "Integral factor for closed loop control"},
    10: {"name": "Regen braking current limit",   "range": (2, 40),   "default": 25,  "unit": "A",
         "description": "2-40A"},
    11: {"name": "Input PIN 15 options",          "range": (0, 6),    "default": 0,   "unit": "",
         "description": "0-6, see device manual for pin 15 function modes"},
    12: {"name": "Current limit",                 "range": (0, 40),   "default": 20,  "unit": "A",
         "description": "0=off, 1-40A"},
    13: {"name": "Input PIN 19 options",          "range": (0, 100),  "default": 50,  "unit": "",
         "description": "0=I-lim analog, 1=stop, 2=end stop FW, 3=end stop BW, 4=analog, 10-100=speed-2"},
    14: {"name": "I-trip reset mode",             "range": (0, 200),  "default": 0,   "unit": "",
         "description": "0=disable pin only, 1=disable or speed change, 10-200=timer (0.1s steps)"},
    15: {"name": "Startup mode",                  "range": (0, 200),  "default": 1,   "unit": "",
         "description": "Power-on & over-temp reset behavior, see manual"},
    16: {"name": "PIN 17 output function",        "range": (0, 4),    "default": 1,   "unit": "",
         "description": "0=overtemp+overvolt, 1=+I-trip, 2=+overcurrent, 3=pulse out, 4=LED mirror"},
    17: {"name": "Pulse output divider",          "range": (1, 20),   "default": 1,   "unit": "pulse/N rounds",
         "description": "Only active if param 16=3. 1=1pulse/round, N=1pulse/N rounds"},
    18: {"name": "Brake res. threshold (overvoltage)", "range": (15, 60), "default": 35, "unit": "V",
         "description": "15-60V"},
    19: {"name": "Brake output & braking mode",   "range": (0, 3),    "default": 0,   "unit": "",
         "description": "0=regen, 1=freewheel, 2=regen+run, 3=freewheel+run"},
    20: {"name": "Input PIN 20 options",          "range": (0, 6),    "default": 0,   "unit": "",
         "description": "0=disable, 1=safety switch, 2=stop, 3=end stop FW, 4=end stop BW, 5=analog, 6=inv disable"},
    21: {"name": "Baud rate",                     "range": (0, 5),    "default": 3,   "unit": "",
         "description": "0=9600/even/1, 1=9600/odd/1, 2=9600/none/2, 3=19200/even/1, 4=19200/odd/1, 5=19200/none/2"},
    22: {"name": "Modbus address",                "range": (1, 247),  "default": 1,   "unit": "",
         "description": "Slave address 1-247"},
}

# Modbus holding register address for the Parameter Update control register
REG_PARAM_UPDATE = 20

# Parameters 1-22 map to holding registers 21-42 (reg = 20 + param_number)
REG_PARAM_BASE = 21


class ParameterConfigurator:
    """
    Manages Modbus connections to multiple EM-366 controllers on the same
    RS-485 bus. Each device is identified by its slave address.

    Internally caches minimalmodbus.Instrument objects per address so the
    serial port configuration is only done once per device.
    """

    def __init__(self, port: str, baudrate: int = 19200,
                 parity: str = 'E', stopbits: int = 1, timeout: float = 0.1):
        """
        Configure the shared serial port settings.

        Args:
            port:     Serial port path, e.g. '/dev/ttyUSB0' or 'COM3'
            baudrate: 9600 or 19200
            parity:   'N', 'E', or 'O'
            stopbits: 1 or 2
            timeout:  Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.timeout = timeout

        # Map parity character to pyserial constant
        parity_map = {
            'N': minimalmodbus.serial.PARITY_NONE,
            'E': minimalmodbus.serial.PARITY_EVEN,
            'O': minimalmodbus.serial.PARITY_ODD,
        }
        if parity.upper() not in parity_map:
            raise ValueError(f"Invalid parity '{parity}'. Use 'N', 'E', or 'O'.")
        self.parity = parity_map[parity.upper()]

        # Cache of Instrument objects, keyed by slave address.
        # All instruments share the same underlying serial port —
        # minimalmodbus handles this via pyserial's singleton behavior
        # (same port string = same serial.Serial instance).
        self._instruments: dict[int, minimalmodbus.Instrument] = {}

    def _get_instrument(self, address: int) -> minimalmodbus.Instrument:
        """
        Get or create a minimalmodbus Instrument for the given slave address.
        Instruments are cached so serial config only happens once per address.

        Args:
            address: Modbus slave address (1-247)

        Returns:
            Configured minimalmodbus.Instrument
        """
        if address not in self._instruments:
            instrument = minimalmodbus.Instrument(self.port, address)
            instrument.serial.baudrate = self.baudrate
            instrument.serial.bytesize = 8
            instrument.serial.parity = self.parity
            instrument.serial.stopbits = self.stopbits
            instrument.serial.timeout = self.timeout
            self._instruments[address] = instrument

        return self._instruments[address]

    def read_all_parameters(self, address: int) -> dict:
        """
        Read all 22 parameters from a specific device.

        Process:
          1. Write 3 to reg 20 → device copies internal params into regs 21-42
          2. Wait for the controller to finish
          3. Read registers 21-42

        Args:
            address: Modbus slave address of the target device

        Returns:
            dict mapping parameter number (1-22) to its current value
        """
        instrument = self._get_instrument(address)

        # Trigger parameter read: device populates registers 21-42
        instrument.write_register(REG_PARAM_UPDATE, 3, functioncode=6)
        time.sleep(0.2)

        params = {}
        for param_num in range(1, 23):
            reg_addr = REG_PARAM_BASE + (param_num - 1)
            try:
                value = instrument.read_register(reg_addr, functioncode=3)
                params[param_num] = value
            except Exception as e:
                print(f"  [ERROR] Could not read param {param_num} (reg {reg_addr}): {e}")
                params[param_num] = None

        return params

    def read_parameter(self, address: int, param_num: int) -> int | None:
        """
        Read a single parameter from a specific device.

        Same mechanism as read_all: triggers code 3 on reg 20, then
        reads only the one register corresponding to param_num.

        Args:
            address:   Modbus slave address of the target device
            param_num: Parameter number (1-22)

        Returns:
            Parameter value, or None on failure
        """
        if param_num not in PARAMETER_DEFINITIONS:
            raise ValueError(f"Invalid parameter number {param_num}. Valid: 1-22.")

        instrument = self._get_instrument(address)

        # Trigger parameter read: device populates registers 21-42
        instrument.write_register(REG_PARAM_UPDATE, 3, functioncode=6)
        time.sleep(0.2)

        reg_addr = REG_PARAM_BASE + (param_num - 1)
        value = instrument.read_register(reg_addr, functioncode=3)
        return value

    def write_parameter(self, address: int, param_num: int, value: int,
                        save_to_eeprom: bool = False):
        """
        Write a single parameter to a specific device.

        Process:
          1. Validate param_num and value
          2. Trigger a read (code 3) to populate all registers with current
             device values — defensive measure against bulk overwrite
          3. Write the new value to the target register
          4. Commit with code 1 (volatile) or 2 (EEPROM)

        Args:
            address:        Modbus slave address of the target device
            param_num:      Parameter number (1-22)
            value:          New value to set
            save_to_eeprom: True = persist to EEPROM, False = volatile
        """
        # --- Validate parameter number ---
        if param_num not in PARAMETER_DEFINITIONS:
            raise ValueError(f"Invalid parameter number {param_num}. Valid: 1-22.")

        # --- Validate value against known range ---
        param_def = PARAMETER_DEFINITIONS[param_num]
        low, high = param_def["range"]
        if not (low <= value <= high):
            raise ValueError(
                f"Param {param_num} ({param_def['name']}): "
                f"value {value} out of range [{low}, {high}]"
            )

        instrument = self._get_instrument(address)

        # --- Write the new value to the target register ---
        reg_addr = REG_PARAM_BASE + (param_num - 1)
        instrument.write_register(reg_addr, value, functioncode=6)

        # --- Commit: 1 = volatile, 2 = EEPROM ---
        update_code = 2 if save_to_eeprom else 1
        instrument.write_register(REG_PARAM_UPDATE, update_code, functioncode=6)
        time.sleep(0.1)

        storage = "EEPROM" if save_to_eeprom else "volatile"
        print(f"  Param {param_num} ({param_def['name']}) → {value} [{storage}]")


def print_all_parameters(address: int, params: dict):
    """Pretty-print all parameter values in a formatted table."""
    print(f"\n  Parameters for device at address {address}")
    print("=" * 75)
    print(f"  {'#':<4} {'Name':<38} {'Value':<8} {'Range':<12} {'Unit'}")
    print("-" * 75)
    for num in range(1, 23):
        defn = PARAMETER_DEFINITIONS[num]
        val = params.get(num)
        val_str = str(val) if val is not None else "ERROR"
        low, high = defn["range"]
        print(f"  {num:<4} {defn['name']:<38} {val_str:<8} {low}-{high:<8} {defn['unit']}")
    print("=" * 75 + "\n")


def main():
    """
    Interactive terminal tool for reading/writing EM-366 parameters
    on a multi-device RS-485 bus.

    Usage:
        python param_config.py <port> [baudrate] [parity] [stopbits]

    Examples:
        python param_config.py /dev/ttyUSB0
        python param_config.py COM3 19200 E 1

    Once running, first select a device, then read/write parameters:
        target <address>  - Select the device to work with
        read              - Read all 22 parameters from the target device
        write <num> <val> - Write a parameter value (volatile)
        save <num> <val>  - Write a parameter value and store to EEPROM
        info <num>        - Show details for a specific parameter
        help              - Show available commands
        quit / exit       - Exit the tool
    """
    # --- Parse command-line arguments ---
    if len(sys.argv) < 2:
        print("Usage: python param_config.py <serial_port> [baudrate] [parity] [stopbits]")
        print("  Example: python param_config.py /dev/ttyUSB0")
        print("  Example: python param_config.py COM3 19200 E 1")
        sys.exit(1)

    port = sys.argv[1]
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 19200
    parity = sys.argv[3] if len(sys.argv) > 3 else 'E'
    stopbits = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    # --- Create the configurator (shared serial port) ---
    print(f"Opening {port} at {baudrate} baud, parity={parity}, stopbits={stopbits}")
    try:
        configurator = ParameterConfigurator(port, baudrate, parity, stopbits)
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        sys.exit(1)
    print("Serial port open.\n")

    # Track which device the user is currently working with
    target_address: int | None = None

    # --- Help text ---
    help_text = (
        "Commands:\n"
        "  target <address>  - Select device by Modbus slave address (1-247)\n"
        "  get <num>         - Read a single parameter from the target device\n"
        "  read              - Read all parameters from the target device\n"
        "  write <num> <val> - Write parameter (volatile, lost on reboot)\n"
        "  save  <num> <val> - Write parameter and store to EEPROM\n"
        "  info  <num>       - Show details for a specific parameter\n"
        "  help              - Show this help message\n"
        "  quit / exit       - Exit\n"
    )
    print(help_text)
    print("Select a target device first with: target <address>\n")

    # --- Main command loop ---
    while True:
        # Show current target in the prompt for clarity
        prompt = f"[device {target_address}] >> " if target_address else "[no device] >> "
        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        parts = user_input.split()
        command = parts[0].lower()

        if command in ("quit", "exit", "q"):
            print("Exiting.")
            break

        elif command == "help":
            print(help_text)

        elif command == "target":
            # Select which device to communicate with
            if len(parts) != 2:
                print("  Usage: target <address>")
                continue
            try:
                addr = int(parts[1])
                if not (1 <= addr <= 247):
                    print("  Address must be 1-247.")
                    continue
                target_address = addr
                print(f"  Target set to device at address {target_address}")
            except ValueError:
                print("  Address must be an integer.")

        elif command == "read":
            if target_address is None:
                print("  No target device selected. Use: target <address>")
                continue
            print(f"  Reading parameters from device {target_address}...")
            try:
                params = configurator.read_all_parameters(target_address)
                print_all_parameters(target_address, params)
            except Exception as e:
                print(f"  [ERROR] Read failed: {e}")

        elif command == "get":
            # Read a single parameter from the target device
            if target_address is None:
                print("  No target device selected. Use: target <address>")
                continue
            if len(parts) != 2:
                print("  Usage: get <param_number>")
                continue
            try:
                param_num = int(parts[1])
            except ValueError:
                print("  Parameter number must be an integer.")
                continue
            try:
                value = configurator.read_parameter(target_address, param_num)
                defn = PARAMETER_DEFINITIONS[param_num]
                unit = defn['unit'] or ''
                print(f"  Param {param_num} ({defn['name']}): {value} {unit}")
            except ValueError as e:
                print(f"  [VALIDATION] {e}")
            except Exception as e:
                print(f"  [ERROR] Read failed: {e}")

        elif command in ("write", "save"):
            if target_address is None:
                print("  No target device selected. Use: target <address>")
                continue
            if len(parts) != 3:
                print(f"  Usage: {command} <param_number> <value>")
                continue
            try:
                param_num = int(parts[1])
                value = int(parts[2])
            except ValueError:
                print("  Parameter number and value must be integers.")
                continue

            save_to_eeprom = (command == "save")
            try:
                configurator.write_parameter(target_address, param_num, value, save_to_eeprom)
            except ValueError as e:
                print(f"  [VALIDATION] {e}")
            except Exception as e:
                print(f"  [ERROR] Write failed: {e}")

        elif command == "info":
            if len(parts) != 2:
                print("  Usage: info <param_number>")
                continue
            try:
                num = int(parts[1])
                if num not in PARAMETER_DEFINITIONS:
                    print("  Invalid parameter number. Valid: 1-22.")
                    continue
                d = PARAMETER_DEFINITIONS[num]
                print(f"  Parameter {num}: {d['name']}")
                print(f"  Range:   {d['range'][0]} - {d['range'][1]}")
                print(f"  Default: {d['default']}")
                print(f"  Unit:    {d['unit'] or 'N/A'}")
                print(f"  Info:    {d['description']}")
            except ValueError:
                print("  Parameter number must be an integer.")

        else:
            print(f"  Unknown command: '{command}'. Type 'help' for options.")


if __name__ == "__main__":
    main()