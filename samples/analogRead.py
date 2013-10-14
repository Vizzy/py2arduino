'''
AnalogReadSerial
  Reads an analog input on pin 0, prints the result to the serial monitor.
  Attach the center pin of a potentiometer to pin A0, and the outside pins to +5V and ground.
'''

def setup():
	Serial.begin(9600)

def loop():
	sensorValue = analogRead(A0)
	Serial.println(sensorValue)
	delay(1)