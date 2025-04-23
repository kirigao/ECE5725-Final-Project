import pygame
from threading import Thread
from time import sleep
import constants

# global variables

lcd = pygame.display.set_mode((1200, 800))

cur_id = 0
user_car = pygame.transform.scale_by(pygame.image.load(constants.USER_CAR_PATH), 0.1)
user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)
cpu_car_id_to_rect_map = {}
cpu_car_id_to_surface_map = {}

def generate_cpu_car():
  global cur_id
  cpu_car_center = (600, 300) # hard coded for now ===============================
  cpu_car = pygame.transform.scale_by(pygame.image.load(constants.CPU_CAR_PATH), 0.1)
  cpu_car_rect = cpu_car.get_rect(center=(cpu_car_center))
  cpu_car_id_to_rect_map[cur_id] = cpu_car_rect
  cpu_car_id_to_surface_map[cur_id] = cpu_car
  cur_id = cur_id + 1

def remove_all_passed_cpu_cars():
  cpu_cars_list = list(cpu_car_id_to_rect_map.keys())
  for id in cpu_cars_list:
    cpu_car_rect = cpu_car_id_to_rect_map[id]
    cpu_car_coordinates = (cpu_car_rect.x, cpu_car_rect.y)
    print(cpu_car_coordinates)
    if (out_of_bounds(cpu_car_coordinates)):
      cpu_car_id_to_rect_map.pop(id)
      cpu_car_id_to_surface_map.pop(id)

def move_all_cpu_cars():
  for cpu_car_rect in cpu_car_id_to_rect_map.values():
    move_cpu_car(cpu_car_rect)

def move_cpu_car(cpu_car):
  cpu_car.move_ip(0, constants.CPU_CAR_SPEED)

def out_of_bounds(coordinates):
  x = coordinates[0]
  y = coordinates[1]
  if x < constants.LEFT_BOUNDARY:
    return True
  elif x > constants.RIGHT_BOUNDARY:
    return True
  elif y > constants.BOTTOM_BOUNDARY:
    print("out of bounds!")
    return True
  return False

def move_user_left():
  new_user_car_coordinates = (user_car_rect.left - constants.LANE_X_LENGTH, user_car_rect.right)
  if not out_of_bounds(new_user_car_coordinates):
    user_car_rect.move_ip(-constants.LANE_X_LENGTH, 0)

def move_user_right():
  new_user_car_coordinates = (user_car_rect.left + constants.LANE_X_LENGTH, user_car_rect.right)
  if not out_of_bounds(new_user_car_coordinates):
    user_car_rect.move_ip(constants.LANE_X_LENGTH, 0)

def left_button_pressed():
  return pygame.key.get_pressed()[pygame.K_LEFT]

def right_button_pressed():
  return pygame.key.get_pressed()[pygame.K_RIGHT]

def move_user_car():
  sleep(0.3)
  if left_button_pressed():
    move_user_left()
    print("left button pressed")
  else:
    move_user_right()

def draw_background():
  lcd.fill((0,0,0))
  return

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

lcd.fill((0,0,0))
pygame.display.update()

# prompt_text = "Enter a num: "
# user_num = 1
# print("entering main code...")

# t1 = Thread(target=task)  #create new thread
# t1.start()    #start the thread
generate_cpu_car() #remove after testing
# Add a game loop to keep the window open
running = True
while running:
    draw_background()
    draw_user()
    draw_cpu()
    draw_lanes()
    pygame.display.update()
    pygame.display.flip()
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

print("quit main code, waiting for thread to quit...")
# t1.join()   # Wait for thread to complete
pygame.quit()