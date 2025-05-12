import time
import os
from smbus2 import SMBus
import RPi.GPIO as GPIO
import subprocess

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
CENTER_VOLTAGE = 1.65
DEADZONE_VOLTAGE = 0.1
MAX_DUTY_CYCLE = 50
GAIN = 100

def apply_feedback(voltage):
    error = voltage - CENTER_VOLTAGE
    if abs(error) < DEADZONE_VOLTAGE:
        pwm.ChangeDutyCycle(0)
        return

    if error < 0:
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
    else:
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)

    duty = min(MAX_DUTY_CYCLE, abs(error) * GAIN)
    pwm.ChangeDutyCycle(duty)

# --- FIFO Setup ---
FIFO_PATH = "steering_fifo"

# Create FIFO if it doesn't exist
if not os.path.exists(FIFO_PATH):
    os.mkfifo(FIFO_PATH)

# --- Main Loop ---
with SMBus(I2C_BUS) as bus, open(FIFO_PATH, 'w') as fifo:
    print("Force feedback active. Writing to FIFO. Press Ctrl+C to stop.")
    try:
        while True:
            voltage = read_voltage(bus)
            normalized_V = voltage / 3.3
            my_cmd = f"echo {normalized_V:.4f} > /home/pi/finalproject/steering_fifo"
            subprocess.check_output(my_cmd, shell=True)
            apply_feedback(voltage)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        pwm.stop()
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.cleanup()
