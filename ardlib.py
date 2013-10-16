class Mode:
	def __init__(self, mode):
		self.mode = mode

class Serial:
	@staticmethod
	def begin(baudrate: int):
		pass

	@staticmethod
	def print(text: str):
		pass

	@staticmethod
	def println(text: str):
		pass

INPUT = Mode('INPUT')
OUTPUT = Mode('OUTPUT')

HIGH = 1
LOW = 0

# digital IO

def pinMode(x: int, mode: Mode):
	pass

def digitalWrite(x: int, level: bool):
	pass

def digitalRead() -> int:
	pass

# analog IO

def analogRead(pin: int) -> int:
	pass

def analogWrite(pin: int, value: int):
	pass

# TIME

def millis() -> int:
	pass

def micros() -> int:
	pass

def delay(x: int):
	pass