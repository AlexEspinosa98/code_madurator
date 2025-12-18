import RPi.GPIO as GPIO
import time

led_pin = 19

GPIO.setmode(GPIO.BCM)   
GPIO.setup(led_pin, GPIO.OUT)

pwm = GPIO.PWM(led_pin, 500)    
pwm.start(0)                     


while(True):
  pwm.ChangeDutyCycle(100)
  time.sleep(0.02)


