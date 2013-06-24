from ardlib import *

# define the led
led = 13

def setup():
    led = 10
    pinMode(led, OUTPUT)

def loop():
    digitalWrite(led, HIGH)
    delay(1000)
    digitalWrite(led, LOW)
    delay(1000)

def calc_delay(x: int) -> int:
    return x * 2