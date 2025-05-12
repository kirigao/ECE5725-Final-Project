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

pygame.init()
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
DEADZONE_VOLTAGE = 0.15
MAX_DUTY_CYCLE = 90
P_GAIN = 100
D_GAIN = 50
last_error = 1.65

def apply_feedback(voltage):
    global last_error
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

    # proportional gain
    duty = abs(error) * P_GAIN

    # derivative gain
    derivative = error - last_error

    duty += derivative * D_GAIN
    last_error = error

    #clamp max duty cycle
    duty = min(MAX_DUTY_CYCLE, duty)
    duty = max(0, duty)
    pwm.ChangeDutyCycle(duty)

# --- Main Loop ---
def motor_thread_function():
  global normalized_V
  global running
  with SMBus(I2C_BUS) as bus:
      try:
          while running:
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
FPS = 60
# statistics
score = 0
high_score = 0
cars_avoided = 0
total_cash = 0
time_passed = 0
current_level = 0
lives = 3


program_start_time = time.time()

last_button_press = time.time()
game_state = constants.GAME_STATE_TITLE

last_item_generate_time = time.time()
last_time_lost_life = time.time()

#0.45 for OG
user_car = pygame.transform.scale_by(pygame.image.load(constants.USER_CAR_PATH), 0.18).convert_alpha()
user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)

background = pygame.image.load(constants.BACKGROUND_PATH).convert_alpha()
background_rect = background.get_rect(center=constants.BACKGROUND_CENTER)

title_screen = pygame.image.load(constants.TITLE_SCREEN_PATH).convert_alpha()
title_screen_rect = title_screen.get_rect(center=constants.TITLE_SCREEN_CENTER)

duplicate_background_rect = background.get_rect(center=constants.DUPLICATE_BACKGROUND_CENTER)

restart_button = pygame.transform.scale_by(pygame.image.load(constants.RESTART_BUTTON_PATH), 0.5).convert_alpha()
restart_button_rect = restart_button.get_rect(center=constants.RESTART_BUTTON_CENTER)

green_car_image = pygame.transform.scale_by(pygame.image.load(constants.CAR_PATHS[0]), 0.45).convert_alpha()
blue_car_image = pygame.transform.scale_by(pygame.image.load(constants.CAR_PATHS[1]), 0.45).convert_alpha()
truck_image = pygame.transform.scale_by(pygame.image.load(constants.CAR_PATHS[2]), 0.58).convert_alpha()
bus_image = pygame.transform.scale_by(pygame.image.load(constants.CAR_PATHS[3]), 0.58).convert_alpha()

cpu_car_images = [green_car_image, blue_car_image, truck_image, bus_image]
coin_image = pygame.transform.scale_by(pygame.image.load(constants.COIN_PATH), 0.04).convert_alpha()
bill_image = pygame.transform.scale_by(pygame.image.load(constants.BILL_PATH), 0.055).convert_alpha()
stack_image = pygame.transform.scale_by(pygame.image.load(constants.STACK_PATH), 0.055).convert_alpha()

heart_image = pygame.transform.scale_by(pygame.image.load(constants.HEART_PATH), 0.4).convert_alpha()

numbers_images = []
for i in range(10):
 num_img = pygame.transform.scale_by(pygame.image.load(f"./images/levels/{i}.png"), 0.2).convert_alpha()
 numbers_images.append(num_img)

level_image = pygame.transform.scale_by(pygame.image.load(constants.LEVEL_PATH), 0.2).convert_alpha()

quit_game_image = pygame.transform.scale_by(pygame.image.load(constants.QUIT_GAME_PATH), 0.2).convert_alpha()
return_home_image = pygame.transform.scale_by(pygame.image.load(constants.RETURN_HOME_PATH), 0.2).convert_alpha()

font = pygame.font.SysFont(None, 24)
name_font = pygame.font.SysFont(None, 36)

item_id_to_rect_map = {}
item_id_to_surface_map = {}

sorted_players = []

my_clock = pygame.time.Clock()

user_input_box = pygame.Rect(constants.USER_INPUT_BOX_X, constants.USER_INPUT_BOX_Y, constants.USER_INPUT_BOX_WIDTH, constants.USER_INPUT_BOX_HEIGHT)
user_input = ''
player_name = ''
new_level_buffer = False
prev_level = -1
base_level_time = time.time()

def convert_level_to_list(num):
  result = []
  while num != 0:
    result.insert(0, num % 10)
    num = num // 10
  return result

def write_to_file(filename, player_score):
  with open(filename, 'a') as file:
      for player, score in player_score.items():
        file.write(f"{player},{score}\n")
  print(f"Player data has been written to {filename}")

def read_and_sort(filename):
    global sorted_players
    players_scores = {}
    try:
      with open(filename, 'r') as file:
        for line in file:
          player, score = line.strip().split(',')
          players_scores[player] = int(score)

      sorted_players = sorted(players_scores.items(), key=lambda x: x[1], reverse=True)
      print("\nPlayers sorted by score (highest to lowest):")
      for player, score in sorted_players:
        print(f"{player}: {score}")
    except FileNotFoundError:
      print(f"File {fileName} not found.")

def update_time_passed():
    global time_passed
    time_passed = time.time() - program_start_time

def update_score():
    global score
    score = int(time.time() - program_start_time) + total_cash

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
  global lives
  global new_level_buffer
  global prev_level
  global base_level_time
  item_id_to_rect_map.clear()
  item_id_to_surface_map.clear()
  user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)
  cur_id = 0
  score = 0
  total_cash = 0
  program_start_time = time.time()
  last_car_generate_time = time.time()
  last_money_generate_time = time.time()
  last_time_lost_life = time.time()
  cars_avoided = 0
  time_passed = 0
  current_level = 0
  lives = 3
  new_level_buffer = False
  prev_level = -1
  base_level_time = time.time()

def detect_collisions():
  global game_state
  global total_cash
  global lives
  global last_time_lost_life
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
            if time.time() - last_time_lost_life >= constants.LIFE_LOST_COOLDOWN:
              last_time_lost_life = time.time()
              if lives == 1:
                game_state = constants.GAME_STATE_OVER
              else:
                found_collision_id = id
                lives = lives - 1
                break


  if found_collision_id != "Null":
      item_id_to_rect_map.pop(id)
      item_id_to_surface_map.pop(id)


def generate_random_car():
  global current_level
  if current_level < 4:
    random_car = random.choices([0, 1, 2, 3], weights = constants.LEVELPROBS[current_level])[0]
  else:
    random_car = random.choices([0, 1, 2, 3], weights = constants.LEVELPROBS[4])[0]
  return random_car

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
    random_car = generate_random_car()

    cpu_car_rect = cpu_car_images[random_car].get_rect(center=(item_center))
    item_id_to_rect_map["car" + str(cur_id)] = cpu_car_rect
    item_id_to_surface_map["car" + str(cur_id)] = cpu_car_images[random_car]
  elif random_item_probability <= constants.GENERATE_COIN_PROBABILITY:
    money_rect = coin_image.get_rect(center=(item_center))
    item_id_to_rect_map["coin" + str(cur_id)] = money_rect
    item_id_to_surface_map["coin" + str(cur_id)] = coin_image
  elif random_item_probability <= constants.GENERATE_BILL_PROBABILITY:
    money_rect = bill_image.get_rect(center=(item_center))
    item_id_to_rect_map["bill" + str(cur_id)] = money_rect
    item_id_to_surface_map["bill" + str(cur_id)] = bill_image
  elif random_item_probability <= constants.GENERATE_STACK_PROBABILITY:
    money_rect = stack_image.get_rect(center=(item_center))
    item_id_to_rect_map["stack" + str(cur_id)] = money_rect
    item_id_to_surface_map["stack" + str(cur_id)] = stack_image
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

    volt_to_x_coord = invert_volt*constants.USER_CAR_BOUND_LENGTH + constants.USER_CAR_LEFT_BOUND
    dx = volt_to_x_coord - user_car_rect.center[0]
    user_car_rect.move_ip(dx, 0)

def draw_input():
    user_input_text = name_font.render(user_input, True, constants.BLACK)
    pygame.draw.rect(lcd, WHITE, user_input_box)
    lcd.blit(user_input_text, constants.USER_INPUT_CENTER)

def draw_title():
  lcd.fill((0,0,0))

  lcd.blit(title_screen, title_screen_rect)

  instructions_text = name_font.render(constants.TITLE_SCREEN_INSTRUCTIONS, True, WHITE)
  lcd.blit(instructions_text, constants.TITLE_SCREEN_INSTRUCTIONS_CENTER)

  lcd.blit(quit_game_image, (350, 735))
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
  lcd.blit(background, duplicate_background_rect)
  return

def draw_score():
    global high_score
    update_score()
    if score > high_score:
        high_score = score
    score_text = font.render('score: ' + str(int(score)), True, BLUE)
    lcd.blit(score_text, (50, 100))
    high_score_text = font.render('high score: ' + str(int(high_score)), True, BLUE)
    lcd.blit(high_score_text, (50, 150))

def draw_lives():
  global lives
  for i in range(lives):
    lcd.blit(heart_image, (900+90*i, 700))
  life_text = font.render('lives left: ' + str(lives), True, BLUE)
  lcd.blit(life_text, (50, 400))

def draw_leaderboard():
  index = 1
  leaderboard_text = font.render("Leaderboard", True, BLUE)
  lcd.blit(leaderboard_text, (1000, 100))
  for player, score in sorted_players:
    if index == 10:
      break
    text = font.render(f"{index}: {player} {score}", True, BLUE)
    lcd.blit(text, (1000, 100 + 50*index))
    index = index + 1

def draw_cars_avoided():
    global cars_avoided
    cars_avoided_text = font.render('cars avoided: ' + str(cars_avoided), True, BLUE)
    lcd.blit(cars_avoided_text, (50, 200))

def draw_total_cash():
    global total_cash
    total_cash_text = font.render('total cash: ' + str(total_cash), True, BLUE)
    lcd.blit(total_cash_text, (50, 250))

def draw_time_passed():
    global time_passed
    time_passed_text = font.render('time passed: ' + str(int(time_passed)), True, BLUE)
    lcd.blit(time_passed_text, (50, 300))

def draw_current_level():
    global current_level
    current_level_text = font.render('current level: ' + str(current_level), True, BLUE)
    lcd.blit(current_level_text, (50, 350))

def draw_level_display(current_time):
  global new_level_buffer
  global base_level_time
  global current_level
  if time.time() - base_level_time < constants.LEVEL_DISPLAY_TIME and new_level_buffer:
      numbers = convert_level_to_list(current_level)
      # 123 -> [1, 2, 3]
      index = 0
      if len(numbers) > 0:
        lcd.blit(level_image, (400, 150))
      for num in numbers:
        lcd.blit(numbers_images[num], (700 + 60 * index, 150))
        index = index + 1
  else:
      new_level_buffer = False

def draw_statistics():
    draw_score()
    draw_cars_avoided()
    draw_total_cash()
    
    update_time_passed()
    draw_time_passed()
    draw_current_level()
    draw_lives()

def draw_restart_button():
  lcd.blit(restart_button, restart_button_rect)
  lcd.blit(return_home_image, (350, 710))

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
currently_writing = True
read_and_sort(constants.SCORES_FILE_NAME)
while running:
  my_clock.tick(FPS)
  lcd.fill((0,0,0))
  if (game_state == constants.GAME_STATE_TITLE):
    draw_title()
    draw_input()
  elif (game_state == constants.GAME_STATE_OVER):
    draw_background()
    draw_restart_button()
  elif (game_state == constants.GAME_STATE_RUNNING):
    current_time = time.time()
    current_level = int((current_time - program_start_time) //30)
    if current_level > prev_level:
      prev_level = current_level
      new_level_buffer = True
      base_level_time = time.time()
    # if (current_time - last_item_generate_time >= 8/ (10 + (current_time - last_item_generate_time) * 0.1)):
    if (current_time - last_item_generate_time >= (8 / (7 + 2.5 * current_level))) and new_level_buffer == False:
      generate_item()
      last_item_generate_time = current_time
    draw_background()
    draw_level_display(base_level_time)
    draw_statistics()
    draw_leaderboard()
    draw_user()
    draw_cpu()
    #draw_lanes()
    detect_collisions()
  pygame.display.update()
  #pygame.display.flip()
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False

    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and game_state == constants.GAME_STATE_OVER:
      print("restart click")
      write_to_file(constants.SCORES_FILE_NAME, {player_name:score})
      game_state = constants.GAME_STATE_TITLE
      currently_writing = True

    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and game_state == constants.GAME_STATE_TITLE:
      running = False

    elif event.type == pygame.MOUSEBUTTONUP and game_state == constants.GAME_STATE_OVER:    
      write_to_file(constants.SCORES_FILE_NAME, {player_name:score})  
      reset_game()
      game_state = constants.GAME_STATE_RUNNING

    elif event.type == pygame.KEYDOWN and currently_writing:
      if event.key == pygame.K_RETURN:
        currently_writing = False
        player_name = user_input
        reset_game()
        game_state = constants.GAME_STATE_RUNNING
      elif event.key == pygame.K_BACKSPACE:
        user_input = user_input[:-1]
      else:
        if len(user_input) < 11:  
          user_input = user_input + event.unicode

print("quit main code, waiting for thread to quit...")
t1.join()   # Wait for thread to complete
pygame.quit()
