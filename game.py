import pygame
# from pygame.locals import * # for event MOUSE variables
import random
from threading import Thread
import time
from time import sleep
import constants
import os
from smbus2 import SMBus
import RPi.GPIO as GPIO
import subprocess

normalized_V = 0.5

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
    time.sleep(0.07)
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

# --- Main Loop ---
def motor_thread_function():
  global normalized_V
  with SMBus(I2C_BUS) as bus:
      try:
          while True:
              voltage = read_voltage(bus)
              normalized_V = voltage / 3.3
              apply_feedback(voltage)
      except KeyboardInterrupt:
          print("\nShutting down...")
      finally:
          pwm.stop()
          GPIO.output(IN1, GPIO.LOW)
          GPIO.output(IN2, GPIO.LOW)
          GPIO.cleanup()

# global variables

lcd = pygame.display.set_mode((1200, 800))
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

cur_id = 0

# statistics
score = 0
high_score = 0
cars_avoided = 0
total_cash = 0
time_passed = 0
current_level = 0


program_start_time = time.time()

last_button_press = time.time()
game_state = constants.GAME_STATE_TITLE

last_item_generate_time = time.time()

user_car = pygame.transform.scale_by(pygame.image.load(constants.USER_CAR_PATH), 0.2)
user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)

background = pygame.image.load(constants.BACKGROUND_PATH)
background_rect = background.get_rect(center=constants.BACKGROUND_CENTER)

duplicate_background = pygame.image.load(constants.BACKGROUND_PATH)
duplicate_background_rect = background.get_rect(center=constants.DUPLICATE_BACKGROUND_CENTER)

restart_button = pygame.image.load(constants.RESTART_BUTTON_PATH)
restart_button_rect = restart_button.get_rect(center=constants.RESTART_BUTTON_CENTER)

item_id_to_rect_map = {}
item_id_to_surface_map = {}

def update_time_passed():
    global time_passed
    time_passed = time.time() - program_start_time

def update_score():
    global score
    score = time.time() - program_start_time + total_cash

def reset_game():
  global user_car_rect
  global cur_id
  global score
  global total_cash
  global program_start_time
  global last_car_generate_time
  global last_money_generate_time
  global cars_avoided
  global time_passed
  global current_level
  item_id_to_rect_map.clear()
  item_id_to_surface_map.clear()
  user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)
  cur_id = 0
  score = 0
  total_cash = 0
  program_start_time = time.time()
  last_car_generate_time = time.time()
  last_money_generate_time = time.time()
  cars_avoided = 0
  time_passed = 0
  current_level = 0

def detect_collisions():
  global game_state
  global total_cash
  item_rect_list = list(item_id_to_rect_map.values())
  found_collision_id = "Null"
  for (id, item_rect) in item_id_to_rect_map.items():
    if user_car_rect.colliderect(item_rect) == True:
        if constants.COIN in id:
            found_collision_id = id
            total_cash = total_cash + 2
            break
        elif constants.BILL in id:
            found_collision_id = id
            total_cash = total_cash + 5
            break
        elif constants.STACK in id:
            found_collision_id = id
            total_cash = total_cash + 10
            break
        else:
            game_state = constants.GAME_STATE_OVER

  if found_collision_id != "Null":
      item_id_to_rect_map.pop(id)
      item_id_to_surface_map.pop(id)

def generate_item():
  global cur_id
  random_item_probability = random.randint(1, 100)
  random_num = random.randint(1, 3)
  item_center = (0, 0)
  if (random_num == 1):
    item_center = (constants.LEFT_LANE_CENTER_X, -300)
  elif (random_num == 2):
    item_center = (constants.MIDDLE_LANE_CENTER_X, -300)
  else:
    item_center = (constants.RIGHT_LANE_CENTER_X, -300)

  if random_item_probability <= constants.GENERATE_CAR_PROBABILITY:
    random_car = random.randint(0, 2)
    car_path = constants.CAR_PATHS[random_car]
    cpu_car = pygame.transform.scale_by(pygame.image.load(car_path), 0.4)
    cpu_car_rect = cpu_car.get_rect(center=(item_center))
    item_id_to_rect_map["car" + str(cur_id)] = cpu_car_rect
    item_id_to_surface_map["car" + str(cur_id)] = cpu_car
  elif random_item_probability <= constants.GENERATE_COIN_PROBABILITY:
    money = pygame.transform.scale_by(pygame.image.load(constants.COIN_PATH), 0.04)
    money_rect = money.get_rect(center=(item_center))
    item_id_to_rect_map["coin" + str(cur_id)] = money_rect
    item_id_to_surface_map["coin" + str(cur_id)] = money
  elif random_item_probability <= constants.GENERATE_BILL_PROBABILITY:
    money = pygame.transform.scale_by(pygame.image.load(constants.BILL_PATH), 0.08)
    money_rect = money.get_rect(center=(item_center))
    item_id_to_rect_map["bill" + str(cur_id)] = money_rect
    item_id_to_surface_map["bill" + str(cur_id)] = money
  elif random_item_probability <= constants.GENERATE_STACK_PROBABILITY:
    money = pygame.transform.scale_by(pygame.image.load(constants.STACK_PATH), 0.08)
    money_rect = money.get_rect(center=(item_center))
    item_id_to_rect_map["stack" + str(cur_id)] = money_rect
    item_id_to_surface_map["stack" + str(cur_id)] = money
  cur_id = cur_id + 1



def remove_all_items():
  global cars_avoided
  item_list = list(item_id_to_rect_map.keys())
  for id in item_list:
    item_rect = item_id_to_rect_map[id]
    if (out_of_bounds(item_rect)):
      if "car" in id:
        cars_avoided = cars_avoided + 1
      item_id_to_rect_map.pop(id)
      item_id_to_surface_map.pop(id)

def move_all_items():
  for item_rect in item_id_to_rect_map.values():
    move_item(item_rect)

def move_item(item_rect):
  time_passed = time.time() - program_start_time
  item_rect.move_ip(0, constants.CPU_CAR_SPEED + time_passed*0.1)

def move_item_half_speed(item_rect):
  time_passed = time.time() - program_start_time
  item_rect.move_ip(0, (constants.CPU_CAR_SPEED + time_passed*0.1)/2)

def move_background_to_top(background_rect):
  background_rect.move_ip(0, (-constants.BACKGROUND_TOP_DISTANCE + ((constants.CPU_CAR_SPEED + time_passed*0.1)/2) ) )

def out_of_bounds(rect):
  left = rect.left
  right = rect.left + rect.width
  top = rect.top
  bottom = rect.top + rect.height
  if left < constants.LEFT_BOUNDARY or right < constants.LEFT_BOUNDARY:
    return True
  elif left > constants.RIGHT_BOUNDARY or right > constants.RIGHT_BOUNDARY:
    return True
  elif top > constants.BOTTOM_BOUNDARY:
    #print("out of bounds!")
    return True
  return False

def bg_out_of_bounds(rect):
  top = rect.top
  return top >= constants.BOTTOM_BOUNDARY

def move_user_car():
    volt = normalized_V
    invert_volt = 1-volt

    volt_to_x_coord = invert_volt*720 + 240
    dx = volt_to_x_coord - user_car_rect.center[0]
    user_car_rect.move_ip(dx, 0)

def draw_title():
  lcd.fill((0,0,0))
  font = pygame.font.SysFont(None, 72)
  title_text = font.render('[Insert Title]', True, WHITE)
  lcd.blit(title_text, (450, 220))
  return

def draw_background():
  lcd.fill((0,0,0))
  if bg_out_of_bounds(background_rect) == False:
    move_item_half_speed(background_rect)
  elif bg_out_of_bounds(background_rect):
    move_background_to_top(background_rect)

  if bg_out_of_bounds(duplicate_background_rect) == False:
    move_item_half_speed(duplicate_background_rect)
  elif bg_out_of_bounds(duplicate_background_rect):
    move_background_to_top(duplicate_background_rect)

  lcd.blit(background, background_rect)
  lcd.blit(duplicate_background, duplicate_background_rect)
  return

def draw_score():
    global high_score
    update_score()
    if score > high_score:
        high_score = score
    font = pygame.font.SysFont(None, 24)
    score_text = font.render('score: ' + str(int(score)), True, BLUE)
    lcd.blit(score_text, (50, 100))
    high_score_text = font.render('high score: ' + str(int(high_score)), True, BLUE)
    lcd.blit(high_score_text, (50, 150))

def draw_cars_avoided():
    global cars_avoided
    font = pygame.font.SysFont(None, 24)
    cars_avoided_text = font.render('cars avoided: ' + str(cars_avoided), True, BLUE)
    lcd.blit(cars_avoided_text, (50, 200))

def draw_total_cash():
    global total_cash
    font = pygame.font.SysFont(None, 24)
    total_cash_text = font.render('total_cash: ' + str(total_cash), True, BLUE)
    lcd.blit(total_cash_text, (50, 250))

def draw_time_passed():
    global time_passed
    font = pygame.font.SysFont(None, 24)
    time_passed_text = font.render('time passed: ' + str(int(time_passed)), True, BLUE)
    lcd.blit(time_passed_text, (50, 300))

def draw_current_level():
    global current_level
    font = pygame.font.SysFont(None, 24)
    current_level_text = font.render('current level: ' + str(current_level), True, BLUE)
    lcd.blit(current_level_text, (50, 350))

def draw_statistics():
    draw_score()
    draw_cars_avoided()
    draw_total_cash()
    
    update_time_passed()
    draw_time_passed()
    draw_current_level()

def draw_restart_button():
  lcd.blit(restart_button, restart_button_rect)

def draw_user():
  move_user_car()
  lcd.blit(user_car, user_car_rect)
  return

def draw_cpu():
  move_all_items()
  remove_all_items()
  for (id, item_rect) in item_id_to_rect_map.items():
    item = item_id_to_surface_map[id]
    lcd.blit(item, item_rect)
    #print(cpu_car_rect)
  return

def draw_lanes():
  left_lane = pygame.draw.line(lcd, constants.LANE_COLOR, constants.LEFT_LANE_START_POS, constants.LEFT_LANE_END_POS, width=constants.LANE_WIDTH)
  middle_lane = pygame.draw.line(lcd, constants.LANE_COLOR, constants.MIDDLE_LANE_START_POS, constants.MIDDLE_LANE_END_POS, width=constants.LANE_WIDTH)
  right_lane = pygame.draw.line(lcd, constants.LANE_COLOR, constants.RIGHT_LANE_START_POS, constants.RIGHT_LANE_END_POS, width=constants.LANE_WIDTH)
  auxiliary = pygame.draw.line(lcd, constants.LANE_COLOR, constants.AUXILIARY_START_POS, constants.AUXILIARY_END_POS, width=constants.LANE_WIDTH)
  return

# def task():
#   global user_num
#   thread_running = True
#   print("thread running...")
#   while (thread_running):
#     if (user_num == 0):
#       thread_running = False

pygame.init()
pygame.mouse.set_visible(True)

lcd.fill((0,0,0))
pygame.display.update()

# prompt_text = "Enter a num: "
# user_num = 1
# print("entering main code...")

# t1 = Thread(target=task)  #create new thread
# t1.start()    #start the thread

t1 = Thread(target=motor_thread_function)
t1.start()    #start the thread

# Add a game loop to keep the window open
running = True
while running:
  if (game_state == constants.GAME_STATE_TITLE):
    draw_title()
    draw_restart_button()
  elif (game_state == constants.GAME_STATE_OVER):
    draw_background()
    draw_restart_button()
  elif (game_state == constants.GAME_STATE_RUNNING):
    current_time = time.time()
    # current_level = int((current_time - program_start_time) //30)
    # if current_time - last_item_generate_time >= constants.ITEM_GENERATION_INTERVAL-current_level*0.5:
    if (current_time - last_item_generate_time >= 5.67/ (4 + (current_time - last_item_generate_time) * 0.1)):
      generate_item()
      last_item_generate_time = current_time
    draw_background()
    draw_statistics()
    draw_user()
    draw_cpu()
    draw_lanes()
    detect_collisions()
  pygame.display.update()
  pygame.display.flip()
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False

    elif event.type == pygame.MOUSEBUTTONUP and game_state == constants.GAME_STATE_OVER:
      print("restart click")
      reset_game()
      game_state = constants.GAME_STATE_RUNNING

    elif event.type == pygame.MOUSEBUTTONUP and game_state == constants.GAME_STATE_TITLE:
      print("restart click")
      reset_game()
      game_state = constants.GAME_STATE_RUNNING

print("quit main code, waiting for thread to quit...")
t1.join()   # Wait for thread to complete
pygame.quit()
