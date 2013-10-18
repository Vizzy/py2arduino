# define the led

def setup():
    global led
    led = 13
    pinMode(led, OUTPUT)

def loop():
    digitalWrite(led, HIGH)
    delay(1000)
    digitalWrite(led, LOW)
    delay(1000)