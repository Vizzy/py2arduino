#!/usr/bin/env python3.3

import sys, pprint, os.path
from pyduino import translate

pp = pprint.PrettyPrinter()

input_code = sys.argv[1]

if os.path.exists(input_code):
	input_code = open(input_code).read()


result = translate(input_code)

pp.pprint(result)
print(result['code'])
