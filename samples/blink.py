# define the led
led = 13

def setup():
    led = 10
    pinMode(led, OUTPUT)

def loop():
    digitalWrite(led, HIGH)
    delay(calc_delay(500))
    digitalWrite(led, LOW)
    delay(calc_delay(500*2))

def calc_delay(x: int) -> int:
	return x * 2