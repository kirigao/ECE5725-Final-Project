import time
from smbus2 import SMBus
import RPi.GPIO as GPIO

# --- ADS1115 Setup ---
I2C_BUS = 1
ADS1115_ADDRESS = 0x48

ADS1115_POINTER_CONVERSION = 0x00
ADS1115_POINTER_CONFIG     = 0x01

CONFIG_OS_SINGLE     = 0x8000
CONFIG_MUX_AIN0      = 0x4000
CONFIG_GAIN_4_096V   = 0x0200
CONFIG_MODE_SINGLE   = 0x0100
CONFIG_DR_128SPS     = 0x0080
CONFIG_COMP_QUE_DISABLE = 0x0003

CONFIG_REG = (CONFIG_OS_SINGLE |
              CONFIG_MUX_AIN0 |
              CONFIG_GAIN_4_096V |
              CONFIG_MODE_SINGLE |
              CONFIG_DR_128SPS |
              CONFIG_COMP_QUE_DISABLE)

def read_voltage(bus):
    config_bytes = [(CONFIG_REG >> 8) & 0xFF, CONFIG_REG & 0xFF]
    bus.write_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONFIG, config_bytes)
    time.sleep(0.01)
    data = bus.read_i2c_block_data(ADS1115_ADDRESS, ADS1115_POINTER_CONVERSION, 2)
    raw_adc = (data[0] << 8) | data[1]
    if raw_adc > 0x7FFF:
        raw_adc -= 0x10000
    voltage = raw_adc * (4.096 / 32768.0)
    return voltage

# --- GPIO + Motor Setup ---
IN1 = 6
IN2 = 5
PWM = 13

GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(PWM, GPIO.OUT)

GPIO.output(IN1, GPIO.HIGH)
GPIO.output(IN2, GPIO.LOW)

pwm = GPIO.PWM(PWM, 3000)
pwm.start(0)

# --- Force Feedback Parameters ---
CENTER_VOLTAGE = 1.65      # Ideal center of 3.3V range
DEADZONE_VOLTAGE = 0.1     # Volts to ignore near center
MAX_DUTY_CYCLE = 50        # Max PWM % to apply
GAIN = 100                 # Scale of force per volt

def apply_feedback(voltage):
    error = voltage - CENTER_VOLTAGE

    # Apply deadzone
    if abs(error) < DEADZONE_VOLTAGE:
        pwm.ChangeDutyCycle(0)
        return

    # Determine direction
    if error < 0:
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
    else:
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)

    # Apply torque proportional to error
    duty = min(MAX_DUTY_CYCLE, abs(error) * GAIN)
    pwm.ChangeDutyCycle(duty)

# --- Main Loop ---
with SMBus(I2C_BUS) as bus:
    print("Force feedback active. Press Ctrl+C to stop.")
    try:
        while True:
            voltage = read_voltage(bus)
            print(f"Pot Voltage: {voltage:.3f} V")
            apply_feedback(voltage)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        pwm.stop()
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.cleanup()
