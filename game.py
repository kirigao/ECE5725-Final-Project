import pygame
# from pygame.locals import * # for event MOUSE variables
import random
from threading import Thread
import time
from time import sleep
import constants

# global variables

lcd = pygame.display.set_mode((1200, 800))

cur_id = 0
last_button_press = time.time()
game_state = constants.GAME_STATE_RUNNING

user_car = pygame.transform.scale_by(pygame.image.load(constants.USER_CAR_PATH), 0.1)
user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)

restart_button = pygame.image.load(constants.RESTART_BUTTON_PATH)
restart_button_rect = restart_button.get_rect(center=constants.RESTART_BUTTON_CENTER)

cpu_car_id_to_rect_map = {}
cpu_car_id_to_surface_map = {}

def detect_collisions():
  global game_state
  cpu_car_rect_list = list(cpu_car_id_to_rect_map.values())
  if user_car_rect.collidelist(cpu_car_rect_list) != -1:
    #print("collision detected!")
    game_state = constants.GAME_STATE_OVER

def generate_cpu_car():
  global cur_id
  random_num = random.randint(1, 3)
  cpu_car_center = (0, 0)
  if (random_num == 1):
    cpu_car_center = (constants.LEFT_LANE_CENTER_X, 0)
  elif (random_num == 2):
    cpu_car_center = (constants.MIDDLE_LANE_CENTER_X, 0)
  else:
    cpu_car_center = (constants.RIGHT_LANE_CENTER_X, 0)

  cpu_car = pygame.transform.scale_by(pygame.image.load(constants.CPU_CAR_PATH), 0.1)
  cpu_car_rect = cpu_car.get_rect(center=(cpu_car_center))
  cpu_car_id_to_rect_map[cur_id] = cpu_car_rect
  cpu_car_id_to_surface_map[cur_id] = cpu_car
  cur_id = cur_id + 1

def remove_all_passed_cpu_cars():
  cpu_cars_list = list(cpu_car_id_to_rect_map.keys())
  for id in cpu_cars_list:
    cpu_car_rect = cpu_car_id_to_rect_map[id]
    if (out_of_bounds(cpu_car_rect)):
      cpu_car_id_to_rect_map.pop(id)
      cpu_car_id_to_surface_map.pop(id)

def move_all_cpu_cars():
  for cpu_car_rect in cpu_car_id_to_rect_map.values():
    move_cpu_car(cpu_car_rect)

def move_cpu_car(cpu_car):
  cpu_car.move_ip(0, constants.CPU_CAR_SPEED)

def out_of_bounds(rect):
  left = rect.left
  right = rect.left + rect.width
  top = rect.top
  bottom = rect.top + rect.height
  if left < constants.LEFT_BOUNDARY or right < constants.LEFT_BOUNDARY:
    return True
  elif left > constants.RIGHT_BOUNDARY or right > constants.RIGHT_BOUNDARY:
    return True
  elif top > constants.BOTTOM_BOUNDARY or bottom > constants.BOTTOM_BOUNDARY:
    #print("out of bounds!")
    return True
  return False

def move_user_left():
  time.sleep(0.2)
  new_rect = user_car_rect.copy()
  new_rect.move_ip(-constants.LANE_X_LENGTH, 0)
  if not out_of_bounds(new_rect):
    user_car_rect.move_ip(-constants.LANE_X_LENGTH, 0)

def move_user_right():
  time.sleep(0.2)
  new_rect = user_car_rect.copy()
  new_rect.move_ip(constants.LANE_X_LENGTH, 0)
  if not out_of_bounds(new_rect):
    user_car_rect.move_ip(constants.LANE_X_LENGTH, 0)

def left_button_pressed():
  return pygame.key.get_pressed()[pygame.K_LEFT]

def right_button_pressed():
  return pygame.key.get_pressed()[pygame.K_RIGHT]

def move_user_car():
  global last_button_press
  current_time = time.time()
  if current_time - last_button_press >= constants.KEY_PRESS_INTERVAL:
    if left_button_pressed():
      move_user_left()
      print("left button pressed")
    elif right_button_pressed():
      move_user_right()
      print("right button pressed")

    last_button_press = current_time

def draw_background():
  lcd.fill((0,0,0))
  return

def draw_restart_button():
  lcd.blit(restart_button, restart_button_rect)

def draw_user():
  if (left_button_pressed() or right_button_pressed()):
    move_user_car()
  lcd.blit(user_car, user_car_rect)
  return

def draw_cpu():
  move_all_cpu_cars()
  remove_all_passed_cpu_cars()
  for (id, cpu_car_rect) in cpu_car_id_to_rect_map.items():
    cpu_car = cpu_car_id_to_surface_map[id]
    lcd.blit(cpu_car, cpu_car_rect)
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
last_generate_time = time.time()


lcd.fill((0,0,0))
pygame.display.update()

# prompt_text = "Enter a num: "
# user_num = 1
# print("entering main code...")

# t1 = Thread(target=task)  #create new thread
# t1.start()    #start the thread
# Add a game loop to keep the window open
running = True
while running:
  if (game_state == constants.GAME_STATE_OVER):
    draw_background()
    draw_restart_button()
  elif (game_state == constants.GAME_STATE_RUNNING):
    current_time = time.time()
    if current_time - last_generate_time >= constants.CPU_GENERATION_INTERVAL:
      # print(str(current_time) + " generated new cpu car.")
      generate_cpu_car()
      last_generate_time = current_time
    draw_background()
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

print("quit main code, waiting for thread to quit...")
# t1.join()   # Wait for thread to complete
pygame.quit()