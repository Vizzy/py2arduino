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

HIGH = True
LOW = False

def pinMode(x: int, mode: Mode):
	pass

def digitalWrite(x: int, level: bool):
	pass

def digitalRead() -> int:
	pass

def delay(x: int):
	pass