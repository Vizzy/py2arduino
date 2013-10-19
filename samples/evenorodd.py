def setup():
	global led
	led = 13
	pinMode(led, OUTPUT)
	Serial.begin(9600)
	Serial.println('beginning communication')

def loop():

	if Serial.available() > 0:
		Serial.println('> ')
		incoming = Serial.read()
		even = even_or_odd(incoming)

		if even:
			Serial.println('even')
			digitalWrite(led, HIGH)
		else:
			Serial.println('odd')
			digitalWrite(led, LOW)

def even_or_odd(x: int):
	if x % 2 is 0:
		return True
	else:
		return False
