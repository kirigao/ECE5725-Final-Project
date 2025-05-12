from threading import Thread
from time import sleep
import RPi.GPIO as GPIO

def user_input_thread():
    global duty_cycle, running
    while running:
        try:
            value = int(input("Enter duty cycle (0–100), or 0 to stop: "))
            if 0 <= value <= 100:
                duty_cycle = value
                if value == 0:
                    running = False
            else:
                print("Please enter a number between 0 and 100.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# --- GPIO Setup ---
GPIO.setmode(GPIO.BCM)

IN1 = 6
IN2 = 5
PWM = 13

GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(PWM, GPIO.OUT)

# Set fixed direction (e.g., CW)
GPIO.output(IN1, GPIO.HIGH)
GPIO.output(IN2, GPIO.LOW)

# PWM setup
freq = 3000
duty_cycle = 0
running = True

pwm13 = GPIO.PWM(PWM, freq)
pwm13.start(duty_cycle)

# --- Start user input thread ---
t1 = Thread(target=user_input_thread)
t1.start()

try:
    while running:
        pwm13.ChangeDutyCycle(duty_cycle)
        sleep(0.1)  # Small delay to prevent CPU hogging
finally:
    print("Shutting down...")
    pwm13.stop()
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.cleanup()
    t1.join()
