class Mode:
	def __init__(self, mode):
		self.mode = mode

class Format():
	def __init__(self, theformat):
		self.format = theformat

class Serial:
	@staticmethod
	def available() -> int:
		pass

	@staticmethod
	def begin(baudrate: int):
		pass

	@staticmethod
	def print(text: str):
		pass

	@staticmethod
	def println(text: str, format: Format=None):
		pass

	@staticmethod
	def read() -> int:
		pass

INPUT = Mode('INPUT')
OUTPUT = Mode('OUTPUT')

DEC = Format('DEC')
HEX = Format('HEX')
OCT = Format('OCT')
BIN = Format('BIN')

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