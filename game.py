import pygame
from threading import Thread
from time import sleep
import constants

def draw_background():
  lcd.fill((0,0,0))
  return

def draw_user():
  lcd.blit(user_car, user_car_rect)
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
lcd = pygame.display.set_mode((1200, 800))

user_car = pygame.transform.scale_by(pygame.image.load(constants.USER_CAR_PATH), 0.1)
user_car_rect = user_car.get_rect(center=constants.USER_CAR_CENTER)

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
    draw_user()
    draw_lanes()
    pygame.display.flip()
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

print("quit main code, waiting for thread to quit...")
# t1.join()   # Wait for thread to complete
pygame.quit()