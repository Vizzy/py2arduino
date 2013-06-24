class Mode:
	def __init__(self, mode):
		self.mode = mode

INPUT = Mode('INPUT')
OUTPUT = Mode('OUTPUT')

HIGH = True
LOW = False

def pinMode(x: int, mode: Mode):
	pass

def digitalWrite(x: int, level: bool):
	pass

def delay(x: int):
	pass