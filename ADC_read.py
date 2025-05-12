import time
from smbus2 import SMBus

I2C_BUS = 1
ADS1115_ADDRESS = 0x48

# Register addresses
ADS1115_POINTER_CONVERSION = 0x00
ADS1115_POINTER_CONFIG     = 0x01

# Config register values (single-shot, AIN0, gain=4.096V, 128SPS)
CONFIG_OS_SINGLE     = 0x8000
CONFIG_MUX_AIN0      = 0x4000  # AIN0 vs GND
CONFIG_GAIN_4_096V   = 0x0200
CONFIG_MODE_SINGLE   = 0x0100
CONFIG_DR_128SPS     = 0x0080
CONFIG_COMP_QUE_DISABLE = 0x0003

# Full config: single-shot read on AIN0
CONFIG_REG = (CONFIG_OS_SINGLE |
              CONFIG_MUX_AIN0 |
              CONFIG_GAIN_4_096V |
              CONFIG_MODE_SINGLE |
              CONFIG_DR_128SPS |
              CONFIG_COMP_QUE_DISABLE)

def read_voltage(bus):
    # Write config to start single conversion
    config_bytes = [(CONFIG_REG >> 8) & 0xFF, CONFIG_REG & 0xFF]
    bus.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONFIG, config_bytes)

    # Wait for conversion (about 8ms for 128SPS)
    time.sleep(0.01)

    # Read conversion result (2 bytes)
    data = bus.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONVERSION, 2)
    raw_adc = (data[0] << 8) | data[1]

    # Handle negative values for signed 16-bit result
    if raw_adc > 0x7FFF:
        raw_adc -= 0x10000

    # Calculate voltage (4.096V reference, 16-bit ADC)
    voltage = raw_adc * (4.096 / 32768.0)
    return voltage

with SMBus(I2C_BUS) as bus:
    print("Reading ADS1115 AIN0:")
    try:
        while True:
            voltage = read_voltage(bus)
            print(f"Voltage: {voltage:.4f} V")
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nExiting...")
