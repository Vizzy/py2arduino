def three_or_more(x: int):
	y = x + 1
	if y >= 3:
		return doubler(y)
	else:
		return three_or_more(y)

def doubler(x: int):
	return x*2